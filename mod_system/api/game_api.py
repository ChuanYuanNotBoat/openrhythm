# mystia_rhythm/mod_system/api/game_api.py
"""
游戏控制API
提供给Mod的游戏控制接口
"""
from typing import Dict, List, Optional, Any
from enum import Enum

from mod_system.permission_system import Permission


class GameState(Enum):
    """游戏状态（与核心一致）"""
    LOADING = 0
    MENU = 1
    SONG_SELECT = 2
    PLAYING = 3
    PAUSED = 4
    RESULT = 5
    EDITOR = 6


class GameAPI:
    """游戏控制API"""
    
    def __init__(self, mod_instance):
        self.mod_instance = mod_instance
        self.game_engine = mod_instance.game_engine
        
    def get_game_state(self) -> GameState:
        """获取当前游戏状态"""
        return GameState(self.game_engine.state.value)
        
    def pause_game(self) -> bool:
        """暂停游戏"""
        if not self._check_permission(Permission.PAUSE_GAME):
            return False
            
        self.game_engine.pause_game()
        return True
        
    def resume_game(self) -> bool:
        """恢复游戏"""
        if not self._check_permission(Permission.PAUSE_GAME):
            return False
            
        self.game_engine.resume_game()
        return True
        
    def restart_game(self) -> bool:
        """重新开始游戏"""
        if not self._check_permission(Permission.RESTART_GAME):
            return False
            
        self.game_engine.reset_game()
        self.game_engine.start_game()
        return True
        
    def exit_game(self) -> bool:
        """退出游戏"""
        if not self._check_permission(Permission.EXIT_GAME):
            return False
            
        # 触发游戏结束
        self.game_engine.end_game()
        return True
        
    def get_current_time(self) -> float:
        """获取当前游戏时间（秒）"""
        return self.game_engine.current_time
        
    def get_score(self) -> int:
        """获取当前分数"""
        return self.game_engine.judgment.get_score()
        
    def set_score(self, score: int) -> bool:
        """设置分数（用于RPG Mod等）"""
        if not self._check_permission(Permission.MODIFY_SCORE):
            return False
            
        # 注意：直接修改分数可能会影响游戏平衡
        # 这里只是示例，实际应用中可能需要更复杂的逻辑
        self.game_engine.judgment.calculator.score = score
        return True
        
    def get_combo(self) -> int:
        """获取当前连击"""
        return self.game_engine.judgment.get_combo()
        
    def set_combo(self, combo: int) -> bool:
        """设置连击数"""
        if not self._check_permission(Permission.MODIFY_COMBO):
            return False
            
        self.game_engine.judgment.calculator.combo = combo
        self.game_engine.judgment.calculator.max_combo = max(
            self.game_engine.judgment.calculator.max_combo, combo
        )
        return True
        
    def get_accuracy(self) -> float:
        """获取当前准确率"""
        return self.game_engine.judgment.get_accuracy()
        
    def get_judgment_counts(self) -> Dict[str, int]:
        """获取判定统计"""
        from ...core.judgment_system import Judgment
        counts = self.game_engine.judgment.calculator.judgments
        
        return {
            'BEST': counts.get(Judgment.BEST, 0),
            'COOL': counts.get(Judgment.COOL, 0),
            'GOOD': counts.get(Judgment.GOOD, 0),
            'MISS': counts.get(Judgment.MISS, 0)
        }
        
    def get_current_chart_info(self) -> Optional[Dict[str, Any]]:
        """获取当前谱面信息"""
        if not self.game_engine.current_chart:
            return None
            
        meta = self.game_engine.current_chart.metadata
        return {
            'title': meta.title,
            'artist': meta.artist,
            'charter': meta.charter,
            'difficulty': meta.difficulty,
            'level': meta.level,
            'bpm': meta.bpm,
            'duration': meta.duration if hasattr(meta, 'duration') else 0
        }
        
    def register_callback(self, event: str, callback) -> bool:
        """注册回调函数"""
        # 检查事件是否有效
        valid_events = [
            'on_note_hit', 'on_note_miss', 'on_combo_change',
            'on_score_change', 'on_game_start', 'on_game_end',
            'on_state_change'
        ]
        
        if event not in valid_events:
            return False
            
        self.game_engine.register_callback(event, callback)
        return True
        
    def unregister_callback(self, event: str, callback) -> bool:
        """取消注册回调函数"""
        self.game_engine.unregister_callback(event, callback)
        return True
        
    def _check_permission(self, permission: Permission) -> bool:
        """检查权限"""
        # 从Mod管理器获取权限管理器
        mod_manager = self.game_engine.mod_manager
        if hasattr(mod_manager, 'permission_manager'):
            return mod_manager.permission_manager.check_permission(
                self.mod_instance.manifest.mod_id, permission
            )
        return False