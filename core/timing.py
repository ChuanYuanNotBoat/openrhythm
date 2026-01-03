# mystia_rhythm/core/timing.py
"""
时间同步和节拍计算系统
处理BPM变化、节拍映射和音画同步
"""
import time
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

@dataclass
class TimeSignature:
    """拍号"""
    numerator: int = 4  # 每小节拍数
    denominator: int = 4  # 音符类型（4=四分音符）
    
@dataclass
class BPMChange:
    """BPM变化点"""
    beat: float  # 拍数位置
    bpm: float   # BPM值
    time: float  # 时间位置（秒，计算后填充）

class TimingSystem:
    """
    时间系统 - 将拍数映射到时间
    
    Malody谱面格式：note.beat = [拍数, 分子, 分母]
    例如 [2, 1, 4] = 第2拍 + 1/4拍 = 2.25拍
    """
    
    def __init__(self, bpm: float = 120.0, time_signature: TimeSignature = None):
        self.bpm = bpm
        self.time_signature = time_signature or TimeSignature()
        self.bpm_changes: List[BPMChange] = []
        self._beat_to_time_cache: Dict[float, float] = {}
        self._time_to_beat_cache: Dict[float, float] = {}
        
    def add_bpm_change(self, beat: float, bpm: float) -> None:
        """添加BPM变化点"""
        self.bpm_changes.append(BPMChange(beat=beat, bpm=bpm, time=0.0))
        self.bpm_changes.sort(key=lambda x: x.beat)
        self._recalculate_timing()
        
    def beat_to_time(self, beat: List[float]) -> float:
        """
        将拍数数组转换为时间（秒）
        
        Args:
            beat: [整数拍, 分子, 分母]，如 [2, 1, 4]
            
        Returns:
            时间（秒）
        """
        # 计算总拍数
        if len(beat) == 3:
            whole, num, den = beat
            total_beat = whole + (num / den)
        else:
            total_beat = float(beat[0])
            
        # 检查缓存
        if total_beat in self._beat_to_time_cache:
            return self._beat_to_time_cache[total_beat]
            
        # 如果没有BPM变化，简单计算
        if not self.bpm_changes:
            time_sec = (total_beat * 60) / self.bpm
            self._beat_to_time_cache[total_beat] = time_sec
            return time_sec
            
        # 处理BPM变化
        current_beat = 0.0
        current_time = 0.0
        current_bpm = self.bpm
        
        # 找到初始BPM
        for change in self.bpm_changes:
            if change.beat <= current_beat:
                current_bpm = change.bpm
                current_time = change.time
            else:
                break
                
        # 分段计算
        for i, change in enumerate(self.bpm_changes):
            if change.beat > total_beat:
                break
                
            # 计算到变化点的拍数
            segment_beats = change.beat - current_beat
            segment_time = (segment_beats * 60) / current_bpm
            current_time += segment_time
            current_beat = change.beat
            current_bpm = change.bpm
            
        # 计算剩余部分
        remaining_beats = total_beat - current_beat
        remaining_time = (remaining_beats * 60) / current_bpm
        total_time = current_time + remaining_time
        
        self._beat_to_time_cache[total_beat] = total_time
        return total_time
        
    def time_to_beat(self, time_sec: float) -> float:
        """将时间（秒）转换为拍数"""
        if time_sec in self._time_to_beat_cache:
            return self._time_to_beat_cache[time_sec]
            
        if not self.bpm_changes:
            beat = (time_sec * self.bpm) / 60
            self._time_to_beat_cache[time_sec] = beat
            return beat
            
        # 处理BPM变化
        current_beat = 0.0
        current_time = 0.0
        current_bpm = self.bpm
        
        for change in self.bpm_changes:
            if change.time <= time_sec:
                current_bpm = change.bpm
                current_time = change.time
                current_beat = change.beat
            else:
                break
                
        remaining_time = time_sec - current_time
        remaining_beats = (remaining_time * current_bpm) / 60
        total_beat = current_beat + remaining_beats
        
        self._time_to_beat_cache[time_sec] = total_beat
        return total_beat
        
    def _recalculate_timing(self) -> None:
        """重新计算BPM变化点的时间位置"""
        self._beat_to_time_cache.clear()
        self._time_to_beat_cache.clear()
        
        if not self.bpm_changes:
            return
            
        # 按拍数排序
        self.bpm_changes.sort(key=lambda x: x.beat)
        
        current_beat = 0.0
        current_time = 0.0
        current_bpm = self.bpm
        
        for change in self.bpm_changes:
            # 计算到变化点的时间
            segment_beats = change.beat - current_beat
            segment_time = (segment_beats * 60) / current_bpm
            current_time += segment_time
            current_beat = change.beat
            
            # 更新变化点的时间
            change.time = current_time
            current_bpm = change.bpm
            
    def get_current_bpm(self, current_time: float) -> float:
        """获取当前时间的BPM"""
        if not self.bpm_changes:
            return self.bpm
            
        for i, change in enumerate(self.bpm_changes):
            if change.time <= current_time:
                if i == len(self.bpm_changes) - 1 or self.bpm_changes[i + 1].time > current_time:
                    return change.bpm
                    
        return self.bpm
        
    def get_beat_phase(self, current_time: float) -> float:
        """获取当前时间在小节中的相位（0-1）"""
        beat = self.time_to_beat(current_time)
        return beat % self.time_signature.numerator / self.time_signature.numerator


class GameClock:
    """
    游戏时钟 - 管理游戏时间，支持暂停、变速
    """
    
    def __init__(self):
        self.real_time = 0.0  # 真实时间
        self.game_time = 0.0  # 游戏时间（受暂停和变速影响）
        self.paused = False
        self.time_scale = 1.0  # 时间缩放
        self.audio_offset = 0.0  # 音频延迟补偿
        
    def update(self, dt: float) -> None:
        """更新时钟"""
        self.real_time += dt
        if not self.paused:
            self.game_time += dt * self.time_scale
            
    def pause(self) -> None:
        """暂停"""
        self.paused = True
        
    def resume(self) -> None:
        """恢复"""
        self.paused = False
        
    def set_time_scale(self, scale: float) -> None:
        """设置时间缩放"""
        self.time_scale = scale
        
    def get_audio_time(self) -> float:
        """获取音频时间（考虑延迟补偿）"""
        return self.game_time + self.audio_offset
        
    def seek(self, time_sec: float) -> None:
        """跳转到指定时间"""
        self.game_time = time_sec
        
    def reset(self) -> None:
        """重置时钟"""
        self.real_time = 0.0
        self.game_time = 0.0
        self.paused = False
        self.time_scale = 1.0