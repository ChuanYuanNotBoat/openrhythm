# mystia_rhythm/mod_system/mod_manager.py
"""
Mod管理器
负责加载、管理和运行Mod
"""
import logging
import importlib.util
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass
from enum import Enum

from config import config, MOD_DIR

logger = logging.getLogger(__name__)


class ModState(Enum):
    """Mod状态"""
    DISABLED = 0
    ENABLED = 1
    LOADED = 2
    ERROR = 3
    

class ModCategory(Enum):
    """Mod分类"""
    GAMEPLAY = "gameplay"      # 玩法修改
    VISUAL = "visual"          # 视觉效果
    AUDIO = "audio"            # 音频效果
    UI = "ui"                  # 界面修改
    SYSTEM = "system"          # 系统功能
    OTHERS  = "others"                # 其他分类
    

@dataclass
class ModManifest:
    """Mod清单"""
    mod_id: str                    # 唯一ID
    name: str                      # 显示名称
    version: str                   # 版本号
    author: str                    # 作者
    description: str               # 描述
    category: ModCategory          # 分类
    dependencies: List[str]        # 依赖的Mod
    permissions: List[str]         # 需要的权限
    main_module: str               # 主模块（如 main.py）
    enabled_by_default: bool       # 默认是否启用
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModManifest':
        """从字典创建"""
        return cls(
            mod_id=data['id'],
            name=data['name'],
            version=data.get('version', '1.0.0'),
            author=data.get('author', 'Unknown'),
            description=data.get('description', ''),
            category=ModCategory(data.get('category', 'gameplay')),
            dependencies=data.get('dependencies', []),
            permissions=data.get('permissions', []),
            main_module=data.get('main_module', 'main.py'),
            enabled_by_default=data.get('enabled_by_default', False)
        )
        

class ModInstance:
    """Mod实例"""
    
    def __init__(self, mod_path: Path, manifest: ModManifest):
        self.mod_path = mod_path
        self.manifest = manifest
        self.state = ModState.DISABLED
        self.module = None
        self.error: Optional[str] = None
        
        # 加载的API实例
        self.api_instances: Dict[str, Any] = {}
        
    def load(self, api_classes: Dict[str, Type]) -> bool:
        """加载Mod"""
        try:
            # 构建模块规范
            spec = importlib.util.spec_from_file_location(
                f"mod_{self.manifest.mod_id}",
                self.mod_path / self.manifest.main_module
            )
            
            if spec is None or spec.loader is None:
                self.error = "无法创建模块规范"
                self.state = ModState.ERROR
                return False
                
            # 创建模块
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            
            # 注入API
            for api_name, api_class in api_classes.items():
                api_instance = api_class(self)
                self.api_instances[api_name] = api_instance
                setattr(module, api_name, api_instance)
                
            # 执行模块
            spec.loader.exec_module(module)
            self.module = module
            
            # 调用初始化函数（如果存在）
            if hasattr(module, 'initialize'):
                module.initialize()
                
            self.state = ModState.LOADED
            return True
            
        except Exception as e:
            self.error = str(e)
            self.state = ModState.ERROR
            return False
            
    def unload(self) -> bool:
        """卸载Mod"""
        try:
            # 调用清理函数（如果存在）
            if self.module and hasattr(self.module, 'cleanup'):
                self.module.cleanup()
                
            # 清理API实例
            self.api_instances.clear()
            
            # 从sys.modules中移除
            mod_name = f"mod_{self.manifest.mod_id}"
            if mod_name in sys.modules:
                del sys.modules[mod_name]
                
            self.module = None
            self.state = ModState.DISABLED
            return True
            
        except Exception as e:
            self.error = str(e)
            return False
            
    def enable(self) -> bool:
        """启用Mod"""
        if self.state == ModState.DISABLED:
            # 需要先加载
            return self.load()
        return self.state == ModState.LOADED or self.state == ModState.ENABLED
        
    def disable(self) -> bool:
        """禁用Mod"""
        if self.state == ModState.LOADED or self.state == ModState.ENABLED:
            return self.unload()
        return True
        
    def call_hook(self, hook_name: str, *args, **kwargs) -> Any:
        """调用钩子函数"""
        if self.module and hasattr(self.module, hook_name):
            try:
                func = getattr(self.module, hook_name)
                return func(*args, **kwargs)
            except Exception as e:
                print(f"Mod {self.manifest.mod_id} 钩子 {hook_name} 执行失败: {e}")
        return None


class ModManager:
    """Mod管理器"""
    
    def __init__(self, game_engine):
        logger.info("初始化Mod管理器")
        self.game_engine = game_engine
        self.mods: Dict[str, ModInstance] = {}
        self.load_order: List[str] = []
        self.api_classes: Dict[str, Type] = {}
        
        logger.debug(f"Mod目录: {MOD_DIR}")
        self._scan_mods()
        logger.info(f"扫描完成: 找到 {len(self.mods)} 个Mod")
        
    def _scan_mods(self) -> None:
        """扫描Mod目录"""
        logger.debug("开始扫描Mod...")
        if not MOD_DIR.exists():
            logger.debug(f"Mod目录不存在，创建: {MOD_DIR}")
            MOD_DIR.mkdir(parents=True, exist_ok=True)
            return
            
        for mod_dir in MOD_DIR.iterdir():
            if not mod_dir.is_dir():
                continue
                
            manifest_file = mod_dir / 'manifest.json'
            if not manifest_file.exists():
                logger.debug(f"跳过无清单文件的目录: {mod_dir.name}")
                continue
                
            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                    
                manifest = ModManifest.from_dict(manifest_data)
                mod_instance = ModInstance(mod_dir, manifest)
                
                enabled_mods = config.get('mods.enabled_mods', [])
                if manifest.mod_id in enabled_mods:
                    mod_instance.state = ModState.ENABLED
                    logger.debug(f"Mod已启用: {manifest.name}")
                else:
                    logger.debug(f"Mod已禁用: {manifest.name}")
                    
                self.mods[manifest.mod_id] = mod_instance
                logger.info(f"加载Mod清单: {manifest.name} v{manifest.version}")
                
            except Exception as e:
                logger.error(f"加载Mod清单失败 {mod_dir}: {e}")
                
    def register_api(self, api_name: str, api_class: Type) -> None:
        """注册API类"""
        self.api_classes[api_name] = api_class
        
    def load_all_mods(self) -> None:
        """加载所有启用的Mod"""
        logger.info("开始加载Mod...")
        self.load_order = config.get('mods.mod_load_order', [])
        
        if not self.load_order:
            logger.debug("使用依赖关系排序Mod")
            self.load_order = self._resolve_dependencies()
            
        loaded_count = 0
        for mod_id in self.load_order:
            if mod_id in self.mods:
                mod = self.mods[mod_id]
                if mod.state == ModState.ENABLED:
                    logger.info(f"加载Mod: {mod.manifest.name}")
                    if not mod.load(self.api_classes):
                        logger.error(f"Mod加载失败: {mod.manifest.name} ({mod.error})")
                    else:
                        loaded_count += 1
                        logger.debug(f"Mod加载成功: {mod.manifest.name}")
                        
        logger.info(f"Mod加载完成: {loaded_count}/{len(self.load_order)}")
        
    def unload_all_mods(self) -> None:
        """卸载所有Mod"""
        # 按相反顺序卸载
        for mod_id in reversed(self.load_order):
            if mod_id in self.mods:
                mod = self.mods[mod_id]
                if mod.state == ModState.LOADED:
                    mod.unload()
                    
    def enable_mod(self, mod_id: str) -> bool:
        """启用Mod"""
        if mod_id not in self.mods:
            return False
            
        mod = self.mods[mod_id]
        
        # 检查依赖
        for dep_id in mod.manifest.dependencies:
            if dep_id not in self.mods or self.mods[dep_id].state == ModState.DISABLED:
                print(f"Mod {mod_id} 依赖 {dep_id} 未启用")
                return False
                
        # 启用Mod
        success = mod.enable()
        if success:
            # 更新配置
            enabled_mods = config.get('mods.enabled_mods', [])
            if mod_id not in enabled_mods:
                enabled_mods.append(mod_id)
                config.set('mods.enabled_mods', enabled_mods)
                
            # 重新计算加载顺序
            self.load_order = self._resolve_dependencies()
            
        return success
        
    def disable_mod(self, mod_id: str) -> bool:
        """禁用Mod"""
        if mod_id not in self.mods:
            return False
            
        mod = self.mods[mod_id]
        success = mod.disable()
        
        if success:
            # 更新配置
            enabled_mods = config.get('mods.enabled_mods', [])
            if mod_id in enabled_mods:
                enabled_mods.remove(mod_id)
                config.set('mods.enabled_mods', enabled_mods)
                
        return success
        
    def call_hooks(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """调用所有Mod的钩子函数"""
        results = []
        
        for mod_id in self.load_order:
            if mod_id in self.mods:
                mod = self.mods[mod_id]
                if mod.state == ModState.LOADED:
                    result = mod.call_hook(hook_name, *args, **kwargs)
                    if result is not None:
                        results.append(result)
                        
        return results
        
    def _resolve_dependencies(self) -> List[str]:
        """解析依赖关系，返回加载顺序"""
        # 构建依赖图
        graph = {}
        for mod_id, mod in self.mods.items():
            if mod.state != ModState.ENABLED:
                continue
            graph[mod_id] = set(mod.manifest.dependencies)
            
        # 拓扑排序
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(node):
            if node in temp_visited:
                raise Exception(f"循环依赖: {node}")
            if node not in visited:
                temp_visited.add(node)
                for dep in graph.get(node, []):
                    if dep in graph:  # 只考虑启用的Mod
                        visit(dep)
                temp_visited.remove(node)
                visited.add(node)
                order.append(node)
                
        for node in list(graph.keys()):
            if node not in visited:
                visit(node)
                
        return order
        
    def get_mod_info(self, mod_id: str) -> Optional[Dict[str, Any]]:
        """获取Mod信息"""
        if mod_id not in self.mods:
            return None
            
        mod = self.mods[mod_id]
        return {
            'id': mod.manifest.mod_id,
            'name': mod.manifest.name,
            'version': mod.manifest.version,
            'author': mod.manifest.author,
            'description': mod.manifest.description,
            'category': mod.manifest.category.value,
            'state': mod.state.value,
            'error': mod.error,
            'permissions': mod.manifest.permissions
        }
        
    def list_mods(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有Mod"""
        result = []
        
        for mod_id, mod in self.mods.items():
            if category and mod.manifest.category.value != category:
                continue
                
            result.append(self.get_mod_info(mod_id))
            
        return result