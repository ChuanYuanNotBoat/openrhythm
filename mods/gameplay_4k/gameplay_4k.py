"""
4K下落式玩法Mod - 完整版
"""
from typing import List, Optional, Tuple, Dict, Any, Callable
import json
import time
import math
from enum import Enum
from dataclasses import dataclass

class NoteType(Enum):
    TAP = 1
    HOLD = 2
    SLIDE = 3
    CHAIN = 4

@dataclass
class Note:
    id: int
    start_time: float
    end_time: Optional[float]
    column: int
    note_type: NoteType
    beat: Tuple[int, int, int]
    sound: Optional[str] = None
    volume: Optional[int] = None
    
    # 游戏状态
    hit: bool = False
    missed: bool = False
    hit_time: Optional[float] = None
    accuracy: float = 0.0
    hold_progress: float = 0.0  # 长按进度 0.0-1.0
    
    def is_active(self, current_time: float, judgement_window: float) -> bool:
        """检查音符是否处于活动状态（需要被渲染或判定）"""
        if self.hit or self.missed:
            return False
        
        # 提前出现的时间
        appear_time = 2.0  # 提前2秒出现
        
        # 检查结束时间（对于长按音符）
        end = self.end_time or self.start_time
        return (self.start_time - appear_time <= current_time <= end + judgement_window)
    
    def get_y_position(self, current_time: float, scroll_speed: float) -> float:
        """计算音符的Y位置（基于下落速度）"""
        time_until_hit = self.start_time - current_time
        return 0.8 - (time_until_hit * scroll_speed * 0.4)
    
    def get_hold_length(self, current_time: float, scroll_speed: float) -> float:
        """计算长按音符的长度（如果是长按）"""
        if self.note_type != NoteType.HOLD or not self.end_time:
            return 0.0
        
        duration = self.end_time - self.start_time
        return duration * scroll_speed * 0.4

class Judgement(Enum):
    PERFECT = 0
    GREAT = 1
    GOOD = 2
    BAD = 3
    MISS = 4

@dataclass
class JudgementWindow:
    perfect: float  # ±毫秒
    great: float
    good: float
    bad: float
    
    @classmethod
    def default(cls) -> 'JudgementWindow':
        return cls(perfect=50, great=100, good=150, bad=200)
    
    def judge(self, time_diff: float) -> Tuple[Judgement, float]:
        """根据时间差判断命中等级"""
        abs_diff = abs(time_diff * 1000)  # 转换为毫秒
        
        if abs_diff <= self.perfect:
            return Judgement.PERFECT, 1.0
        elif abs_diff <= self.great:
            accuracy = 1.0 - (abs_diff - self.perfect) / (self.great - self.perfect) * 0.3
            return Judgement.GREAT, accuracy
        elif abs_diff <= self.good:
            accuracy = 0.7 - (abs_diff - self.great) / (self.good - self.great) * 0.3
            return Judgement.GOOD, accuracy
        elif abs_diff <= self.bad:
            accuracy = 0.4 - (abs_diff - self.good) / (self.bad - self.good) * 0.3
            return Judgement.BAD, accuracy
        else:
            return Judgement.MISS, 0.0

@dataclass
class ScoreInfo:
    score: int = 0
    combo: int = 0
    max_combo: int = 0
    judgements: Dict[Judgement, int] = None
    accuracy: float = 0.0
    grade: str = "F"
    
    def __post_init__(self):
        if self.judgements is None:
            self.judgements = {j: 0 for j in Judgement}
    
    def add_judgement(self, judgement: Judgement, accuracy: float = 0.0):
        """添加判定结果"""
        self.judgements[judgement] += 1
        
        # 更新连击
        if judgement in [Judgement.PERFECT, Judgement.GREAT, Judgement.GOOD]:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            
            # 计算分数（基于连击和准确度）
            base_score = {
                Judgement.PERFECT: 100,
                Judgement.GREAT: 80,
                Judgement.GOOD: 50,
            }[judgement]
            
            combo_multiplier = min(1.0 + (self.combo - 1) * 0.01, 2.0)  # 最大2倍
            self.score += int(base_score * combo_multiplier * accuracy)
        else:
            self.combo = 0
        
        # 计算准确率
        total_notes = sum(self.judgements.values())
        if total_notes > 0:
            weighted_score = (
                self.judgements[Judgement.PERFECT] * 1.0 +
                self.judgements[Judgement.GREAT] * 0.7 +
                self.judgements[Judgement.GOOD] * 0.4 +
                self.judgements[Judgement.BAD] * 0.1
            )
            self.accuracy = weighted_score / total_notes * 100
    
    def calculate_grade(self) -> str:
        """计算评级"""
        if self.accuracy >= 99.0:
            return "SSS"
        elif self.accuracy >= 95.0:
            return "SS"
        elif self.accuracy >= 90.0:
            return "S"
        elif self.accuracy >= 80.0:
            return "A"
        elif self.accuracy >= 70.0:
            return "B"
        elif self.accuracy >= 60.0:
            return "C"
        elif self.accuracy >= 50.0:
            return "D"
        else:
            return "F"

class GameplayState(Enum):
    LOADING = 1
    READY = 2
    PLAYING = 3
    PAUSED = 4
    FINISHED = 5

class Gameplay4K:
    """4K下落式玩法实现 - 完整版"""
    
    def __init__(self, chart_data: Dict[str, Any], difficulty_settings: Dict[str, Any]):
        self.chart_data = chart_data
        self.difficulty_settings = difficulty_settings
        
        # 游戏状态
        self.state = GameplayState.LOADING
        self.notes: List[Note] = []
        self.active_notes: List[Note] = []
        self.note_index = 0
        
        # 分数系统
        self.score_info = ScoreInfo()
        
        # 时间管理
        self.current_time = 0.0
        self.song_start_time = 0.0
        self.paused_time = 0.0
        self.audio_offset = 0  # 音频偏移，毫秒
        
        # 游戏参数
        self.judgement_window = JudgementWindow.default()
        self.scroll_speed = difficulty_settings.get("scroll_speed", 1.0)
        self.input_offset = difficulty_settings.get("input_offset", 0)  # 输入偏移，毫秒
        
        # 轨道配置
        self.column_count = 4
        self.column_positions = self._calculate_column_positions()
        
        # 音频管理
        self.audio_playing = False
        self.audio_start_time = 0.0
        
        # 回调函数
        self.on_judgement_callback: Optional[Callable[[Judgement, float, Note], None]] = None
        self.on_combo_break_callback: Optional[Callable[[], None]] = None
        
        # 加载谱面
        self._load_chart()
    
    def _calculate_column_positions(self) -> List[float]:
        """计算轨道位置"""
        positions = []
        total_width = 1.6
        column_width = total_width / self.column_count
        
        for i in range(self.column_count):
            x = -0.8 + column_width * (i + 0.5)
            positions.append(x)
        
        return positions
    
    def _load_chart(self):
        """加载谱面数据"""
        try:
            # 解析元数据
            meta = self.chart_data.get("meta", {})
            song = meta.get("song", {})
            
            # 获取音频偏移
            self.audio_offset = 0
            for note_data in self.chart_data.get("note", []):
                if note_data.get("type") == 1:  # 音频文件类型
                    self.audio_offset = note_data.get("offset", 0)
                    break
            
            # 解析BPM变化
            bpm_changes = []
            for time_point in self.chart_data.get("time", []):
                beat = time_point["beat"]
                bpm = time_point["bpm"]
                bpm_changes.append({
                    "beat": (beat[0], beat[1], beat[2]),
                    "bpm": bpm
                })
            
            # 解析音符
            notes = []
            for i, note_data in enumerate(self.chart_data.get("note", [])):
                # 跳过音频引用
                if note_data.get("type") == 1:
                    continue
                
                beat = note_data["beat"]
                column = note_data.get("column", 0)
                
                # 计算时间
                time_sec = self._beat_to_time(beat, bpm_changes)
                
                # 确定音符类型
                note_type_value = note_data.get("type", 0)
                if note_type_value == 1:
                    note_type = NoteType.HOLD
                elif note_type_value == 2:
                    note_type = NoteType.SLIDE
                elif note_type_value == 3:
                    note_type = NoteType.CHAIN
                else:
                    note_type = NoteType.TAP
                
                # 计算结束时间（对于长按）
                end_time = None
                if note_type == NoteType.HOLD and "end" in note_data:
                    end_beat = note_data["end"]
                    end_time = self._beat_to_time(end_beat, bpm_changes)
                
                note = Note(
                    id=i,
                    start_time=time_sec,
                    end_time=end_time,
                    column=column,
                    note_type=note_type,
                    beat=(beat[0], beat[1], beat[2]),
                    sound=note_data.get("sound"),
                    volume=note_data.get("vol")
                )
                notes.append(note)
            
            # 按开始时间排序
            notes.sort(key=lambda n: n.start_time)
            self.notes = notes
            
            print(f"Loaded {len(self.notes)} notes")
            print(f"Audio offset: {self.audio_offset}ms")
            
            self.state = GameplayState.READY
            
        except Exception as e:
            print(f"Error loading chart: {e}")
            import traceback
            traceback.print_exc()
            self.state = GameplayState.FINISHED
    
    def _beat_to_time(self, beat: List[int], bpm_changes: List[Dict]) -> float:
        """将拍数转换为时间（秒）"""
        measure, numerator, denominator = beat
        beats = measure + numerator / denominator
        
        # 如果没有BPM变化，使用默认BPM
        if not bpm_changes:
            default_bpm = 120.0
            return beats * (60.0 / default_bpm)
        
        # 根据BPM变化计算时间
        time = 0.0
        current_beat = 0.0
        current_bpm = bpm_changes[0]["bpm"]
        
        for change in bpm_changes:
            change_beats = change["beat"][0] + change["beat"][1] / change["beat"][2]
            
            if change_beats <= beats:
                beats_until_change = change_beats - current_beat
                time_until_change = beats_until_change * (60.0 / current_bpm)
                
                time += time_until_change
                current_beat = change_beats
                current_bpm = change["bpm"]
            else:
                break
        
        remaining_beats = beats - current_beat
        time += remaining_beats * (60.0 / current_bpm)
        
        return time
    
    def set_judgement_callback(self, callback: Callable[[Judgement, float, Note], None]):
        """设置判定回调"""
        self.on_judgement_callback = callback
    
    def set_combo_break_callback(self, callback: Callable[[], None]):
        """设置连击中断回调"""
        self.on_combo_break_callback = callback
    
    def start(self, audio_start_time: float = 0.0):
        """开始游戏"""
        if self.state not in [GameplayState.READY, GameplayState.PAUSED]:
            return
        
        self.state = GameplayState.PLAYING
        self.song_start_time = time.time() - audio_start_time
        self.current_time = audio_start_time
        self.note_index = 0
        self.active_notes.clear()
        self.audio_start_time = audio_start_time
        self.audio_playing = True
        
        # 重置分数
        self.score_info = ScoreInfo()
        
        print(f"Game started at time {audio_start_time:.3f}s")
    
    def pause(self):
        """暂停游戏"""
        if self.state == GameplayState.PLAYING:
            self.state = GameplayState.PAUSED
            self.paused_time = time.time()
            self.audio_playing = False
            print("Game paused")
    
    def resume(self):
        """恢复游戏"""
        if self.state == GameplayState.PAUSED:
            self.state = GameplayState.PLAYING
            pause_duration = time.time() - self.paused_time
            self.song_start_time += pause_duration
            self.audio_playing = True
            print("Game resumed")
    
    def update(self, delta_time: float):
        """更新游戏逻辑"""
        if self.state != GameplayState.PLAYING:
            return
        
        # 更新时间
        self.current_time = time.time() - self.song_start_time
        
        # 添加新音符到活动列表
        while self.note_index < len(self.notes):
            note = self.notes[self.note_index]
            if note.is_active(self.current_time, self.judgement_window.bad / 1000):
                self.active_notes.append(note)
                self.note_index += 1
            else:
                break
        
        # 更新长按音符进度
        for note in self.active_notes:
            if note.note_type == NoteType.HOLD and note.end_time:
                if note.hit and not note.missed:
                    current = min(self.current_time, note.end_time)
                    progress = (current - note.start_time) / (note.end_time - note.start_time)
                    note.hold_progress = max(0.0, min(1.0, progress))
                    
                    # 检查长按是否结束
                    if self.current_time >= note.end_time:
                        note.hit = True
                        note.hold_progress = 1.0
        
        # 移除已处理或过期的音符
        self.active_notes = [
            note for note in self.active_notes
            if note.is_active(self.current_time, self.judgement_window.bad / 1000)
        ]
        
        # 检查未命中
        for note in list(self.active_notes):
            if not note.hit and not note.missed:
                # 计算最晚命中时间
                latest_hit_time = note.start_time + (self.judgement_window.bad / 1000)
                
                # 对于长按音符，需要持续按住
                if note.note_type == NoteType.HOLD and note.end_time:
                    if self.current_time > note.end_time + (self.judgement_window.bad / 1000):
                        note.missed = True
                        self._on_note_missed(note)
                elif self.current_time > latest_hit_time:
                    note.missed = True
                    self._on_note_missed(note)
    
    def handle_input(self, column: int, pressed: bool, current_time: float = None):
        """处理输入"""
        if self.state != GameplayState.PLAYING:
            return
        
        if current_time is None:
            current_time = self.current_time
        
        # 应用输入偏移
        adjusted_time = current_time + (self.input_offset / 1000)
        
        if pressed:
            self._handle_key_press(column, adjusted_time)
        else:
            self._handle_key_release(column, adjusted_time)
    
    def _handle_key_press(self, column: int, current_time: float):
        """处理按键按下"""
        # 查找最接近的音符
        best_note = None
        best_diff = float('inf')
        
        for note in self.active_notes:
            if (note.column == column and 
                not note.hit and 
                not note.missed and
                note.note_type != NoteType.HOLD):  # 长按音符有特殊处理
                
                # 对于滑动和连打音符，可能需要不同的判定逻辑
                diff = abs(note.start_time - current_time)
                if diff < best_diff:
                    best_diff = diff
                    best_note = note
        
        if best_note:
            self._on_note_hit(best_note, best_diff)
        
        # 检查长按音符的开始
        for note in self.active_notes:
            if (note.column == column and 
                note.note_type == NoteType.HOLD and
                not note.hit and 
                not note.missed):
                
                diff = abs(note.start_time - current_time)
                if diff <= self.judgement_window.bad / 1000:
                    note.hit = True
                    note.hit_time = current_time
                    note.hold_progress = 0.0
                    
                    judgement, accuracy = self.judgement_window.judge(diff)
                    note.accuracy = accuracy
                    self.score_info.add_judgement(judgement, accuracy)
                    
                    if self.on_judgement_callback:
                        self.on_judgement_callback(judgement, accuracy, note)
                    
                    print(f"Held note started: {judgement} (diff: {diff:.3f}s)")
    
    def _handle_key_release(self, column: int, current_time: float):
        """处理按键释放"""
        # 检查长按音符的结束
        for note in self.active_notes:
            if (note.column == column and 
                note.note_type == NoteType.HOLD and
                note.hit and 
                not note.missed and
                note.end_time):
                
                # 检查是否在正确的时间释放
                expected_end = note.end_time
                diff = abs(expected_end - current_time)
                
                if diff <= self.judgement_window.bad / 1000:
                    # 成功完成长按
                    note.hold_progress = 1.0
                    
                    judgement, accuracy = self.judgement_window.judge(diff)
                    self.score_info.add_judgement(judgement, accuracy)
                    
                    if self.on_judgement_callback:
                        self.on_judgement_callback(judgement, accuracy, note)
                    
                    print(f"Held note completed: {judgement} (diff: {diff:.3f}s)")
                else:
                    # 过早释放
                    note.missed = True
                    self._on_note_missed(note)
    
    def _on_note_hit(self, note: Note, diff: float):
        """处理音符命中"""
        note.hit = True
        note.hit_time = self.current_time
        
        judgement, accuracy = self.judgement_window.judge(diff)
        note.accuracy = accuracy
        self.score_info.add_judgement(judgement, accuracy)
        
        if self.on_judgement_callback:
            self.on_judgement_callback(judgement, accuracy, note)
        
        print(f"Hit note: {judgement} (diff: {diff:.3f}s, accuracy: {accuracy:.2f})")
    
    def _on_note_missed(self, note: Note):
        """处理音符未命中"""
        note.missed = True
        self.score_info.add_judgement(Judgement.MISS)
        
        if self.on_combo_break_callback and self.score_info.combo > 10:
            self.on_combo_break_callback()
        
        print("Missed note")
    
    def get_render_objects(self) -> List[Dict]:
        """获取需要渲染的对象"""
        objects = []
        
        # 渲染轨道
        for i, pos in enumerate(self.column_positions):
            objects.append({
                "type": "rectangle",
                "position": [pos, -0.8],
                "size": [0.15, 1.6],
                "color": [0.3, 0.3, 0.3, 1.0],
                "layer": 0,
            })
        
        # 渲染音符
        for note in self.active_notes:
            if note.hit or note.missed:
                continue
            
            column = note.column
            if column < 0 or column >= len(self.column_positions):
                continue
            
            x = self.column_positions[column]
            y = note.get_y_position(self.current_time, self.scroll_speed)
            
            if -1.0 <= y <= 1.0:  # 只在屏幕内渲染
                # 根据音符类型选择颜色
                if note.note_type == NoteType.TAP:
                    color = [1.0, 0.5, 0.0, 1.0]
                    size = [0.1, 0.1]
                elif note.note_type == NoteType.HOLD:
                    color = [0.0, 0.8, 1.0, 1.0]
                    hold_length = note.get_hold_length(self.current_time, self.scroll_speed)
                    size = [0.08, max(0.05, hold_length)]
                    
                    # 调整Y位置（长按音符的中心）
                    y = y - hold_length / 2
                elif note.note_type == NoteType.SLIDE:
                    color = [0.8, 0.2, 0.8, 1.0]
                    size = [0.1, 0.1]
                else:  # CHAIN
                    color = [1.0, 0.8, 0.0, 1.0]
                    size = [0.1, 0.1]
                
                objects.append({
                    "type": "rectangle",
                    "position": [x, y],
                    "size": size,
                    "color": color,
                    "layer": 1,
                })
                
                # 对于长按音符，渲染进度条
                if note.note_type == NoteType.HOLD and note.hit and note.hold_progress > 0:
                    progress_height = hold_length * note.hold_progress
                    objects.append({
                        "type": "rectangle",
                        "position": [x, y + hold_length / 2 - progress_height / 2],
                        "size": [0.08, progress_height],
                        "color": [0.2, 1.0, 0.2, 0.7],
                        "layer": 2,
                    })
        
        # 渲染判定线
        objects.append({
            "type": "rectangle",
            "position": [0.0, -0.8],
            "size": [1.6, 0.02],
            "color": [1.0, 1.0, 1.0, 0.8],
            "layer": 0,
        })
        
        # 渲染连击显示
        if self.score_info.combo > 0:
            objects.append({
                "type": "text",
                "text": f"{self.score_info.combo}",
                "position": [0.0, 0.5],
                "size": 0.1,
                "color": [1.0, 1.0, 1.0, 1.0],
                "layer": 3,
            })
        
        # 渲染准确率
        objects.append({
            "type": "text",
            "text": f"{self.score_info.accuracy:.2f}%",
            "position": [0.7, 0.8],
            "size": 0.05,
            "color": [1.0, 1.0, 1.0, 1.0],
            "layer": 3,
        })
        
        return objects
    
    def get_score_info(self) -> ScoreInfo:
        """获取分数信息"""
        return self.score_info
    
    def get_gameplay_state(self) -> GameplayState:
        """获取游戏状态"""
        return self.state
    
    def get_current_time(self) -> float:
        """获取当前游戏时间"""
        return self.current_time
    
    def get_progress(self) -> float:
        """获取游戏进度 (0.0-1.0)"""
        if not self.notes:
            return 0.0
        
        total_duration = self.notes[-1].start_time + 5.0  # 加上5秒缓冲
        return min(1.0, self.current_time / total_duration)
    
    def is_finished(self) -> bool:
        """检查游戏是否结束"""
        if self.state == GameplayState.FINISHED:
            return True
        
        # 检查是否所有音符都已处理
        all_notes_processed = all(n.hit or n.missed for n in self.notes)
        
        # 检查是否已过最后音符一定时间
        if self.notes:
            last_note_time = max(n.end_time or n.start_time for n in self.notes)
            time_after_last_note = self.current_time - last_note_time
            
            if all_notes_processed and time_after_last_note > 3.0:
                self.state = GameplayState.FINISHED
                self._calculate_final_score()
                return True
        
        return False
    
    def _calculate_final_score(self):
        """计算最终分数和评级"""
        self.score_info.grade = self.score_info.calculate_grade()
        
        print(f"Game finished!")
        print(f"  Score: {self.score_info.score}")
        print(f"  Max Combo: {self.score_info.max_combo}")
        print(f"  Accuracy: {self.score_info.accuracy:.2f}%")
        print(f"  Grade: {self.score_info.grade}")
        print(f"  Judgements:")
        for judgement in Judgement:
            count = self.score_info.judgements[judgement]
            if count > 0:
                print(f"    {judgement.name}: {count}")
    
    def set_scroll_speed(self, speed: float):
        """设置下落速度"""
        self.scroll_speed = max(0.1, min(5.0, speed))
    
    def set_input_offset(self, offset_ms: int):
        """设置输入偏移"""
        self.input_offset = offset_ms

# Mod入口点
def create_gameplay(chart_data: Dict[str, Any], difficulty_settings: Dict[str, Any]) -> Gameplay4K:
    """创建游戏实例（供核心调用）"""
    return Gameplay4K(chart_data, difficulty_settings)

def get_mod_info() -> Dict[str, Any]:
    """获取Mod信息"""
    return {
        "name": "4K下落式玩法",
        "version": "1.0.0",
        "author": "OpenRhythm Team",
        "description": "支持Malody谱面格式的4键下落式音游玩法",
        "supported_modes": [0],  # 4K模式
        "features": ["tap", "hold", "slide", "chain"],
    }