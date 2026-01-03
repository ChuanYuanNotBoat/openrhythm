# mystia_rhythm/ui/song_select.py
"""
选曲界面
显示所有可用歌曲和谱面
"""
import logging
import os
from pathlib import Path
from typing import List, Dict, Optional

from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.core.image import Image as CoreImage
from kivy.animation import Animation

from .ui_base import BaseScreen, CustomButton
from core.chart_parser import ChartParser
from config import config, BEATMAP_DIR

logger = logging.getLogger(__name__)


class SongInfo:
    """歌曲信息"""

    def __init__(self, song_id: str, title: str, artist: str,
                 cover_path: Optional[Path] = None):
        self.song_id = song_id
        self.title = title
        self.artist = artist
        self.cover_path = cover_path
        self.charts: List[Dict] = []  # 所有谱面

    def add_chart(self, chart_path: Path, difficulty: str, level: int):
        """添加谱面"""
        self.charts.append({
            'path': chart_path,
            'difficulty': difficulty,
            'level': level
        })

    def sort_charts(self):
        """按难度排序谱面"""
        self.charts.sort(key=lambda x: x['level'])


class SongButton(CustomButton):
    """歌曲按钮"""

    def __init__(self, song_info: SongInfo, **kwargs):
        super().__init__(**kwargs)
        self.song_info = song_info

        # 创建布局
        self.size_hint = (None, None)
        self.size = (300, 100)

        # 封面图
        cover = Image(size_hint=(None, None), size=(80, 80),
                      pos_hint={'center_y': 0.5})
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
        self.add_widget(cover)

        # 文本信息
        text_layout = RelativeLayout(pos=(90, 0), size_hint=(None, None), size=(200, 100))

        title_label = Label(text=song_info.title, font_size=20,
                            halign='left', valign='middle',
                            size_hint=(None, None), size=(200, 50),
                            pos=(0, 50))
        title_label.bind(size=title_label.setter('text_size'))

        artist_label = Label(text=song_info.artist, font_size=14,
                             halign='left', valign='middle',
                             size_hint=(None, None), size=(200, 30),
                             pos=(0, 20))
        artist_label.bind(size=artist_label.setter('text_size'))

        charts_label = Label(text=f"{len(song_info.charts)}个谱面", font_size=12,
                             halign='left', valign='middle',
                             size_hint=(None, None), size=(200, 20),
                             pos=(0, 0))
        charts_label.bind(size=charts_label.setter('text_size'))

        text_layout.add_widget(title_label)
        text_layout.add_widget(artist_label)
        text_layout.add_widget(charts_label)
        self.add_widget(text_layout)


class DifficultyButton(CustomButton):
    """难度按钮"""

    def __init__(self, chart_info: Dict, **kwargs):
        super().__init__(**kwargs)
        self.chart_info = chart_info

        self.size_hint = (None, None)
        self.size = (200, 50)

        diff_label = Label(text=chart_info['difficulty'], font_size=16,
                           halign='center', valign='middle')
        diff_label.bind(size=diff_label.setter('text_size'))
        self.add_widget(diff_label)


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
        logger.debug(f"目录是否存在: {BEATMAP_DIR.exists()}")
        
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
                        chart.metadata.level or 0
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
        
        # 主布局
        main_layout = GridLayout(cols=1, spacing=10, padding=20,
                                 size_hint_y=None)
        main_layout.bind(minimum_height=main_layout.setter('height'))

        # 标题
        title_label = Label(text='选择歌曲', font_size=32,
                            size_hint_y=None, height=60,
                            color=[1, 1, 1, 1])
        main_layout.add_widget(title_label)

        # 歌曲列表
        if self.songs:
            songs_layout = GridLayout(cols=1, spacing=5,
                                      size_hint_y=None)
            songs_layout.bind(minimum_height=songs_layout.setter('height'))

            for song_info in self.songs:
                song_btn = SongButton(song_info)
                song_btn.bind(on_release=lambda btn: self._on_song_selected(btn.song_info))
                songs_layout.add_widget(song_btn)

            # 滚动视图
            scroll_view = ScrollView(size_hint=(1, 1))
            scroll_view.add_widget(songs_layout)  # 改为添加 songs_layout
            
            self.add_widget(scroll_view)
        else:
            # 没有歌曲时显示提示
            no_songs_label = Label(
                text='未找到谱面\n请将谱面文件放置在：\n' + str(BEATMAP_DIR),
                font_size=20,
                halign='center',
                valign='middle',
                size_hint=(1, 1)
            )
            no_songs_label.bind(size=no_songs_label.setter('text_size'))
            self.add_widget(no_songs_label)

        # 难度选择面板（初始隐藏）
        self.diff_panel = GridLayout(cols=1, spacing=5, padding=10,
                                     size_hint=(None, None), size=(400, 300),
                                     pos_hint={'center_x': 0.5, 'center_y': 0.5})
        self.diff_panel.opacity = 0  # 隐藏
        
        # 返回按钮
        back_btn = CustomButton(text='返回', size_hint=(None, None),
                          size=(100, 50), pos_hint={'x': 0.05, 'y': 0.05})
        back_btn.bind(on_release=self._on_back)

        # 添加到界面
        self.add_widget(self.diff_panel)
        self.add_widget(back_btn)

    def _on_song_selected(self, song_info: SongInfo) -> None:
        """歌曲被选中"""
        self.current_song = song_info

        # 显示难度选择面板
        self._show_difficulty_panel(song_info)

    def _show_difficulty_panel(self, song_info: SongInfo) -> None:
        """显示难度选择面板"""
        # 清空面板
        self.diff_panel.clear_widgets()

        # 标题
        title_label = Label(text=f'选择难度: {song_info.title}',
                            font_size=20, size_hint_y=None, height=40,
                            color=[1, 1, 1, 1])
        self.diff_panel.add_widget(title_label)

        # 难度按钮
        for chart_info in song_info.charts:
            diff_btn = DifficultyButton(chart_info)
            diff_btn.bind(on_release=lambda btn: self._on_difficulty_selected(btn.chart_info))
            self.diff_panel.add_widget(diff_btn)

        # 取消按钮
        cancel_btn = CustomButton(text='取消', size_hint_y=None, height=40)
        cancel_btn.bind(on_release=self._hide_difficulty_panel)
        self.diff_panel.add_widget(cancel_btn)

        # 显示面板
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
            
            if self.game_engine.load_chart(chart):
                logger.info("谱面加载到游戏引擎")

                self._hide_difficulty_panel()
                self.game_engine.start_game()
                if self.game_engine.play_ui:
                    self.parent.current = 'play'

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