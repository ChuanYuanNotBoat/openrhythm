# mystia_rhythm/ui/menu.py
"""
主菜单界面
"""
import logging
from pathlib import Path

from kivy.uix.image import Image
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.animation import Animation

from .ui_base import BaseScreen, CustomButton, CustomLabel

logger = logging.getLogger(__name__)


class MenuScreen(BaseScreen):
    """主菜单界面"""
    
    def __init__(self, game_engine, **kwargs):
        logger.info("初始化主菜单")
        super().__init__(game_engine, **kwargs)
        
        self._create_ui()
        
    def _create_ui(self):
        """创建UI"""
        # 主布局
        main_layout = BoxLayout(orientation='vertical', padding=50, spacing=20)
        
        # 标题
        title_label = CustomLabel(
            text='Mystia Rhythm',
            font_size=48,
            size_hint_y=0.3,
            color=[1, 1, 1, 1]
        )
        
        # 按钮容器
        button_layout = GridLayout(cols=1, spacing=20, size_hint_y=0.5)
        
        # 开始游戏按钮
        start_btn = CustomButton(
            text='开始游戏',
            size_hint_y=None,
            height=60,
            background_color=[0.2, 0.6, 0.8, 1],
            hover_color=[0.3, 0.7, 0.9, 1]
        )
        start_btn.bind(on_release=self._on_start)
        
        # 设置按钮
        settings_btn = CustomButton(
            text='设置',
            size_hint_y=None,
            height=60,
            background_color=[0.4, 0.4, 0.4, 1],
            hover_color=[0.5, 0.5, 0.5, 1]
        )
        settings_btn.bind(on_release=self._on_settings)
        
        # 退出按钮
        quit_btn = CustomButton(
            text='退出游戏',
            size_hint_y=None,
            height=60,
            background_color=[0.8, 0.2, 0.2, 1],
            hover_color=[0.9, 0.3, 0.3, 1]
        )
        quit_btn.bind(on_release=self._on_quit)
        
        # 添加按钮
        button_layout.add_widget(start_btn)
        button_layout.add_widget(settings_btn)
        button_layout.add_widget(quit_btn)
        
        # 版本信息
        version_label = CustomLabel(
            text='v1.0.0',
            font_size=14,
            size_hint_y=0.1,
            color=[0.7, 0.7, 0.7, 1]
        )
        
        # 添加到布局
        main_layout.add_widget(title_label)
        main_layout.add_widget(button_layout)
        main_layout.add_widget(version_label)
        
        # 背景
        bg_path = Path(__file__).parent.parent / 'assets' / 'images' / 'bg_menu.png'
        if bg_path.exists():
            try:
                bg_image = Image(
                    source=str(bg_path),
                    allow_stretch=True,
                    size_hint=(1, 1),
                    pos_hint={'x': 0, 'y': 0}
                )
                self.add_widget(bg_image)
            except Exception as e:
                logger.error(f"背景图片加载失败: {e}")
        
        self.add_widget(main_layout)
        
    def _on_start(self, *args):
        """开始游戏按钮回调"""
        logger.info("切换到选曲界面")
        self.parent.current = 'song_select'
        
    def _on_settings(self, *args):
        """设置按钮回调"""
        logger.info("打开设置界面")
        self.parent.current = 'settings'
        
    def _on_quit(self, *args):
        """退出游戏按钮回调"""
        logger.info("退出游戏")
        self.game_engine.app.stop()