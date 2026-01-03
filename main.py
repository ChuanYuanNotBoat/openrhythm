# mystia_rhythm/main.py
"""
主程序入口
"""
import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到sys.path
sys.path.insert(0, str(Path(__file__).parent))

# 配置日志（在其他导入之前）
def setup_logging():
    """设置日志系统"""
    log_dir = Path(__file__).parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'mystia_rhythm.log'
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

# 先设置日志
logger = setup_logging()
logger.info("日志系统初始化完成")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.core.window import Window
from kivy.clock import Clock

# 导入配置（在日志之后）
from config import config
from core.game_engine import GameEngine, GameState
from ui.menu import MenuScreen
from ui.song_select import SongSelectScreen
from ui.play_ui import PlayUI
from ui.result_ui import ResultScreen
from mod_system.mod_manager import ModManager
from mod_system.permission_system import PermissionManager
from mod_system.api.game_api import GameAPI
from mod_system.api.ui_api import UIApi
from mod_system.api.chart_api import ChartAPI
from mod_system.api.audio_api import AudioAPI
from mod_system.api.custom_api import CustomAPI


class MystiaRhythmApp(App):
    """主应用类"""
    
    def __init__(self, **kwargs):
        logger.info("=" * 60)
        logger.info("Mystia Rhythm 应用启动")
        logger.info("=" * 60)
        
        super().__init__(**kwargs)
        self.game_engine = None
        self.screen_manager = None
        self.mod_manager = None
        
    def build(self):
        """构建应用界面"""
        logger.info("构建应用界面")
        
        try:
            # 设置窗口
            resolution = config.get('graphics.resolution', [1280, 720])
            Window.size = tuple(resolution)
            Window.title = 'Mystia Rhythm'
            
            if config.get('graphics.fullscreen', False):
                Window.fullscreen = 'auto'
                
            # 创建游戏引擎
            self.game_engine = GameEngine(self)
            
            # 创建Mod管理器
            self.mod_manager = ModManager(self.game_engine)
            
            # 设置权限管理器
            permission_manager = PermissionManager()
            self.mod_manager.permission_manager = permission_manager
            
            # 注册API类
            self.mod_manager.register_api('game_api', GameAPI)
            self.mod_manager.register_api('ui_api', UIApi)
            self.mod_manager.register_api('chart_api', ChartAPI)
            self.mod_manager.register_api('audio_api', AudioAPI)
            self.mod_manager.register_api('custom_api', CustomAPI)
            
            # 加载所有启用的Mod
            self.mod_manager.load_all_mods()
            
            # 创建屏幕管理器
            self.screen_manager = ScreenManager(transition=FadeTransition())
            
            # 创建各个屏幕
            menu_screen = MenuScreen(
                game_engine=self.game_engine
            )
            menu_screen.name = 'menu'
            
            song_select_screen = SongSelectScreen(
                game_engine=self.game_engine
            )
            song_select_screen.name = 'song_select'
            
            play_screen = PlayUI(
                game_engine=self.game_engine
            )
            play_screen.name = 'play'
            self.game_engine.play_ui = play_screen
            
            result_screen = ResultScreen(
                game_engine=self.game_engine
            )
            result_screen.name = 'result'
            
            # 添加屏幕（按正确的顺序）
            self.screen_manager.add_widget(menu_screen)
            self.screen_manager.add_widget(song_select_screen)
            self.screen_manager.add_widget(play_screen)
            self.screen_manager.add_widget(result_screen)
            
            # 设置初始屏幕为菜单
            self.screen_manager.current = 'menu'
            
            # 启动游戏引擎更新循环
            Clock.schedule_interval(self.game_engine.update, 1.0 / 60.0)
            
            logger.info("应用构建完成")
            return self.screen_manager
        except Exception as e:
            logger.error(f"应用构建失败: {e}", exc_info=True)
            raise
        
    def on_start(self):
        """应用启动时调用"""
        logger.info("应用已启动")
        
        # 调用Mod的启动钩子
        if hasattr(self.mod_manager, 'call_hooks'):
            self.mod_manager.call_hooks('on_app_start')
        
    def on_stop(self):
        """应用停止时调用"""
        logger.info("应用停止中...")
        
        # 卸载所有Mod
        if self.mod_manager:
            self.mod_manager.unload_all_mods()
        
        # 保存配置
        config.save()
        
        # 调用Mod的停止钩子
        if hasattr(self.mod_manager, 'call_hooks'):
            self.mod_manager.call_hooks('on_app_stop')
        
        logger.info("=" * 60)
        logger.info("Mystia Rhythm 应用已关闭")
        logger.info("=" * 60)
        
    def on_pause(self):
        """应用暂停时调用"""
        if self.game_engine and self.game_engine.state == GameState.PLAYING:
            self.game_engine.pause_game()
        return True
        
    def on_resume(self):
        """应用恢复时调用"""
        pass


def main():
    """主函数"""
    try:
        logger.info(f"项目根目录: {Path(__file__).parent}")
        
        # 配置系统字体
        try:
            from kivy.core.text import LabelBase
            # 使用项目中的字体
            font_path = Path(__file__).parent / 'assets' / 'fonts' / 'SourceHanSansSC-Regular.otf'
            if font_path.exists():
                LabelBase.register('default', str(font_path))
            else:
                # 如果没有字体文件，使用系统默认
                logger.warning("字体文件未找到，使用系统默认字体")
        except Exception as e:
            logger.warning(f"字体配置失败: {e}")
        
        logger.info("启动Kivy应用")
        MystiaRhythmApp().run()
        
    except Exception as e:
        logger.error(f"应用启动失败: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()