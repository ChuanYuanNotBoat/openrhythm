# mystia_rhythm/mod_system/api/audio_api.py
"""
音频控制API
提供给Mod的音频控制接口
"""
from typing import Dict, List, Optional, Any
from pathlib import Path

from mod_system.permission_system import Permission


class AudioAPI:
    """音频控制API"""
    
    def __init__(self, mod_instance):
        self.mod_instance = mod_instance
        self.game_engine = mod_instance.game_engine
        
    def play_sound(self, sound_name: str, volume: float = 1.0) -> bool:
        """播放音效"""
        if not self._check_permission(Permission.PLAY_SOUND):
            return False
            
        self.game_engine.audio.play_sound(sound_name, volume)
        return True
        
    def load_sound(self, name: str, path: Path) -> bool:
        """加载音效"""
        if not self._check_permission(Permission.ACCESS_AUDIO_STREAM):
            return False
            
        return self.game_engine.audio.load_sound(name, path)
        
    def set_music_volume(self, volume: float) -> bool:
        """设置音乐音量"""
        if not self._check_permission(Permission.MODIFY_AUDIO):
            return False
            
        self.game_engine.audio.set_volume(music=volume)
        return True
        
    def set_effect_volume(self, volume: float) -> bool:
        """设置音效音量"""
        if not self._check_permission(Permission.MODIFY_AUDIO):
            return False
            
        self.game_engine.audio.set_volume(effect=volume)
        return True
        
    def set_master_volume(self, volume: float) -> bool:
        """设置主音量"""
        if not self._check_permission(Permission.MODIFY_AUDIO):
            return False
            
        self.game_engine.audio.set_volume(master=volume)
        return True
        
    def pause_music(self) -> bool:
        """暂停音乐"""
        if not self._check_permission(Permission.MODIFY_AUDIO):
            return False
            
        self.game_engine.audio.pause_music()
        return True
        
    def resume_music(self) -> bool:
        """恢复音乐"""
        if not self._check_permission(Permission.MODIFY_AUDIO):
            return False
            
        self.game_engine.audio.resume_music()
        return True
        
    def stop_music(self) -> bool:
        """停止音乐"""
        if not self._check_permission(Permission.MODIFY_AUDIO):
            return False
            
        self.game_engine.audio.stop_music()
        return True
        
    def seek_music(self, time_sec: float) -> bool:
        """跳转音乐位置"""
        if not self._check_permission(Permission.MODIFY_AUDIO):
            return False
            
        return self.game_engine.audio.seek_music(time_sec)
        
    def get_music_position(self) -> float:
        """获取音乐当前位置"""
        if not self._check_permission(Permission.ACCESS_AUDIO_STREAM):
            return 0.0
            
        return self.game_engine.audio.get_music_position()
        
    def get_music_duration(self) -> float:
        """获取音乐总时长"""
        if not self.game_engine.current_chart:
            return 0.0
            
        # 这里需要从谱面元数据中获取时长
        # 暂时返回0
        return 0.0
        
    def _check_permission(self, permission: Permission) -> bool:
        """检查权限"""
        mod_manager = self.game_engine.mod_manager
        if hasattr(mod_manager, 'permission_manager'):
            return mod_manager.permission_manager.check_permission(
                self.mod_instance.manifest.mod_id, permission
            )
        return False