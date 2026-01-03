# mystia_rhythm/ui/pause_screen.py
"""
暂停界面
"""
import logging
from pathlib import Path

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.animation import Animation

from .ui_base import BaseScreen, CustomButton, CustomLabel

logger = logging.getLogger(__name__)


class PauseScreen(BaseScreen):
    """暂停界面"""
    
    def __init__(self, game_engine, **kwargs):
        logger.info("初始化暂停界面")
        super().__init__(game_engine, **kwargs)
        
        self._create_ui()
        
    def _create_ui(self):
        """创建UI"""
        # 半透明背景
        with self.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(0, 0, 0, 0.5)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
            self.bind(pos=self._update_bg_rect, size=self._update_bg_rect)
        
        # 主布局
        main_layout = BoxLayout(orientation='vertical', padding=50, spacing=30,
                                size_hint=(0.6, 0.7), pos_hint={'center_x': 0.5, 'center_y': 0.5})
        
        # 标题
        title_label = CustomLabel(
            text='游戏暂停',
            font_size=48,
            size_hint_y=0.2,
            color=[1, 1, 1, 1]
        )
        
        # 按钮容器
        button_layout = GridLayout(cols=1, spacing=20, size_hint_y=0.6)
        
        # 继续按钮
        resume_btn = CustomButton(
            text='继续游戏',
            size_hint_y=None,
            height=60
        )
        resume_btn.bind(on_release=self._on_resume)
        
        # 重新开始按钮
        restart_btn = CustomButton(
            text='重新开始',
            size_hint_y=None,
            height=60
        )
        restart_btn.bind(on_release=self._on_restart)
        
        # 返回选曲按钮
        back_song_btn = CustomButton(
            text='返回选曲',
            size_hint_y=None,
            height=60
        )
        back_song_btn.bind(on_release=self._on_back_song)
        
        # 返回菜单按钮
        back_menu_btn = CustomButton(
            text='返回菜单',
            size_hint_y=None,
            height=60
        )
        back_menu_btn.bind(on_release=self._on_back_menu)
        
        button_layout.add_widget(resume_btn)
        button_layout.add_widget(restart_btn)
        button_layout.add_widget(back_song_btn)
        button_layout.add_widget(back_menu_btn)
        
        # 当前谱面信息
        info_label = CustomLabel(
            text=self._get_song_info(),
            font_size=16,
            size_hint_y=0.2,
            color=[0.8, 0.8, 0.8, 1]
        )
        
        main_layout.add_widget(title_label)
        main_layout.add_widget(button_layout)
        main_layout.add_widget(info_label)
        
        self.add_widget(main_layout)
        
        # 初始透明度为0，然后淡入
        self.opacity = 0
        Animation(opacity=1, duration=0.3).start(self)
    
    def _update_bg_rect(self, *args):
        """更新背景矩形"""
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        
    def _get_song_info(self) -> str:
        """获取当前歌曲信息"""
        if not self.game_engine.current_chart:
            return "未加载谱面"
            
        chart = self.game_engine.current_chart
        return f"{chart.metadata.title} - {chart.metadata.artist}\n难度: {chart.metadata.difficulty}"
        
    def _on_resume(self, *args):
        """继续游戏"""
        logger.info("继续游戏")
        self.game_engine.resume_game()
        self.parent.current = 'play'
        
    def _on_restart(self, *args):
        """重新开始"""
        logger.info("重新开始游戏")
        self.game_engine.start_game()
        self.parent.current = 'play'
        
    def _on_back_song(self, *args):
        """返回选曲"""
        logger.info("返回选曲界面")
        self.parent.current = 'song_select'
        
    def _on_back_menu(self, *args):
        """返回主菜单"""
        logger.info("返回主菜单")
        self.parent.current = 'menu'
        
    def on_enter(self, *args):
        """当进入界面时"""
        # 不要在这里调用 pause_game()，已经在外部调用了
        logger.debug("暂停界面已进入")
        # 确保游戏已暂停
        if self.game_engine.state.value == 3:  # PLAYING
            # 记录日志但不调用 pause_game()，因为这会导致递归
            logger.warning("游戏仍在运行状态，但暂停界面已显示")
            
    def on_leave(self, *args):
        """当离开界面时"""
        pass