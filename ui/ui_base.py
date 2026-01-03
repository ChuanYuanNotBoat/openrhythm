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
    font_name = StringProperty('DefaultFont')  # 改为DefaultFont
    
    def __init__(self, **kwargs):
        # 确保字体设置
        if 'font_name' not in kwargs:
            kwargs['font_name'] = 'DefaultFont'  # 改为DefaultFont
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
            
    def on_touch_down(self, touch):
        """处理触摸按下事件"""
        if self.collide_point(*touch.pos):
            self._is_hovering = True
            self._update_rect()
            return super().on_touch_down(touch)
        return False
            
    def on_touch_up(self, touch):
        """处理触摸释放事件"""
        if self.collide_point(*touch.pos):
            self._is_hovering = False
            self._update_rect()
        return super().on_touch_up(touch)


class CustomLabel(Label):
    """自定义标签 - 确保字体正确"""
    
    def __init__(self, **kwargs):
        if 'font_name' not in kwargs:
            kwargs['font_name'] = 'DefaultFont'  # 改为DefaultFont
        super().__init__(**kwargs)


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