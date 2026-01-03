# mystia_rhythm/mod_system/api/ui_api.py
"""
UI控制API
提供给Mod的UI控制接口
"""
from typing import Dict, List, Optional, Tuple, Any
from kivy.uix.widget import Widget

from mod_system.permission_system import Permission


class UIApi:
    """UI控制API"""
    
    def __init__(self, mod_instance):
        self.mod_instance = mod_instance
        self.game_engine = mod_instance.game_engine
        
        # 存储Mod创建的UI元素
        self.ui_elements: List[Widget] = []
        
    def create_widget(self, widget_class: str, **kwargs) -> Optional[Widget]:
        """创建UI组件"""
        if not self._check_permission(Permission.CREATE_UI_ELEMENT):
            return None
            
        try:
            # 动态导入Kivy组件
            module_name, class_name = widget_class.rsplit('.', 1)
            
            if module_name == 'kivy.uix.label':
                from kivy.uix.label import Label
                widget = Label(**kwargs)
            elif module_name == 'kivy.uix.button':
                from kivy.uix.button import Button
                widget = Button(**kwargs)
            elif module_name == 'kivy.uix.image':
                from kivy.uix.image import Image
                widget = Image(**kwargs)
            elif module_name == 'kivy.uix.slider':
                from kivy.uix.slider import Slider
                widget = Slider(**kwargs)
            elif module_name == 'kivy.uix.layout':
                if class_name == 'BoxLayout':
                    from kivy.uix.boxlayout import BoxLayout
                    widget = BoxLayout(**kwargs)
                elif class_name == 'GridLayout':
                    from kivy.uix.gridlayout import GridLayout
                    widget = GridLayout(**kwargs)
                elif class_name == 'FloatLayout':
                    from kivy.uix.floatlayout import FloatLayout
                    widget = FloatLayout(**kwargs)
                else:
                    return None
            else:
                return None
                
            # 存储引用
            self.ui_elements.append(widget)
            return widget
            
        except Exception as e:
            print(f"创建UI组件失败: {e}")
            return None
            
    def add_widget(self, parent: Widget, widget: Widget) -> bool:
        """添加UI组件到父组件"""
        if not self._check_permission(Permission.CREATE_UI_ELEMENT):
            return False
            
        try:
            parent.add_widget(widget)
            return True
        except Exception as e:
            print(f"添加UI组件失败: {e}")
            return False
            
    def remove_widget(self, parent: Widget, widget: Widget) -> bool:
        """从父组件移除UI组件"""
        if not self._check_permission(Permission.REMOVE_UI_ELEMENT):
            return False
            
        try:
            parent.remove_widget(widget)
            
            # 从存储中移除
            if widget in self.ui_elements:
                self.ui_elements.remove(widget)
                
            return True
        except Exception as e:
            print(f"移除UI组件失败: {e}")
            return False
            
    def modify_widget(self, widget: Widget, **kwargs) -> bool:
        """修改UI组件属性"""
        if not self._check_permission(Permission.MODIFY_UI):
            return False
            
        try:
            for key, value in kwargs.items():
                setattr(widget, key, value)
            return True
        except Exception as e:
            print(f"修改UI组件失败: {e}")
            return False
            
    def get_root_widget(self) -> Optional[Widget]:
        """获取根Widget（当前屏幕）"""
        # 这里假设游戏引擎有一个current_screen属性
        if hasattr(self.game_engine, 'current_screen'):
            return self.game_engine.current_screen
        return None
        
    def show_message(self, message: str, duration: float = 3.0) -> bool:
        """显示消息（临时）"""
        if not self._check_permission(Permission.MODIFY_UI):
            return False
            
        # 这里应该实现一个消息显示系统
        # 暂时打印到控制台
        print(f"[Mod消息] {message}")
        return True
        
    def show_dialog(self, title: str, message: str, 
                   buttons: List[str] = None) -> Optional[str]:
        """显示对话框"""
        if not self._check_permission(Permission.MODIFY_UI):
            return None
            
        # 这里应该实现一个对话框系统
        # 暂时模拟返回第一个按钮
        print(f"[Mod对话框] {title}: {message}")
        if buttons:
            return buttons[0]
        return "OK"
        
    def clear_all_elements(self) -> None:
        """清除所有Mod创建的UI元素"""
        for widget in self.ui_elements[:]:  # 使用副本遍历
            if widget.parent:
                widget.parent.remove_widget(widget)
            self.ui_elements.remove(widget)
            
    def _check_permission(self, permission: Permission) -> bool:
        """检查权限"""
        mod_manager = self.game_engine.mod_manager
        if hasattr(mod_manager, 'permission_manager'):
            return mod_manager.permission_manager.check_permission(
                self.mod_instance.manifest.mod_id, permission
            )
        return False