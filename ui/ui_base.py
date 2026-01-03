# mystia_rhythm/ui/ui_base.py
"""
UI基础类
"""
from kivy.uix.screenmanager import Screen
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.properties import StringProperty, NumericProperty, ListProperty
from kivy.graphics import Color, RoundedRectangle


class CustomButton(Button):
    """自定义按钮"""
    
    background_color = ListProperty([0.2, 0.2, 0.2, 1])
    hover_color = ListProperty([0.3, 0.3, 0.3, 1])
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(
            pos=self._update_rect,
            size=self._update_rect,
            background_color=self._update_rect
        )
        self._is_hovering = False
        
    def _update_rect(self, *args):
        """更新背景矩形"""
        self.canvas.before.clear()
        with self.canvas.before:
            color = self.hover_color if self._is_hovering else self.background_color
            Color(*color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10])
            
    def on_enter(self):
        """鼠标进入"""
        self._is_hovering = True
        self._update_rect()
        
    def on_leave(self):
        """鼠标离开"""
        self._is_hovering = False
        self._update_rect()


class BaseScreen(Screen):
    """基础屏幕类"""
    
    def __init__(self, game_engine, **kwargs):
        super().__init__(**kwargs)
        self.game_engine = game_engine
        
    def on_enter(self, *args):
        """当进入屏幕时调用"""
        pass
        
    def on_leave(self, *args):
        """当离开屏幕时调用"""
        pass