"""
谱面浏览器UI Mod
"""
from typing import List, Dict, Any, Optional, Callable
import os
import json
from dataclasses import dataclass

@dataclass
class ChartDisplayInfo:
    id: str
    title: str
    artist: str
    creator: str
    bpm: float
    difficulties: List[Dict[str, Any]]
    play_count: int
    rating: Optional[float]
    tags: List[str]

class ChartBrowserUI:
    """谱面浏览器UI"""
    
    def __init__(self, chart_manager):
        self.chart_manager = chart_manager
        self.charts: List[ChartDisplayInfo] = []
        self.filtered_charts: List[ChartDisplayInfo] = []
        self.selected_chart_index: int = 0
        self.selected_difficulty_index: int = 0
        
        self.search_query: str = ""
        self.sort_by: str = "title"  # title, artist, bpm, play_count, rating
        self.sort_reverse: bool = False
        
        self.filter_mode: str = "all"  # all, 4k, 5k, 6k, 7k, 8k
        self.filter_min_level: int = 1
        self.filter_max_level: int = 30
        
        self.on_chart_selected: Optional[Callable[[Dict[str, Any]], None]] = None
        
        self.load_charts()
    
    def load_charts(self):
        """加载所有谱面"""
        try:
            charts_data = self.chart_manager.get_all_charts()
            
            self.charts = []
            for chart_data in charts_data:
                chart = ChartDisplayInfo(
                    id=chart_data['id'],
                    title=chart_data['title'],
                    artist=chart_data['artist'],
                    creator=chart_data['creator'],
                    bpm=chart_data['bpm'],
                    difficulties=chart_data.get('difficulties', []),
                    play_count=chart_data.get('play_count', 0),
                    rating=chart_data.get('rating'),
                    tags=chart_data.get('tags', [])
                )
                self.charts.append(chart)
            
            self.apply_filters()
            
        except Exception as e:
            print(f"Error loading charts: {e}")
    
    def apply_filters(self):
        """应用筛选和排序"""
        # 筛选
        filtered = []
        for chart in self.charts:
            # 搜索筛选
            if self.search_query:
                query_lower = self.search_query.lower()
                if not (query_lower in chart.title.lower() or 
                       query_lower in chart.artist.lower() or
                       query_lower in chart.creator.lower()):
                    continue
            
            # 模式筛选
            if self.filter_mode != "all":
                mode_tag = f"{self.filter_mode}k"
                if mode_tag not in chart.tags:
                    continue
            
            # 难度等级筛选
            has_difficulty_in_range = False
            for diff in chart.difficulties:
                level = diff.get('level', 1)
                if self.filter_min_level <= level <= self.filter_max_level:
                    has_difficulty_in_range = True
                    break
            
            if not has_difficulty_in_range:
                continue
            
            filtered.append(chart)
        
        # 排序
        if self.sort_by == "title":
            filtered.sort(key=lambda c: c.title.lower(), reverse=self.sort_reverse)
        elif self.sort_by == "artist":
            filtered.sort(key=lambda c: c.artist.lower(), reverse=self.sort_reverse)
        elif self.sort_by == "bpm":
            filtered.sort(key=lambda c: c.bpm, reverse=self.sort_reverse)
        elif self.sort_by == "play_count":
            filtered.sort(key=lambda c: c.play_count, reverse=self.sort_reverse)
        elif self.sort_by == "rating":
            filtered.sort(key=lambda c: c.rating or 0, reverse=self.sort_reverse)
        
        self.filtered_charts = filtered
        
        # 确保选中索引有效
        if self.selected_chart_index >= len(self.filtered_charts):
            self.selected_chart_index = max(0, len(self.filtered_charts) - 1)
    
    def select_chart(self, index: int):
        """选择谱面"""
        if 0 <= index < len(self.filtered_charts):
            self.selected_chart_index = index
            self.selected_difficulty_index = 0
            
            chart = self.filtered_charts[index]
            
            if self.on_chart_selected:
                self.on_chart_selected({
                    'id': chart.id,
                    'title': chart.title,
                    'artist': chart.artist,
                    'difficulty': chart.difficulties[0] if chart.difficulties else None
                })
    
    def select_difficulty(self, index: int):
        """选择难度"""
        chart = self.get_selected_chart()
        if chart and 0 <= index < len(chart.difficulties):
            self.selected_difficulty_index = index
    
    def get_selected_chart(self) -> Optional[ChartDisplayInfo]:
        """获取选中的谱面"""
        if 0 <= self.selected_chart_index < len(self.filtered_charts):
            return self.filtered_charts[self.selected_chart_index]
        return None
    
    def get_selected_difficulty(self) -> Optional[Dict[str, Any]]:
        """获取选中的难度"""
        chart = self.get_selected_chart()
        if chart and 0 <= self.selected_difficulty_index < len(chart.difficulties):
            return chart.difficulties[self.selected_difficulty_index]
        return None
    
    def play_selected_chart(self):
        """游玩选中的谱面"""
        chart = self.get_selected_chart()
        difficulty = self.get_selected_difficulty()
        
        if chart and difficulty:
            # 记录游玩
            try:
                self.chart_manager.record_play(chart.id)
            except Exception as e:
                print(f"Error recording play: {e}")
            
            return {
                'chart_id': chart.id,
                'difficulty_name': difficulty['name'],
                'title': chart.title,
                'artist': chart.artist,
                'difficulty_level': difficulty.get('level', 1),
            }
        
        return None
    
    def import_chart_file(self, file_path: str):
        """导入谱面文件"""
        try:
            if file_path.lower().endswith('.mcz'):
                imported = self.chart_manager.import_mcz(file_path)
                print(f"Imported {len(imported)} charts from MCZ file")
            else:
                # 处理单个文件
                print(f"Single file import not yet implemented")
            
            # 重新加载列表
            self.load_charts()
            
            return True
            
        except Exception as e:
            print(f"Error importing chart: {e}")
            return False
    
    def delete_selected_chart(self):
        """删除选中的谱面"""
        chart = self.get_selected_chart()
        if chart:
            # 这里需要ChartManager支持删除功能
            # self.chart_manager.delete_chart(chart.id)
            print(f"Would delete chart: {chart.title}")
            
            # 重新加载列表
            self.load_charts()
            return True
        
        return False
    
    def set_rating(self, rating: float):
        """为选中的谱面评分"""
        chart = self.get_selected_chart()
        if chart:
            try:
                self.chart_manager.set_rating(chart.id, rating)
                chart.rating = rating
                return True
            except Exception as e:
                print(f"Error setting rating: {e}")
        
        return False

class ChartBrowserRenderer:
    """谱面浏览器渲染器"""
    
    def __init__(self, ui: ChartBrowserUI):
        self.ui = ui
        self.font_size_normal = 0.04
        self.font_size_small = 0.03
        self.font_size_large = 0.06
        self.selected_color = [0.2, 0.6, 1.0, 1.0]
        self.normal_color = [1.0, 1.0, 1.0, 1.0]
        self.dimmed_color = [0.7, 0.7, 0.7, 1.0]
    
    def render(self):
        """渲染谱面浏览器"""
        objects = []
        
        # 背景
        objects.append({
            "type": "rectangle",
            "position": [0.0, 0.0],
            "size": [1.8, 1.0],
            "color": [0.05, 0.05, 0.1, 0.9],
            "layer": 0,
        })
        
        # 标题
        objects.append({
            "type": "text",
            "text": "谱面浏览器",
            "position": [0.0, 0.85],
            "size": self.font_size_large,
            "color": [1.0, 1.0, 1.0, 1.0],
            "layer": 1,
        })
        
        # 搜索框
        search_text = f"搜索: {self.ui.search_query}" if self.ui.search_query else "搜索..."
        objects.append({
            "type": "rectangle",
            "position": [-0.7, 0.7],
            "size": [1.2, 0.08],
            "color": [0.1, 0.1, 0.15, 1.0],
            "layer": 1,
        })
        objects.append({
            "type": "text",
            "text": search_text,
            "position": [-0.7, 0.7],
            "size": self.font_size_normal,
            "color": self.dimmed_color if not self.ui.search_query else self.normal_color,
            "layer": 2,
        })
        
        # 谱面列表
        list_start_y = 0.5
        list_item_height = 0.1
        
        for i, chart in enumerate(self.ui.filtered_charts[:10]):  # 只显示前10个
            y = list_start_y - i * list_item_height
            is_selected = (i == self.ui.selected_chart_index)
            
            # 背景
            bg_color = self.selected_color if is_selected else [0.15, 0.15, 0.2, 1.0]
            objects.append({
                "type": "rectangle",
                "position": [0.0, y],
                "size": [1.6, list_item_height * 0.9],
                "color": bg_color,
                "layer": 1,
            })
            
            # 标题
            title_color = self.normal_color if is_selected else [0.9, 0.9, 0.9, 1.0]
            objects.append({
                "type": "text",
                "text": chart.title,
                "position": [-0.7, y],
                "size": self.font_size_normal,
                "color": title_color,
                "layer": 2,
            })
            
            # 艺术家
            objects.append({
                "type": "text",
                "text": chart.artist,
                "position": [-0.7, y - 0.04],
                "size": self.font_size_small,
                "color": self.dimmed_color,
                "layer": 2,
            })
            
            # BPM
            objects.append({
                "type": "text",
                "text": f"{chart.bpm:.0f} BPM",
                "position": [0.3, y],
                "size": self.font_size_small,
                "color": self.dimmed_color,
                "layer": 2,
            })
            
            # 游玩次数
            if chart.play_count > 0:
                objects.append({
                    "type": "text",
                    "text": f"游玩: {chart.play_count}",
                    "position": [0.3, y - 0.04],
                    "size": self.font_size_small,
                    "color": self.dimmed_color,
                    "layer": 2,
                })
        
        # 选中的谱面详情
        selected_chart = self.ui.get_selected_chart()
        if selected_chart:
            # 详情面板
            objects.append({
                "type": "rectangle",
                "position": [0.0, -0.6],
                "size": [1.6, 0.4],
                "color": [0.1, 0.1, 0.15, 1.0],
                "layer": 1,
            })
            
            # 标题
            objects.append({
                "type": "text",
                "text": selected_chart.title,
                "position": [-0.7, -0.45],
                "size": self.font_size_normal,
                "color": self.normal_color,
                "layer": 2,
            })
            
            # 艺术家
            objects.append({
                "type": "text",
                "text": f"艺术家: {selected_chart.artist}",
                "position": [-0.7, -0.55],
                "size": self.font_size_small,
                "color": self.normal_color,
                "layer": 2,
            })
            
            # 制作者
            objects.append({
                "type": "text",
                "text": f"制作者: {selected_chart.creator}",
                "position": [-0.7, -0.65],
                "size": self.font_size_small,
                "color": self.normal_color,
                "layer": 2,
            })
            
            # 难度列表
            difficulty = self.ui.get_selected_difficulty()
            if difficulty:
                objects.append({
                    "type": "text",
                    "text": f"难度: {difficulty['name']} (等级 {difficulty.get('level', 1)})",
                    "position": [0.3, -0.45],
                    "size": self.font_size_small,
                    "color": self.normal_color,
                    "layer": 2,
                })
            
            # 游玩按钮
            objects.append({
                "type": "rectangle",
                "position": [0.5, -0.7],
                "size": [0.3, 0.08],
                "color": [0.2, 0.8, 0.2, 1.0],
                "layer": 1,
            })
            objects.append({
                "type": "text",
                "text": "游玩",
                "position": [0.5, -0.7],
                "size": self.font_size_normal,
                "color": [1.0, 1.0, 1.0, 1.0],
                "layer": 2,
            })
        
        # 统计信息
        objects.append({
            "type": "text",
            "text": f"谱面数: {len(self.ui.charts)} | 显示: {len(self.ui.filtered_charts)}",
            "position": [0.0, -0.85],
            "size": self.font_size_small,
            "color": self.dimmed_color,
            "layer": 2,
        })
        
        return objects