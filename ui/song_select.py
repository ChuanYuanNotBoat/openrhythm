# mystia_rhythm/ui/song_select.py
"""
选曲界面
显示所有可用歌曲和谱面
"""
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional

from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.animation import Animation

from .ui_base import BaseScreen, CustomButton, CustomLabel
from core.chart_parser import ChartParser
from config import config, BEATMAP_DIR

logger = logging.getLogger(__name__)

# 模式名称映射
MODE_NAMES = {
    0: "Key",
    1: "Step", 
    2: "DJ",
    3: "Catch",
    4: "Pad",
    5: "Taiko",
    6: "Ring", 
    7: "Slide",
    8: "Live",
    9: "Cube"
}

# 模式对应的列数显示
MODE_DISPLAY = {
    0: "K",  # Key模式用K表示，如4K, 6K, 8K等
    1: "S",  # Step
    2: "DJ",
    3: "CT", # Catch
    4: "P",  # Pad
    5: "T",  # Taiko
    6: "R",  # Ring
    7: "SL", # Slide
    8: "L",  # Live
    9: "C"   # Cube
}


class SongInfo:
    """歌曲信息"""

    def __init__(self, song_id: str, title: str, artist: str,
                 cover_path: Optional[Path] = None):
        self.song_id = song_id
        self.title = title
        self.artist = artist
        self.cover_path = cover_path
        self.charts: List[Dict] = []  # 所有谱面

    def add_chart(self, chart_path: Path, difficulty: str, level: int, 
                  charter: str = "Unknown", mode: int = 0, column: int = 4) -> None:
        """添加谱面
        Args:
            chart_path: 谱面文件路径
            difficulty: 难度名称
            level: 难度等级
            charter: 谱师
            mode: 模式编号
            column: 列数（轨道数）
        """
        self.charts.append({
            'path': chart_path,
            'difficulty': difficulty,
            'level': level,
            'charter': charter,
            'mode': mode,
            'column': column
        })

    def sort_charts(self) -> None:
        """按难度排序谱面"""
        self.charts.sort(key=lambda x: x['level'])


class SongButton(CustomButton):
    """歌曲按钮"""

    def __init__(self, song_info: SongInfo, **kwargs):
        super().__init__(**kwargs)
        self.song_info = song_info

        # 创建布局
        self.size_hint = (None, None)
        self.size = (400, 120)  # 增大尺寸以容纳更多信息

        # 创建主布局
        main_layout = BoxLayout(orientation='horizontal', spacing=10,
                                padding=5, size=self.size)
        
        # 左侧：封面图
        cover_layout = BoxLayout(orientation='vertical', size_hint=(0.3, 1))
        cover = Image(size_hint=(1, 1))
        if song_info.cover_path and song_info.cover_path.exists():
            try:
                cover.source = str(song_info.cover_path)
            except:
                # 使用默认封面
                default_cover = Path(__file__).parent.parent / 'assets' / 'images' / 'cover_placeholder.png'
                if default_cover.exists():
                    cover.source = str(default_cover)
        else:
            # 使用默认封面
            default_cover = Path(__file__).parent.parent / 'assets' / 'images' / 'cover_placeholder.png'
            if default_cover.exists():
                cover.source = str(default_cover)
        cover_layout.add_widget(cover)
        
        # 右侧：文本信息
        text_layout = BoxLayout(orientation='vertical', spacing=5, size_hint=(0.7, 1))
        
        # 歌曲标题
        title_label = CustomLabel(
            text=song_info.title,
            font_size=22,
            halign='left',
            valign='top',
            size_hint=(1, 0.4),
            color=[1, 1, 1, 1]
        )
        title_label.bind(size=title_label.setter('text_size'))
        
        # 艺术家
        artist_label = CustomLabel(
            text=f"艺术家: {song_info.artist}",
            font_size=16,
            halign='left',
            valign='middle',
            size_hint=(1, 0.3),
            color=[0.8, 0.8, 0.8, 1]
        )
        artist_label.bind(size=artist_label.setter('text_size'))
        
        # 谱面数量
        charts_label = CustomLabel(
            text=f"谱面: {len(song_info.charts)} 个",
            font_size=14,
            halign='left',
            valign='bottom',
            size_hint=(1, 0.3),
            color=[0.7, 0.7, 0.7, 1]
        )
        charts_label.bind(size=charts_label.setter('text_size'))
        
        text_layout.add_widget(title_label)
        text_layout.add_widget(artist_label)
        text_layout.add_widget(charts_label)
        
        main_layout.add_widget(cover_layout)
        main_layout.add_widget(text_layout)
        
        self.add_widget(main_layout)


class DifficultyButton(CustomButton):
    """难度按钮"""

    def __init__(self, chart_info: Dict, **kwargs):
        super().__init__(**kwargs)
        self.chart_info = chart_info

        self.size_hint = (None, None)
        self.size = (500, 80)  # 增大尺寸以显示更多信息

        # 创建主布局
        main_layout = BoxLayout(orientation='horizontal', spacing=10,
                                padding=10, size=self.size)
        
        # 左侧：模式显示
        mode_display = self._get_mode_display(chart_info)
        mode_layout = BoxLayout(orientation='vertical', size_hint=(0.2, 1))
        
        mode_label = CustomLabel(
            text=mode_display,
            font_size=18,
            halign='center',
            valign='middle',
            size_hint=(1, 1),
            color=[0.8, 1, 0.8, 1]
        )
        mode_layout.add_widget(mode_label)
        
        # 中间：难度信息
        info_layout = BoxLayout(orientation='vertical', spacing=2, size_hint=(0.6, 1))
        
        # 难度名称
        diff_label = CustomLabel(
            text=chart_info.get('difficulty', 'Unknown'),
            font_size=20,
            halign='left',
            valign='top',
            size_hint=(1, 0.5),
            color=[1, 1, 1, 1]
        )
        diff_label.bind(size=diff_label.setter('text_size'))
        
        # 谱师信息
        charter = chart_info.get('charter', 'Unknown')
        charter_label = CustomLabel(
            text=f"谱师: {charter}",
            font_size=14,
            halign='left',
            valign='bottom',
            size_hint=(1, 0.25),
            color=[0.8, 0.8, 0.8, 1]
        )
        charter_label.bind(size=charter_label.setter('text_size'))
        
        # 模式名称
        mode_name = MODE_NAMES.get(chart_info.get('mode', 0), "Unknown")
        mode_info_label = CustomLabel(
            text=f"模式: {mode_name}",
            font_size=14,
            halign='left',
            valign='bottom',
            size_hint=(1, 0.25),
            color=[0.8, 0.8, 0.8, 1]
        )
        mode_info_label.bind(size=mode_info_label.setter('text_size'))
        
        info_layout.add_widget(diff_label)
        info_layout.add_widget(charter_label)
        info_layout.add_widget(mode_info_label)
        
        # 右侧：等级显示
        level_layout = BoxLayout(orientation='vertical', size_hint=(0.2, 1))
        
        level = chart_info.get('level', 0)
        level_label = CustomLabel(
            text=f"Lv.{level}",
            font_size=24,
            halign='center',
            valign='middle',
            size_hint=(1, 1),
            color=self._get_level_color(level)
        )
        level_layout.add_widget(level_label)
        
        main_layout.add_widget(mode_layout)
        main_layout.add_widget(info_layout)
        main_layout.add_widget(level_layout)
        
        self.add_widget(main_layout)
    
    def _get_mode_display(self, chart_info: Dict) -> str:
        """获取模式显示字符串"""
        mode = chart_info.get('mode', 0)
        column = chart_info.get('column', 4)
        
        if mode == 0:  # Key模式
            return f"{column}K"
        else:
            mode_char = MODE_DISPLAY.get(mode, "?")
            return f"{mode_char}"
    
    def _get_level_color(self, level: int) -> List[float]:
        """根据等级获取颜色"""
        if level >= 20:
            return [1, 0.3, 0.3, 1]  # 红色
        elif level >= 15:
            return [1, 0.6, 0.2, 1]  # 橙色
        elif level >= 10:
            return [1, 1, 0.2, 1]  # 黄色
        elif level >= 5:
            return [0.5, 1, 0.5, 1]  # 绿色
        else:
            return [0.7, 0.7, 1, 1]  # 蓝色


class SongSelectScreen(BaseScreen):
    """选曲界面"""

    def __init__(self, game_engine, **kwargs):
        logger.info("初始化选曲界面")
        super().__init__(game_engine, **kwargs)
        self.songs: List[SongInfo] = []
        self.current_song: Optional[SongInfo] = None

        self._load_songs()
        logger.info(f"加载了 {len(self.songs)} 首歌曲")
        self._create_ui()

    def _load_songs(self) -> None:
        """加载所有歌曲"""
        logger.debug("开始加载谱面...")
        logger.debug(f"谱面目录: {BEATMAP_DIR}")
        
        self.songs.clear()

        if not BEATMAP_DIR.exists():
            logger.warning(f"谱面目录不存在: {BEATMAP_DIR}")
            return

        # 递归查找所有可能的谱面文件
        chart_files = []
        
        # 查找所有.mc和.mc.json文件
        for ext in ['.mc', '.mc.json']:
            for chart_file in BEATMAP_DIR.rglob(f'*{ext}'):
                chart_files.append(chart_file)
                
        logger.debug(f"找到 {len(chart_files)} 个谱面文件")
        
        # 按歌曲目录分组
        songs_by_dir = {}
        for chart_file in chart_files:
            song_dir = chart_file.parent
            if song_dir not in songs_by_dir:
                songs_by_dir[song_dir] = []
            songs_by_dir[song_dir].append(chart_file)
            
        # 处理每个歌曲目录
        for song_dir, chart_files in songs_by_dir.items():
            logger.debug(f"处理歌曲目录: {song_dir} (包含 {len(chart_files)} 个谱面)")
            
            # 尝试加载第一个谱面获取歌曲信息
            chart = None
            for chart_file in chart_files:
                chart = ChartParser.load_from_file(chart_file)
                if chart:
                    break
                    
            if not chart:
                logger.warning(f"无法加载任何谱面，跳过目录: {song_dir}")
                continue
                
            # 创建歌曲信息
            song_info = SongInfo(
                song_id=song_dir.name,
                title=chart.metadata.title or song_dir.name,
                artist=chart.metadata.artist or "Unknown"
            )

            # 查找封面
            cover_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.gif']
            cover_files = []
            for ext in cover_extensions:
                cover_files.extend(song_dir.glob(f'*{ext}'))
                
            # 优先使用background或cover命名的文件
            for cover_file in cover_files:
                if 'cover' in cover_file.name.lower() or 'background' in cover_file.name.lower():
                    song_info.cover_path = cover_file
                    break
                    
            if not song_info.cover_path and cover_files:
                song_info.cover_path = cover_files[0]
                
            # 添加所有谱面
            for chart_file in chart_files:
                chart = ChartParser.load_from_file(chart_file)
                if chart:
                    song_info.add_chart(
                        chart_file, 
                        chart.metadata.difficulty or "Unknown",
                        chart.metadata.level,
                        chart.metadata.charter or "Unknown",
                        chart.metadata.mode,
                        chart.metadata.column
                    )

            song_info.sort_charts()
            self.songs.append(song_info)
            logger.debug(f"添加歌曲: {song_info.title} - {len(song_info.charts)} 个谱面")

        # 按标题排序
        self.songs.sort(key=lambda x: x.title.lower())
        logger.info(f"谱面加载完成: 共 {len(self.songs)} 首歌曲")
        
    def _create_ui(self) -> None:
        """创建UI"""
        # 背景
        bg_path = Path(__file__).parent.parent / 'assets' / 'images' / 'bg_select.png'
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
        
        # 主布局 - 使用BoxLayout而不是GridLayout
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # 标题
        title_label = CustomLabel(
            text='选择歌曲',
            font_size=36,
            size_hint=(1, 0.1),
            color=[1, 1, 1, 1]
        )
        main_layout.add_widget(title_label)
        
        # 歌曲列表容器
        songs_container = BoxLayout(orientation='vertical', size_hint=(1, 0.8))
        
        if self.songs:
            # 创建滚动视图
            scroll_view = ScrollView(size_hint=(1, 1))
            
            # 歌曲列表网格布局
            songs_grid = GridLayout(cols=1, spacing=10, size_hint_y=None)
            songs_grid.bind(minimum_height=songs_grid.setter('height'))
            
            for song_info in self.songs:
                song_btn = SongButton(song_info)
                song_btn.bind(on_release=lambda btn: self._on_song_selected(btn.song_info))
                songs_grid.add_widget(song_btn)
            
            scroll_view.add_widget(songs_grid)
            songs_container.add_widget(scroll_view)
        else:
            # 没有歌曲时显示提示
            no_songs_label = CustomLabel(
                text='未找到谱面\n请将谱面文件放置在：\n' + str(BEATMAP_DIR),
                font_size=20,
                halign='center',
                valign='middle',
                size_hint=(1, 1),
                color=[1, 1, 1, 1]
            )
            no_songs_label.bind(size=no_songs_label.setter('text_size'))
            songs_container.add_widget(no_songs_label)
        
        main_layout.add_widget(songs_container)
        
        # 按钮区域
        button_area = BoxLayout(orientation='horizontal', size_hint=(1, 0.1), spacing=10)
        
        # 返回按钮
        back_btn = CustomButton(
            text='返回菜单',
            size_hint=(0.2, 1)
        )
        back_btn.bind(on_release=self._on_back)
        
        # 刷新按钮
        refresh_btn = CustomButton(
            text='刷新列表',
            size_hint=(0.2, 1)
        )
        refresh_btn.bind(on_release=self._on_refresh)
        
        button_area.add_widget(back_btn)
        button_area.add_widget(BoxLayout(size_hint=(0.6, 1)))  # 占位空间
        button_area.add_widget(refresh_btn)
        
        main_layout.add_widget(button_area)
        
        self.add_widget(main_layout)

        # 难度选择面板（初始隐藏）- 放在顶层
        self.diff_panel = BoxLayout(
            orientation='vertical',
            size_hint=(0.8, 0.8),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            spacing=10,
            padding=20
        )
        self.diff_panel.opacity = 0  # 隐藏
        
        # 为难度面板添加背景
        from kivy.graphics import Color, Rectangle
        with self.diff_panel.canvas.before:
            Color(0.1, 0.1, 0.1, 0.9)
            self.diff_bg_rect = Rectangle(pos=self.diff_panel.pos, size=self.diff_panel.size)
            self.diff_panel.bind(pos=self._update_diff_bg, size=self._update_diff_bg)
        
        self.add_widget(self.diff_panel)
    
    def _update_diff_bg(self, *args):
        """更新难度面板背景"""
        self.diff_bg_rect.pos = self.diff_panel.pos
        self.diff_bg_rect.size = self.diff_panel.size

    def _on_song_selected(self, song_info: SongInfo) -> None:
        """歌曲被选中"""
        self.current_song = song_info

        # 显示难度选择面板
        self._show_difficulty_panel(song_info)

    def _show_difficulty_panel(self, song_info: SongInfo) -> None:
        """显示难度选择面板"""
        # 清空面板
        self.diff_panel.clear_widgets()
        
        # 创建滚动视图
        scroll_view = ScrollView(size_hint=(1, 0.8))
        diff_grid = GridLayout(cols=1, spacing=10, size_hint_y=None)
        diff_grid.bind(minimum_height=diff_grid.setter('height'))
        
        # 标题
        title_label = CustomLabel(
            text=f'选择难度: {song_info.title}',
            font_size=24,
            size_hint_y=None,
            height=50,
            color=[1, 1, 1, 1]
        )
        diff_grid.add_widget(title_label)
        
        # 难度按钮
        for chart_info in song_info.charts:
            diff_btn = DifficultyButton(chart_info)
            diff_btn.bind(on_release=lambda btn, info=chart_info: self._on_difficulty_selected(info))
            diff_grid.add_widget(diff_btn)
        
        scroll_view.add_widget(diff_grid)
        self.diff_panel.add_widget(scroll_view)
        
        # 取消按钮
        cancel_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.2), spacing=20)
        
        cancel_btn = CustomButton(
            text='取消',
            size_hint=(0.5, 1)
        )
        cancel_btn.bind(on_release=self._hide_difficulty_panel)
        
        cancel_layout.add_widget(BoxLayout(size_hint=(0.25, 1)))  # 左占位
        cancel_layout.add_widget(cancel_btn)
        cancel_layout.add_widget(BoxLayout(size_hint=(0.25, 1)))  # 右占位
        
        self.diff_panel.add_widget(cancel_layout)

        # 显示面板
        self.diff_panel.opacity = 0
        anim = Animation(opacity=1, duration=0.3)
        anim.start(self.diff_panel)

    def _hide_difficulty_panel(self, *args) -> None:
        """隐藏难度选择面板"""
        anim = Animation(opacity=0, duration=0.3)
        anim.start(self.diff_panel)

    def _on_difficulty_selected(self, chart_info: Dict) -> None:
        """难度被选中"""
        logger.info(f"选择谱面: {self.current_song.title} - {chart_info['difficulty']}")

        chart = ChartParser.load_from_file(chart_info['path'])
        if chart:
            # 设置谱面文件路径用于查找资源
            self.game_engine.current_chart_path = chart_info['path']
            
            # 尝试加载音频
            chart_dir = chart_info['path'].parent
            audio_files = list(chart_dir.glob('*.ogg')) + list(chart_dir.glob('*.mp3'))
            if audio_files:
                chart.metadata.audio_path = audio_files[0]
                logger.debug(f"音频文件: {audio_files[0]}")
            else:
                logger.warning(f"未找到音频文件: {chart_dir}")
            
            if self.game_engine.load_chart(chart):
                logger.info("谱面加载到游戏引擎")

                self._hide_difficulty_panel()
                try:
                    self.game_engine.start_game()
                    logger.info("开始游戏")
                    
                    # 确保切换到游玩界面
                    if self.parent:
                        self.parent.current = 'play'
                        logger.info("已切换到游玩界面")
                    else:
                        logger.error("无法切换到游玩界面：没有父级屏幕管理器")
                except Exception as e:
                    logger.error(f"开始游戏失败: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                logger.error("谱面加载失败")
    
    def _on_refresh(self, *args):
        """刷新歌曲列表"""
        logger.info("刷新歌曲列表")
        self.songs.clear()
        self._load_songs()
        self.clear_widgets()
        self._create_ui()

    def _on_back(self, *args) -> None:
        """返回主菜单"""
        # 切换到主菜单
        self.parent.current = 'menu'

    def on_enter(self):
        """当进入界面时"""
        # 刷新歌曲列表
        self._load_songs()
        
        # 清空当前UI并重新创建
        self.clear_widgets()
        self._create_ui()

    def update(self, dt):
        """更新UI"""
        pass