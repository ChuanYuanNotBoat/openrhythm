# mystia_rhythm/mod_system/permission_system.py
"""
权限管理系统
管理Mod的权限请求和授权
"""
from typing import List, Dict, Set, Optional
from enum import Enum
import json

from config import config, DATA_DIR


class Permission(Enum):
    """权限枚举"""
    # 游戏控制
    PAUSE_GAME = "pause_game"               # 暂停游戏
    RESTART_GAME = "restart_game"           # 重新开始游戏
    EXIT_GAME = "exit_game"                 # 退出游戏
    
    # 谱面操作
    LOAD_CHART = "load_chart"               # 加载谱面
    MODIFY_CHART = "modify_chart"           # 修改谱面（实时）
    ACCESS_CHART_DATA = "access_chart_data" # 访问谱面数据
    
    # 音频控制
    PLAY_SOUND = "play_sound"               # 播放音效
    MODIFY_AUDIO = "modify_audio"           # 修改音频设置
    ACCESS_AUDIO_STREAM = "access_audio_stream" # 访问音频流
    
    # UI控制
    MODIFY_UI = "modify_ui"                 # 修改UI
    CREATE_UI_ELEMENT = "create_ui_element" # 创建UI元素
    REMOVE_UI_ELEMENT = "remove_ui_element" # 移除UI元素
    
    # 文件系统
    READ_FILES = "read_files"               # 读取文件
    WRITE_FILES = "write_files"             # 写入文件
    ACCESS_USER_DATA = "access_user_data"   # 访问用户数据
    
    # 系统
    ACCESS_INTERNET = "access_internet"     # 访问网络
    MODIFY_SETTINGS = "modify_settings"     # 修改设置
    RUN_BACKGROUND_TASKS = "run_background_tasks" # 运行后台任务
    
    # RPG系统
    MODIFY_HEALTH = "modify_health"         # 修改血量（Mod自定义血量系统）
    MODIFY_SCORE = "modify_score"           # 修改分数
    MODIFY_COMBO = "modify_combo"           # 修改连击


class PermissionRequest:
    """权限请求"""
    
    def __init__(self, mod_id: str, permissions: List[Permission], reason: str = ""):
        self.mod_id = mod_id
        self.permissions = permissions
        self.reason = reason
        self.granted = False
        
    def __repr__(self) -> str:
        return f"PermissionRequest(mod_id={self.mod_id}, permissions={[p.value for p in self.permissions]})"


class PermissionManager:
    """权限管理器"""
    
    def __init__(self):
        self.permissions_file = DATA_DIR / 'mod_permissions.json'
        self.granted_permissions: Dict[str, Set[Permission]] = {}
        self._load_permissions()
        
    def _load_permissions(self) -> None:
        """加载已授权的权限"""
        if not self.permissions_file.exists():
            self.granted_permissions = {}
            return
            
        try:
            with open(self.permissions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            for mod_id, perms in data.items():
                self.granted_permissions[mod_id] = {
                    Permission(perm) for perm in perms
                }
        except Exception as e:
            print(f"加载权限文件失败: {e}")
            self.granted_permissions = {}
            
    def _save_permissions(self) -> None:
        """保存权限到文件"""
        try:
            data = {}
            for mod_id, perms in self.granted_permissions.items():
                data[mod_id] = [perm.value for perm in perms]
                
            with open(self.permissions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存权限文件失败: {e}")
            
    def check_permission(self, mod_id: str, permission: Permission) -> bool:
        """检查Mod是否拥有某个权限"""
        # 如果Mod没有请求过权限，自动拒绝
        if mod_id not in self.granted_permissions:
            return False
            
        return permission in self.granted_permissions[mod_id]
        
    def request_permissions(self, mod_id: str, permissions: List[Permission]) -> bool:
        """
        请求权限
        
        Args:
            mod_id: Mod的ID
            permissions: 请求的权限列表
            
        Returns:
            是否授权成功
        """
        # 检查是否已经授权了所有权限
        if mod_id in self.granted_permissions:
            if all(perm in self.granted_permissions[mod_id] for perm in permissions):
                return True
                
        # 这里应该显示权限请求对话框，让用户确认
        # 由于我们是在后台系统，暂时模拟用户同意
        # 在实际应用中，这里应该弹出UI让用户确认
        
        print(f"Mod {mod_id} 请求权限: {[p.value for p in permissions]}")
        
        # 检查是否有危险权限
        dangerous_perms = self._get_dangerous_permissions(permissions)
        if dangerous_perms:
            print(f"警告: Mod {mod_id} 请求了危险权限: {[p.value for p in dangerous_perms]}")
            
        # 模拟用户同意（实际应用中需要用户交互）
        user_granted = self._simulate_user_consent(mod_id, permissions)
        
        if user_granted:
            # 授权
            if mod_id not in self.granted_permissions:
                self.granted_permissions[mod_id] = set()
                
            for perm in permissions:
                self.granted_permissions[mod_id].add(perm)
                
            self._save_permissions()
            return True
        else:
            return False
            
    def revoke_permissions(self, mod_id: str, permissions: List[Permission]) -> None:
        """撤销权限"""
        if mod_id in self.granted_permissions:
            for perm in permissions:
                self.granted_permissions[mod_id].discard(perm)
                
            # 如果没有任何权限了，移除该Mod的记录
            if not self.granted_permissions[mod_id]:
                del self.granted_permissions[mod_id]
                
            self._save_permissions()
            
    def revoke_all_permissions(self, mod_id: str) -> None:
        """撤销Mod的所有权限"""
        if mod_id in self.granted_permissions:
            del self.granted_permissions[mod_id]
            self._save_permissions()
            
    def get_mod_permissions(self, mod_id: str) -> List[Permission]:
        """获取Mod的所有权限"""
        if mod_id in self.granted_permissions:
            return list(self.granted_permissions[mod_id])
        return []
        
    def _get_dangerous_permissions(self, permissions: List[Permission]) -> List[Permission]:
        """获取危险权限列表"""
        dangerous = []
        for perm in permissions:
            if perm in [
                Permission.WRITE_FILES,
                Permission.ACCESS_USER_DATA,
                Permission.ACCESS_INTERNET,
                Permission.MODIFY_SETTINGS,
                Permission.RUN_BACKGROUND_TASKS,
                Permission.MODIFY_HEALTH,
                Permission.MODIFY_SCORE,
                Permission.MODIFY_COMBO
            ]:
                dangerous.append(perm)
        return dangerous
        
    def _simulate_user_consent(self, mod_id: str, permissions: List[Permission]) -> bool:
        """模拟用户同意（临时方案）"""
        # 在实际应用中，这里应该显示一个对话框，让用户选择是否授权
        # 为了测试，我们根据配置决定是否自动授权
        allow_unsafe = config.get('mods.allow_unsafe_mods', False)
        
        # 如果有危险权限且不允许不安全Mod，则拒绝
        dangerous_perms = self._get_dangerous_permissions(permissions)
        if dangerous_perms and not allow_unsafe:
            return False
            
        # 否则自动授权
        return True