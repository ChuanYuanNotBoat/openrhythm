# mystia_rhythm/ui/result_ui.py
"""
结算界面
显示游戏结果和分数
"""
import logging
from pathlib import Path

from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.animation import Animation

from .ui_base import BaseScreen, CustomButton

logger = logging.getLogger(__name__)


class ResultScreen(BaseScreen):
    """结算界面"""
    
    def __init__(self, game_engine, **kwargs):
        logger.info("初始化结算界面")
        super().__init__(game_engine, **kwargs)
        
        self._create_ui()
        
    def _create_ui(self):
        """创建UI"""
        # 背景
        bg_path = Path(__file__).parent.parent / 'assets' / 'images' / 'bg_result.png'
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
        
        # 主布局
        main_layout = BoxLayout(orientation='vertical', padding=50, spacing=20)
        
        # 标题
        title_label = Label(
            text='结算',
            font_size=36,
            size_hint_y=0.2,
            color=[1, 1, 1, 1]
        )
        
        # 分数显示区域
        score_layout = GridLayout(cols=2, spacing=20, size_hint_y=0.6)
        
        # 分数项目
        score_items = [
            ('分数', 'score_value'),
            ('准确率', 'accuracy_value'),
            ('最大连击', 'max_combo_value'),
            ('判定统计', 'judgment_stats')
        ]
        
        for label_text, value_key in score_items:
            item_layout = BoxLayout(orientation='vertical', spacing=5)
            
            label = Label(
                text=label_text,
                font_size=20,
                size_hint_y=0.4,
                color=[0.8, 0.8, 0.8, 1]
            )
            
            value_label = Label(
                text='0',
                font_size=24,
                size_hint_y=0.6,
                color=[1, 1, 1, 1]
            )
            
            # 存储引用以便更新
            setattr(self, value_key, value_label)
            
            item_layout.add_widget(label)
            item_layout.add_widget(value_label)
            score_layout.add_widget(item_layout)
        
        # 按钮区域
        button_layout = GridLayout(cols=3, spacing=20, size_hint_y=0.2)
        
        # 重新游玩按钮
        retry_btn = CustomButton(
            text='重新游玩',
            size_hint_x=0.3
        )
        retry_btn.bind(on_release=self._on_retry)
        
        # 返回选曲按钮
        back_btn = CustomButton(
            text='返回选曲',
            size_hint_x=0.3
        )
        back_btn.bind(on_release=self._on_back)
        
        # 返回菜单按钮
        menu_btn = CustomButton(
            text='返回菜单',
            size_hint_x=0.3
        )
        menu_btn.bind(on_release=self._on_menu)
        
        button_layout.add_widget(retry_btn)
        button_layout.add_widget(back_btn)
        button_layout.add_widget(menu_btn)
        
        # 添加到主布局
        main_layout.add_widget(title_label)
        main_layout.add_widget(score_layout)
        main_layout.add_widget(button_layout)
        
        self.add_widget(main_layout)
        
    def update_results(self):
        """更新结算数据"""
        if not self.game_engine.judgment:
            return
            
        judgment = self.game_engine.judgment
        calculator = judgment.calculator
        
        # 更新分数
        if hasattr(self, 'score_value'):
            self.score_value.text = f'{judgment.get_score():,}'
            
        # 更新准确率
        if hasattr(self, 'accuracy_value'):
            accuracy = judgment.get_accuracy()
            self.accuracy_value.text = f'{accuracy:.2f}%'
            
        # 更新最大连击
        if hasattr(self, 'max_combo_value'):
            max_combo = calculator.max_combo
            self.max_combo_value.text = str(max_combo)
            
        # 更新判定统计
        if hasattr(self, 'judgment_stats'):
            counts = calculator.judgment_counts
            stats_text = '\n'.join([
                f'BEST: {counts.get("BEST", 0)}',
                f'COOL: {counts.get("COOL", 0)}',
                f'GOOD: {counts.get("GOOD", 0)}',
                f'MISS: {counts.get("MISS", 0)}'
            ])
            self.judgment_stats.text = stats_text
            
    def _on_retry(self, *args):
        """重新游玩"""
        logger.info("重新游玩")
        if self.game_engine.current_chart:
            self.game_engine.start_game()
            self.parent.current = 'play'
            
    def _on_back(self, *args):
        """返回选曲"""
        logger.info("返回选曲界面")
        self.parent.current = 'song_select'
        
    def _on_menu(self, *args):
        """返回主菜单"""
        logger.info("返回主菜单")
        self.parent.current = 'menu'
        
    def on_enter(self, *args):
        """当进入界面时"""
        # 更新结算数据
        self.update_results()
        
        # 添加动画效果
        for child in self.children:
            if hasattr(child, 'opacity'):
                child.opacity = 0
                Animation(opacity=1, duration=0.5).start(child)