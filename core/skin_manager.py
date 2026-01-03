"""
皮肤管理系统
支持自定义UI和游戏元素外观
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass

from config import config, SKINS_DIR


@dataclass
class SkinConfig:
    """皮肤配置"""
    name: str
    author: str
    version: str
    description: str
    
    # 颜色配置
    note_colors: Dict[str, list]  # 音符类型 -> RGB颜色
    judgment_line_color: list
    background_color: list
    ui_primary_color: list
    ui_secondary_color: list
    
    # 字体配置
    font_name: str
    font_sizes: Dict[str, int]
    
    # 图片路径
    images: Dict[str, str]
    
    # 特效配置
    particle_effects: bool
    animation_speed: float


class SkinManager:
    """皮肤管理器"""
    
    def __init__(self):
        self.skins_dir = SKINS_DIR
        self.current_skin: Optional[SkinConfig] = None
        self.available_skins: Dict[str, Path] = {}
        
        self._scan_skins()
        self._load_current_skin()
        
    def _scan_skins(self) -> None:
        """扫描皮肤目录"""
        if not self.skins_dir.exists():
            self.skins_dir.mkdir(parents=True, exist_ok=True)
            self._create_default_skin()
            
        for skin_dir in self.skins_dir.iterdir():
            if not skin_dir.is_dir():
                continue
                
            config_file = skin_dir / 'config.json'
            if config_file.exists():
                self.available_skins[skin_dir.name] = skin_dir
                
    def _create_default_skin(self) -> None:
        """创建默认皮肤"""
        default_dir = self.skins_dir / 'default'
        default_dir.mkdir(exist_ok=True)
        
        default_config = {
            'name': 'Default',
            'author': 'Mystia Rhythm Team',
            'version': '1.0.0',
            'description': 'Default game skin',
            
            'note_colors': {
                'tap': [0.2, 0.8, 1.0],
                'hold': [0.2, 1.0, 0.6],
                'drag': [1.0, 0.6, 0.2],
                'flick': [1.0, 0.2, 0.8]
            },
            
            'judgment_line_color': [1.0, 1.0, 1.0],
            'background_color': [0.1, 0.1, 0.1],
            'ui_primary_color': [0.2, 0.6, 1.0],
            'ui_secondary_color': [0.3, 0.3, 0.3],
            
            'font_name': 'default',
            'font_sizes': {
                'title': 32,
                'normal': 24,
                'small': 16,
                'tiny': 12
            },
            
            'images': {
                'note_tap': 'note_tap.png',
                'note_hold': 'note_hold.png',
                'background': 'background.png'
            },
            
            'particle_effects': True,
            'animation_speed': 1.0
        }
        
        config_file = default_dir / 'config.json'
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
            
        # 创建图片目录
        images_dir = default_dir / 'images'
        images_dir.mkdir(exist_ok=True)
        
    def _load_current_skin(self) -> None:
        """加载当前皮肤"""
        skin_name = config.get('skin.current_skin', 'default')
        self.load_skin(skin_name)
        
    def load_skin(self, skin_name: str) -> bool:
        """加载指定皮肤"""
        if skin_name not in self.available_skins:
            print(f"皮肤未找到: {skin_name}, 使用默认皮肤")
            skin_name = 'default'
            
        if skin_name not in self.available_skins:
            print(f"默认皮肤不存在!")
            return False
            
        try:
            skin_path = self.available_skins[skin_name]
            config_file = skin_path / 'config.json'
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                
            # 创建皮肤配置对象
            self.current_skin = SkinConfig(
                name=config_data['name'],
                author=config_data['author'],
                version=config_data['version'],
                description=config_data['description'],
                
                note_colors=config_data.get('note_colors', {}),
                judgment_line_color=config_data.get('judgment_line_color', [1.0, 1.0, 1.0]),
                background_color=config_data.get('background_color', [0.1, 0.1, 0.1]),
                ui_primary_color=config_data.get('ui_primary_color', [0.2, 0.6, 1.0]),
                ui_secondary_color=config_data.get('ui_secondary_color', [0.3, 0.3, 0.3]),
                
                font_name=config_data.get('font_name', 'default'),
                font_sizes=config_data.get('font_sizes', {}),
                
                images=config_data.get('images', {}),
                
                particle_effects=config_data.get('particle_effects', True),
                animation_speed=config_data.get('animation_speed', 1.0)
            )
            
            # 保存当前皮肤
            config.set('skin.current_skin', skin_name)
            
            return True
            
        except Exception as e:
            print(f"加载皮肤失败: {e}")
            return False
            
    def get_image(self, image_key: str) -> Optional[Path]:
        """获取皮肤中的图片路径"""
        if not self.current_skin:
            return None
            
        image_name = self.current_skin.images.get(image_key)
        if not image_name:
            return None
            
        skin_path = self.available_skins.get(self.current_skin.name)
        if not skin_path:
            return None
            
        image_path = skin_path / 'images' / image_name
        if image_path.exists():
            return image_path
            
        return None
        
    def get_color(self, color_key: str) -> Optional[list]:
        """获取皮肤中的颜色"""
        if not self.current_skin:
            return None
            
        if color_key == 'background':
            return self.current_skin.background_color
        elif color_key == 'judgment_line':
            return self.current_skin.judgment_line_color
        elif color_key == 'ui_primary':
            return self.current_skin.ui_primary_color
        elif color_key == 'ui_secondary':
            return self.current_skin.ui_secondary_color
        elif color_key.startswith('note_'):
            note_type = color_key[5:]
            return self.current_skin.note_colors.get(note_type)
            
        return None
        
    def list_skins(self) -> list:
        """列出所有可用皮肤"""
        return list(self.available_skins.keys())
