# mystia_rhythm/core/game_engine.py
"""
游戏引擎主循环
管理游戏状态、更新和渲染
"""
import logging
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import threading
import time
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line, Ellipse

from .timing import GameClock, TimingSystem
from .audio_manager import AudioManager
from .chart_parser import Chart, Note, NoteType
from .judgment_system import JudgmentSystem, Judgment, JudgmentResult
from config import config
from ui.play_ui import PlayUI


# 配置日志
logger = logging.getLogger(__name__)

class GameState(Enum):
    """游戏状态"""
    LOADING = 0
    MENU = 1
    SONG_SELECT = 2
    PLAYING = 3
    PAUSED = 4
    RESULT = 5
    EDITOR = 6


class GameEngine:
    """
    游戏引擎
    管理游戏主循环和状态
    """
    
    def __init__(self, app: App):
        logger.info("初始化游戏引擎")
        self.app = app
        self.state = GameState.LOADING
        
        # 时间系统
        self.clock = GameClock()
        
        # 音频系统
        self.audio = AudioManager(config)
        
        # 谱面数据
        self.current_chart: Optional[Chart] = None
        
        # 判定系统
        self.judgment = JudgmentSystem()
        
        # 游玩参数
        self.scroll_speed = config.get('gameplay.scroll_speed', 1.0)
        self.note_size = config.get('gameplay.note_size', 1.0)
        self.lanes = config.get('gameplay.lanes', 4)
        
        # 当前游戏数据
        self.current_time = 0.0
        self.is_playing = False
        self.keys_pressed = [False] * self.lanes
        
        # 音符数据
        self.notes: List[Note] = []
        self.note_times: List[float] = []  # 每个音符的时间
        self.note_positions: List[float] = []  # 每个音符的屏幕位置
        
        # 回调函数
        self.callbacks: Dict[str, List[Callable]] = {
            'on_note_hit': [],
            'on_note_miss': [],
            'on_combo_change': [],
            'on_score_change': [],
            'on_game_start': [],
            'on_game_end': [],
            'on_state_change': []
        }
        
        # UI引用
        self.play_ui: Optional[PlayUI] = None
        
        # 当前谱面文件路径（用于查找背景等资源）
        self.current_chart_path: Optional[Path] = None
        
        # 设置窗口事件
        Window.bind(on_key_down=self._on_key_down)
        Window.bind(on_key_up=self._on_key_up)
        Window.bind(on_touch_down=self._on_touch_down)
        Window.bind(on_touch_up=self._on_touch_up)
        
        logger.debug(f"游戏参数 - 轨道: {self.lanes}, 滚动速度: {self.scroll_speed}, 音符大小: {self.note_size}")
        
    def load_chart(self, chart: Chart) -> bool:
        """加载谱面"""
        logger.info(f"加载谱面: {chart.metadata.title} - {chart.metadata.artist}")
        logger.debug(f"音符数量: {len(chart.notes)}")
        
        self.current_chart = chart
        self.notes = chart.notes
        
        # 计算每个音符的时间
        self.note_times = []
        self.note_positions = []
        
        for note in self.notes:
            note_time = chart.timing_system.beat_to_time(note.beat)
            self.note_times.append(note_time)
            
            # 如果是长按，也计算结束时间
            if note.endbeat:
                end_time = chart.timing_system.beat_to_time(note.endbeat)
                note.duration = end_time - note_time
            else:
                note.duration = 0.0
                
        # 重置游戏状态
        self.reset_game()
        
        # 加载音频
        if chart.metadata.audio_path:
            logger.debug(f"音频文件: {chart.metadata.audio_path}")
            audio_loaded = self.audio.load_music(chart.metadata.audio_path)
            if not audio_loaded:
                logger.warning(f"音频加载失败: {chart.metadata.audio_path}")
                
        logger.info(f"谱面加载完成")
        return True
        
    def reset_game(self) -> None:
        """重置游戏状态"""
        logger.info("重置游戏状态")
        self.current_time = 0.0
        self.is_playing = False
        self.keys_pressed = [False] * self.lanes
        self.judgment.reset()
        
        # 重置时钟
        self.clock.reset()
        
    def start_game(self) -> None:
        """开始游戏"""
        logger.info("游戏开始")
        if not self.current_chart:
            logger.error("没有加载谱面，无法开始游戏")
            return
            
        self.reset_game()
        self.is_playing = True
        self.audio.play_music()
        self._trigger_callbacks('on_game_start')
        self.change_state(GameState.PLAYING)
        logger.debug("游戏状态: 游玩中")
        
    def pause_game(self) -> None:
        """暂停游戏"""
        logger.info("游戏暂停")
        if not self.is_playing:
            logger.debug("游戏未在运行中")
            return
            
        self.is_playing = False
        self.clock.pause()
        self.audio.pause_music()
        self.change_state(GameState.PAUSED)
        logger.debug("游戏状态: 暂停")
        
    def resume_game(self) -> None:
        """恢复游戏"""
        logger.info("游戏恢复")
        if self.is_playing:
            logger.debug("游戏已在运行中")
            return
            
        self.is_playing = True
        self.clock.resume()
        self.audio.resume_music()
        self.change_state(GameState.PLAYING)
        logger.debug("游戏状态: 游玩中")
        
    def end_game(self) -> None:
        """结束游戏"""
        logger.info(f"游戏结束 - 分数: {self.judgment.get_score()}, 准确率: {self.judgment.get_accuracy():.2f}%")
        self.is_playing = False
        self.audio.stop_music()
        self._trigger_callbacks('on_game_end')
        self.change_state(GameState.RESULT)
        logger.debug("游戏状态: 结算")
        
        # 切换到结算界面
        if self.app and self.app.screen_manager:
            self.app.screen_manager.current = 'result'
        
    def update(self, dt: float) -> None:
        """更新游戏逻辑"""
        # 更新时钟
        self.clock.update(dt)
        
        # 如果不在游玩状态，跳过
        if not self.is_playing or self.state != GameState.PLAYING:
            return
            
        # 更新当前时间
        self.current_time = self.clock.game_time
        
        # 检查游戏是否应该结束（音乐播放完毕）
        if self.current_chart and self.current_chart.metadata.duration:
            if self.current_time >= self.current_chart.metadata.duration + 1.0:
                logger.info("音乐播放完毕，游戏结束")
                self.end_game()
                
        # 更新音符位置和判定
        self._update_notes()
        
        # 更新UI
        if self.play_ui:
            self.play_ui.update(self.current_time)
            
    def _update_notes(self) -> None:
        """更新音符状态"""
        if not self.current_chart:
            return
            
        # 获取当前时间和判定窗口
        current_time = self.current_time
        judgment_window = self.judgment.windows.good / 1000.0  # 转换为秒
        
        # 检查每个音符
        for i, note in enumerate(self.notes):
            note_time = self.note_times[i]
            
            # 如果音符已经经过判定窗口，自动判定为MISS
            if current_time > note_time + judgment_window and i not in self.judgment.judged_notes:
                # 自动MISS
                result = self.judgment.calculator.add_judgment(Judgment.MISS)
                result.offset = (current_time - note_time) * 1000
                self.judgment.judged_notes[i] = result
                
                # 触发回调
                self._trigger_callbacks('on_note_miss', result)
                self._trigger_callbacks('on_combo_change', self.judgment.get_combo())
                self._trigger_callbacks('on_score_change', self.judgment.get_score())
                
    def handle_input(self, lane: int, pressed: bool) -> None:
        """
        处理输入
        
        Args:
            lane: 轨道编号 (0-3)
            pressed: 是否按下
        """
        if not self.is_playing or lane < 0 or lane >= self.lanes:
            return
            
        self.keys_pressed[lane] = pressed
        
        # 如果按下，检查是否有可判定的音符
        if pressed:
            self._check_note_hit(lane)
            
    def _check_note_hit(self, lane: int) -> None:
        """检查指定轨道上的音符命中"""
        if not self.current_chart:
            return
            
        current_time = self.current_time
        judgment_window = self.judgment.windows.good / 1000.0
        
        # 查找在判定窗口内的音符
        for i, note in enumerate(self.notes):
            # 只检查指定轨道的音符
            if note.column != lane:
                continue
                
            # 跳过已判定的音符
            if i in self.judgment.judged_notes:
                continue
                
            note_time = self.note_times[i]
            time_diff = abs(current_time - note_time)
            
            # 如果在判定窗口内
            if time_diff <= judgment_window:
                # 进行判定
                result = self.judgment.judge_note(note, current_time, note_time, True)
                if result:
                    self.judgment.judged_notes[i] = result
                    
                    # 触发回调
                    self._trigger_callbacks('on_note_hit', result)
                    self._trigger_callbacks('on_combo_change', self.judgment.get_combo())
                    self._trigger_callbacks('on_score_change', self.judgment.get_score())
                    
                    # 播放判定音效
                    if note.sound:
                        self.audio.play_sound(note.sound, note.volume)
                    break
                    
    def change_state(self, new_state: GameState) -> None:
        """改变游戏状态"""
        old_state = self.state
        self.state = new_state
        
        # 触发回调
        self._trigger_callbacks('on_state_change', old_state, new_state)
        
    def register_callback(self, event: str, callback: Callable) -> None:
        """注册回调函数"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)
            
    def unregister_callback(self, event: str, callback: Callable) -> None:
        """取消注册回调函数"""
        if event in self.callbacks:
            if callback in self.callbacks[event]:
                self.callbacks[event].remove(callback)
                
    def _trigger_callbacks(self, event: str, *args, **kwargs) -> None:
        """触发回调函数"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    logger.error(f"回调函数执行失败 {event}: {e}")
                    
    def _on_key_down(self, window, key, scancode, codepoint, modifiers) -> bool:
        """处理键盘按下事件"""
        # 获取键位映射
        key_layout = config.get('gameplay.key_layout', 'standard')
        key_map = self._get_key_map(key_layout)
        
        # 检查是否按下对应轨道的键
        for lane, keys in key_map.items():
            if key in keys:
                self.handle_input(lane, True)
                return True
                
        # 其他功能键
        if key == 27:  # ESC
            if self.state == GameState.PLAYING:
                self.pause_game()
            elif self.state == GameState.PAUSED:
                self.resume_game()
            return True
            
        elif key == 32:  # 空格
            if self.state == GameState.PLAYING:
                self.pause_game()
            elif self.state == GameState.PAUSED:
                self.resume_game()
            return True
            
        return False
        
    def _on_key_up(self, window, key, scancode) -> bool:
        """处理键盘释放事件"""
        key_layout = config.get('gameplay.key_layout', 'standard')
        key_map = self._get_key_map(key_layout)
        
        for lane, keys in key_map.items():
            if key in keys:
                self.handle_input(lane, False)
                return True
                
        return False
        
    def _on_touch_down(self, window, touch):
        """处理触摸按下事件"""
        # 在移动端，需要将触摸位置映射到轨道
        if self.play_ui:
            lane = self.play_ui.get_lane_from_touch(touch.x, touch.y)
            if lane is not None:
                self.handle_input(lane, True)
                touch.ud['lane'] = lane
                return True
        return False
        
    def _on_touch_up(self, window, touch):
        """处理触摸释放事件"""
        if 'lane' in touch.ud:
            lane = touch.ud['lane']
            self.handle_input(lane, False)
            return True
        return False
        
    def _get_key_map(self, layout: str) -> Dict[int, List[int]]:
        """获取键位映射"""
        # 标准键位：DFJK
        if layout == 'standard':
            return {
                0: [100],  # D
                1: [102],  # F
                2: [106],  # J
                3: [107],  # K
            }
        # WASD
        elif layout == 'wasd':
            return {
                0: [97],   # A
                1: [119],  # W
                2: [115],  # S
                3: [100],  # D
            }
        # 方向键
        elif layout == 'arrows':
            return {
                0: [276],  # 左
                1: [273],  # 上
                2: [274],  # 下
                3: [275],  # 右
            }
        # 默认返回标准键位
        return {
            0: [100],
            1: [102],
            2: [106],
            3: [107],
        }