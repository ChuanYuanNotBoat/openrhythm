# mystia_rhythm/mod_system/api/chart_api.py
"""
谱面操作API
提供给Mod的谱面操作接口
"""
from typing import Dict, List, Optional, Any
from pathlib import Path

from mod_system.permission_system import Permission
from core.chart_parser import Chart, Note, NoteType, ChartParser


class ChartAPI:
    """谱面操作API"""
    
    def __init__(self, mod_instance):
        self.mod_instance = mod_instance
        self.game_engine = mod_instance.game_engine
        
    def get_current_chart(self) -> Optional[Chart]:
        """获取当前谱面"""
        if not self._check_permission(Permission.ACCESS_CHART_DATA):
            return None
            
        return self.game_engine.current_chart
        
    def get_notes(self) -> List[Note]:
        """获取所有音符"""
        if not self._check_permission(Permission.ACCESS_CHART_DATA):
            return []
            
        if not self.game_engine.current_chart:
            return []
            
        return self.game_engine.current_chart.notes
        
    def add_note(self, note: Note) -> bool:
        """添加音符（实时）"""
        if not self._check_permission(Permission.MODIFY_CHART):
            return False
            
        if not self.game_engine.current_chart:
            return False
            
        self.game_engine.current_chart.notes.append(note)
        
        # 重新计算时间
        self._recalculate_timing()
        return True
        
    def remove_note(self, index: int) -> bool:
        """移除音符"""
        if not self._check_permission(Permission.MODIFY_CHART):
            return False
            
        if not self.game_engine.current_chart:
            return False
            
        if 0 <= index < len(self.game_engine.current_chart.notes):
            self.game_engine.current_chart.notes.pop(index)
            self._recalculate_timing()
            return True
            
        return False
        
    def modify_note(self, index: int, **kwargs) -> bool:
        """修改音符属性"""
        if not self._check_permission(Permission.MODIFY_CHART):
            return False
            
        if not self.game_engine.current_chart:
            return False
            
        if 0 <= index < len(self.game_engine.current_chart.notes):
            note = self.game_engine.current_chart.notes[index]
            for key, value in kwargs.items():
                if hasattr(note, key):
                    setattr(note, key, value)
                    
            self._recalculate_timing()
            return True
            
        return False
        
    def get_timing_system(self):
        """获取时间系统"""
        if not self._check_permission(Permission.ACCESS_CHART_DATA):
            return None
            
        if not self.game_engine.current_chart:
            return None
            
        return self.game_engine.current_chart.timing_system
        
    def load_chart(self, chart_path: Path) -> bool:
        """加载谱面"""
        if not self._check_permission(Permission.LOAD_CHART):
            return False
            
        chart = ChartParser.load_from_file(chart_path)
        if chart:
            return self.game_engine.load_chart(chart)
        return False
        
    def save_chart(self, chart_path: Path) -> bool:
        """保存当前谱面"""
        if not self._check_permission(Permission.WRITE_FILES):
            return False
            
        if not self.game_engine.current_chart:
            return False
            
        return ChartParser.save_to_file(
            self.game_engine.current_chart, chart_path
        )
        
    def create_note(self, beat: List[float], column: int, 
                   note_type: NoteType = NoteType.TAP, 
                   endbeat: Optional[List[float]] = None) -> Note:
        """创建音符对象"""
        return Note(
            beat=beat,
            column=column,
            endbeat=endbeat,
            type=note_type
        )
        
    def _recalculate_timing(self) -> None:
        """重新计算时间（添加/移除音符后需要调用）"""
        # 这里需要重新计算note_times等
        if self.game_engine.current_chart:
            chart = self.game_engine.current_chart
            timing = chart.timing_system
            
            # 重新计算每个音符的时间
            for note in chart.notes:
                note.time = timing.beat_to_time(note.beat)
                if note.endbeat:
                    note.end_time = timing.beat_to_time(note.endbeat)
                    
    def _check_permission(self, permission: Permission) -> bool:
        """检查权限"""
        mod_manager = self.game_engine.mod_manager
        if hasattr(mod_manager, 'permission_manager'):
            return mod_manager.permission_manager.check_permission(
                self.mod_instance.manifest.mod_id, permission
            )
        return False