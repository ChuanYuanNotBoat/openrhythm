# mystia_rhythm/mod_system/api/custom_api.py
"""
自定义数据API
提供给Mod的自定义数据存储接口
"""
import json
from typing import Dict, List, Optional, Any
from pathlib import Path

from mod_system.permission_system import Permission
from config import SAVES_DIR


class CustomAPI:
    """自定义数据API（用于RPG Mod等）"""
    
    def __init__(self, mod_instance):
        self.mod_instance = mod_instance
        self.game_engine = mod_instance.game_engine
        
        # Mod特定的数据目录
        self.mod_data_dir = SAVES_DIR / self.mod_instance.manifest.mod_id
        self.mod_data_dir.mkdir(parents=True, exist_ok=True)
        
    def save_data(self, key: str, data: Any) -> bool:
        """保存自定义数据"""
        if not self._check_permission(Permission.WRITE_FILES):
            return False
            
        try:
            file_path = self.mod_data_dir / f"{key}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存数据失败: {e}")
            return False
            
    def load_data(self, key: str, default: Any = None) -> Any:
        """加载自定义数据"""
        if not self._check_permission(Permission.READ_FILES):
            return default
            
        try:
            file_path = self.mod_data_dir / f"{key}.json"
            if not file_path.exists():
                return default
                
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载数据失败: {e}")
            return default
            
    def delete_data(self, key: str) -> bool:
        """删除自定义数据"""
        if not self._check_permission(Permission.WRITE_FILES):
            return False
            
        try:
            file_path = self.mod_data_dir / f"{key}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        except Exception as e:
            print(f"删除数据失败: {e}")
            return False
            
    def list_data_keys(self) -> List[str]:
        """列出所有数据键"""
        if not self._check_permission(Permission.READ_FILES):
            return []
            
        keys = []
        for file in self.mod_data_dir.glob("*.json"):
            keys.append(file.stem)
        return keys
        
    def set_health(self, health: float) -> bool:
        """设置血量（用于RPG Mod）"""
        if not self._check_permission(Permission.MODIFY_HEALTH):
            return False
            
        # 注意：本体不做死亡判定，但Mod可以添加血量系统
        # 这里只是存储数据，实际效果由Mod自己实现
        return self.save_data("health", health)
        
    def get_health(self) -> float:
        """获取血量"""
        return self.load_data("health", 1.0)
        
    def modify_health(self, delta: float) -> float:
        """修改血量"""
        health = self.get_health()
        health = max(0.0, min(1.0, health + delta))
        self.set_health(health)
        return health
        
    def save_game_state(self, state_data: Dict[str, Any]) -> bool:
        """保存游戏状态"""
        return self.save_data("game_state", state_data)
        
    def load_game_state(self) -> Optional[Dict[str, Any]]:
        """加载游戏状态"""
        return self.load_data("game_state")
        
    def _check_permission(self, permission: Permission) -> bool:
        """检查权限"""
        mod_manager = self.game_engine.mod_manager
        if hasattr(mod_manager, 'permission_manager'):
            return mod_manager.permission_manager.check_permission(
                self.mod_instance.manifest.mod_id, permission
            )
        return False