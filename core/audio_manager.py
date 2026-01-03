# mystia_rhythm/core/audio_manager.py
"""
音频管理系统
支持多音频轨道、延迟补偿和音效池
"""
import logging
import threading
import queue
import time
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

try:
    from kivy.core.audio import SoundLoader
    KIVY_AUDIO_AVAILABLE = True
except ImportError:
    KIVY_AUDIO_AVAILABLE = False
    
try:
    import pygame.mixer
    PYGAME_AUDIO_AVAILABLE = True
except ImportError:
    PYGAME_AUDIO_AVAILABLE = False


class AudioBackend(Enum):
    """音频后端"""
    KIVY = "kivy"
    PYGAME = "pygame"
    OPENAL = "openal"  # 预留


class AudioError(Exception):
    """音频错误"""
    pass


class AudioClip:
    """音频片段"""
    
    def __init__(self, path: Path, backend: AudioBackend = AudioBackend.KIVY):
        self.path = path
        self.backend = backend
        self._sound = None
        self.loaded = False
        self.duration = 0.0
        
    def load(self) -> bool:
        """加载音频"""
        try:
            if self.backend == AudioBackend.KIVY and KIVY_AUDIO_AVAILABLE:
                self._sound = SoundLoader.load(str(self.path))
                if self._sound:
                    self.loaded = True
                    # Kivy Sound没有直接提供时长，需要估算
                    self.duration = getattr(self._sound, 'length', 0)
                    return True
                    
            elif self.backend == AudioBackend.PYGAME and PYGAME_AUDIO_AVAILABLE:
                # pygame需要初始化
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                self._sound = pygame.mixer.Sound(str(self.path))
                self.loaded = True
                self.duration = self._sound.get_length()
                return True
                
        except Exception as e:
            logger.error(f"音频加载失败 {self.path}: {e}")
            
        return False
        
    def play(self, start_time: float = 0.0, volume: float = 1.0) -> bool:
        """播放音频"""
        if not self.loaded:
            if not self.load():
                return False
                
        try:
            if self.backend == AudioBackend.KIVY:
                self._sound.volume = volume
                self._sound.play()
                if start_time > 0:
                    # Kivy不支持直接跳转，需要重新加载或使用其他方法
                    pass
                    
            elif self.backend == AudioBackend.PYGAME:
                self._sound.set_volume(volume)
                channel = self._sound.play()
                if channel and start_time > 0:
                    channel.set_pos(start_time)
                    
            return True
            
        except Exception as e:
            logger.error(f"音频播放失败: {e}")
            return False
            
    def stop(self) -> None:
        """停止播放"""
        if self.loaded and self._sound:
            try:
                self._sound.stop()
            except:
                pass
                
    def set_volume(self, volume: float) -> None:
        """设置音量"""
        if self.loaded and self._sound:
            try:
                self._sound.volume = volume
            except:
                pass


class AudioManager:
    """
    音频管理器
    处理背景音乐、音效和同步
    """
    
    def __init__(self, config):
        logger.info("初始化音频管理器")
        self.config = config
        
        try:
            self.backend = self._detect_backend()
            logger.info(f"音频后端: {self.backend.value}")
        except Exception as e:
            logger.error(f"音频后端检测失败: {e}")
            raise
            
        self.music: Optional[AudioClip] = None
        self.sounds: Dict[str, AudioClip] = {}  # 音效池
        self.sound_queue = queue.Queue()
        self.worker_thread = None
        self.running = False
        
        # 音频同步参数
        self.latency = config.get('audio.audio_latency', 0.05)
        self.master_volume = config.get('audio.volume_master', 0.8)
        self.music_volume = config.get('audio.volume_music', 1.0)
        self.effect_volume = config.get('audio.volume_effect', 1.0)
        
        logger.debug(f"音频参数 - 延迟: {self.latency}s, 主音量: {self.master_volume}")
        
    def _detect_backend(self) -> AudioBackend:
        """检测可用的音频后端"""
        backend = self.config.get('audio.audio_backend', 'auto')
        
        if backend == 'kivy' and KIVY_AUDIO_AVAILABLE:
            return AudioBackend.KIVY
        elif backend == 'pygame' and PYGAME_AUDIO_AVAILABLE:
            return AudioBackend.PYGAME
        elif backend == 'auto':
            if KIVY_AUDIO_AVAILABLE:
                return AudioBackend.KIVY
            elif PYGAME_AUDIO_AVAILABLE:
                return AudioBackend.PYGAME
                
        raise AudioError("没有可用的音频后端")
        
    def start(self) -> None:
        """启动音频管理器"""
        self.running = True
        self.worker_thread = threading.Thread(target=self._audio_worker, daemon=True)
        self.worker_thread.start()
        
    def stop(self) -> None:
        """停止音频管理器"""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=1.0)
            
        if self.music:
            self.music.stop()
            
        for sound in self.sounds.values():
            sound.stop()
            
    def load_music(self, path: Path) -> bool:
        """加载背景音乐"""
        logger.info(f"加载音乐: {path}")
        if self.music:
            self.music.stop()
            
        self.music = AudioClip(path, self.backend)
        success = self.music.load()
        
        if success:
            logger.debug(f"音乐加载成功 - 时长: {self.music.duration:.2f}s")
        else:
            logger.error(f"音乐加载失败: {path}")
            
        return success
        
    def play_music(self, start_time: float = 0.0, loop: bool = False) -> bool:
        """播放背景音乐"""
        if not self.music:
            logger.error("没有加载音乐")
            return False
            
        logger.info(f"播放音乐 (start_time={start_time}s, loop={loop})")
        success = self.music.play(start_time, self.master_volume * self.music_volume)
        
        if success:
            logger.debug("音乐播放成功")
        else:
            logger.error("音乐播放失败")
            
        return success
        
    def pause_music(self) -> None:
        """暂停背景音乐"""
        if self.music and self.music.loaded:
            if self.backend == AudioBackend.KIVY:
                self.music._sound.pause()
            elif self.backend == AudioBackend.PYGAME:
                pygame.mixer.pause()
                
    def resume_music(self) -> None:
        """恢复背景音乐"""
        if self.music and self.music.loaded:
            if self.backend == AudioBackend.KIVY:
                self.music._sound.play()
            elif self.backend == AudioBackend.PYGAME:
                pygame.mixer.unpause()
                
    def seek_music(self, time_sec: float) -> bool:
        """跳转音乐位置"""
        # 注意：这可能需要重新加载音乐
        if self.music:
            self.stop_music()
            return self.play_music(time_sec)
        return False
        
    def stop_music(self) -> None:
        """停止背景音乐"""
        logger.info("停止音乐")
        if self.music:
            self.music.stop()
            
    def load_sound(self, name: str, path: Path) -> bool:
        """加载音效"""
        sound = AudioClip(path, self.backend)
        if sound.load():
            self.sounds[name] = sound
            return True
        return False
        
    def play_sound(self, name: str, volume: float = 1.0) -> None:
        """播放音效（异步）"""
        self.sound_queue.put((name, volume))
        
    def set_volume(self, master: Optional[float] = None, 
                   music: Optional[float] = None, 
                   effect: Optional[float] = None) -> None:
        """设置音量"""
        if master is not None:
            self.master_volume = max(0.0, min(1.0, master))
            self.config.set('audio.volume_master', self.master_volume)
            
        if music is not None:
            self.music_volume = max(0.0, min(1.0, music))
            self.config.set('audio.volume_music', self.music_volume)
            
        if effect is not None:
            self.effect_volume = max(0.0, min(1.0, effect))
            self.config.set('audio.volume_effect', self.effect_volume)
            
        # 更新当前音乐音量
        if self.music:
            self.music.set_volume(self.master_volume * self.music_volume)
            
    def get_music_position(self) -> float:
        """获取音乐当前位置（秒）"""
        if not self.music or not self.music.loaded:
            return 0.0
            
        if self.backend == AudioBackend.KIVY:
            # Kivy没有直接获取位置的方法
            return 0.0
        elif self.backend == AudioBackend.PYGAME:
            return pygame.mixer.music.get_pos() / 1000.0
            
        return 0.0
        
    def _audio_worker(self) -> None:
        """音频工作线程"""
        while self.running:
            try:
                # 处理音效队列
                while not self.sound_queue.empty():
                    name, volume = self.sound_queue.get_nowait()
                    if name in self.sounds:
                        sound = self.sounds[name]
                        sound.set_volume(self.master_volume * self.effect_volume * volume)
                        sound.play()
                        
                time.sleep(0.01)  # 降低CPU使用
                
            except queue.Empty:
                time.sleep(0.01)
            except Exception as e:
                logger.error(f"音频工作线程错误: {e}")
                time.sleep(0.1)