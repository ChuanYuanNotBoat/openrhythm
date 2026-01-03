# mystia_rhythm/core/chart_parser.py
"""
Malody谱面解析器
解析.mc和.mc.json格式的谱面文件
"""
import logging
import json
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class NoteType(Enum):
    """音符类型（根据Malody文档）"""
    TAP = 1      # 点击
    HOLD = 2     # 长按
    DRAG = 3     # 拖拽
    FLICK = 4    # 滑键
    
@dataclass
class Note:
    """音符数据"""
    beat: List[float]        # [整数拍, 分子, 分母]
    column: int              # 轨道（0-3）
    endbeat: Optional[List[float]] = None  # 长按结束拍
    type: NoteType = NoteType.TAP  # 音符类型
    sound: Optional[str] = None    # 音效文件
    volume: float = 1.0            # 音量
    
@dataclass
class TimeEvent:
    """时间事件（BPM变化等）"""
    beat: List[float]
    bpm: Optional[float] = None
    time_signature: Optional[Tuple[int, int]] = None
    
@dataclass
class EffectEvent:
    """效果事件"""
    beat: List[float]
    type: str
    params: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class ChartMetadata:
    """谱面元数据"""
    title: str = ""
    artist: str = ""
    charter: str = ""
    difficulty: str = ""
    level: int = 0
    bpm: float = 120.0
    time_signature: Tuple[int, int] = (4, 4)
    preview_time: float = 0.0
    background: str = ""
    cover: str = ""
    audio_path: Optional[Path] = None  # 添加音频路径字段
    
@dataclass
class Chart:
    """完整的谱面数据"""
    metadata: ChartMetadata
    notes: List[Note]
    time_events: List[TimeEvent]
    effect_events: List[EffectEvent]
    timing_system: Optional[Any] = None  # 时间系统实例
    
    # 自定义扩展数据（Mod使用）
    custom_data: Dict[str, Any] = field(default_factory=dict)


class ChartParser:
    """谱面解析器"""
    
    @staticmethod
    def load_from_file(file_path: Path) -> Optional[Chart]:
        """
        从文件加载谱面
        支持 .mc, .mc.json, .mcz 格式
        """
        logger.debug(f"尝试加载谱面: {file_path}")
        
        if not file_path.exists():
            logger.error(f"谱面文件不存在: {file_path}")
            return None
            
        try:
            # 先尝试检测文件类型
            with open(file_path, 'rb') as f:
                first_bytes = f.read(10)
                f.seek(0)
                
                # 检查是否是JSON格式（以 { 或 [ 开头）
                if first_bytes.startswith(b'{') or first_bytes.startswith(b'['):
                    logger.debug(f"检测到 JSON 格式: {file_path}")
                    return ChartParser._load_json(file_path)
                # 检查是否是.mcz压缩包
                elif file_path.suffix == '.mcz':
                    logger.debug("检测到 .mcz 格式")
                    return ChartParser._load_mcz(file_path)
                # 否则尝试二进制格式
                else:
                    logger.debug("检测到二进制格式")
                    return ChartParser._load_binary(file_path)
                    
        except Exception as e:
            logger.error(f"谱面加载异常: {e}")
            return None
            
    @staticmethod
    def _load_mcz(mcz_path: Path) -> Optional[Chart]:
        """加载.mcz压缩包"""
        try:
            with zipfile.ZipFile(mcz_path, 'r') as zf:
                # 查找谱面文件
                chart_files = [f for f in zf.namelist() if f.endswith('.mc') or f.endswith('.mc.json')]
                if not chart_files:
                    return None
                    
                # 读取第一个谱面文件
                chart_data = zf.read(chart_files[0])
                
                # 尝试解析JSON
                try:
                    chart_dict = json.loads(chart_data.decode('utf-8'))
                    return ChartParser._parse_dict(chart_dict, mcz_path)
                except:
                    # 否则尝试二进制
                    return ChartParser._parse_binary(chart_data)
                    
        except Exception as e:
            logger.error(f"加载.mcz失败: {e}")
            return None
            
    @staticmethod
    def _load_json(json_path: Path) -> Optional[Chart]:
        """加载JSON格式谱面"""
        try:
            logger.debug(f"加载JSON谱面: {json_path}")
            with open(json_path, 'r', encoding='utf-8') as f:
                chart_dict = json.load(f)
            chart = ChartParser._parse_dict(chart_dict, json_path)
            if chart:
                logger.info(f"谱面加载成功: {chart.metadata.title} (Lv.{chart.metadata.level})")
                logger.debug(f"音符数: {len(chart.notes)}, 时间事件: {len(chart.time_events)}")
            return chart
        except Exception as e:
            logger.error(f"JSON谱面加载失败: {e}")
            return None
            
    @staticmethod
    def _load_binary(bin_path: Path) -> Optional[Chart]:
        """加载二进制格式谱面"""
        try:
            with open(bin_path, 'rb') as f:
                data = f.read()
            return ChartParser._parse_binary(data)
        except Exception as e:
            logger.error(f"加载二进制谱面失败: {e}")
            return None
            
    @staticmethod
    def _parse_binary(data: bytes) -> Optional[Chart]:
        """解析二进制格式（简化版本）"""
        # 注意：完整的Malody二进制格式解析较复杂
        # 这里只提供基本结构
        logger.warning("二进制谱面解析未完整实现")
        return None
        
    @staticmethod
    def _parse_dict(chart_dict: Dict[str, Any], file_path: Path) -> Chart:
        """解析字典格式的谱面数据"""
        # 解析元数据
        meta = chart_dict.get('meta', {})
        song = meta.get('song', {})
        mode_ext = meta.get('mode_ext', {})
        
        metadata = ChartMetadata(
            title=song.get('title', ''),
            artist=song.get('artist', ''),
            charter=meta.get('creator', ''),
            difficulty=meta.get('version', ''),
            level=meta.get('level', 0),
            bpm=120.0,  # 从time中获取
            preview_time=meta.get('preview', 0),
            background=meta.get('background', ''),
            cover=meta.get('cover', meta.get('background', ''))
        )
        
        # 查找音频文件（从谱面文件中提取或搜索目录）
        chart_dir = file_path.parent
        # 首先检查谱面note中是否有音频文件
        note_data = chart_dict.get('note', [])
        for note_obj in note_data:
            if note_obj.get('sound'):
                audio_file = chart_dir / note_obj['sound']
                if audio_file.exists():
                    metadata.audio_path = audio_file
                    break
        
        # 如果没有找到，搜索目录中的音频文件
        if not metadata.audio_path:
            for ext in ['.ogg', '.mp3', '.wav']:
                audio_files = list(chart_dir.glob(f'*{ext}'))
                if audio_files:
                    metadata.audio_path = audio_files[0]
                    break
        
        # 解析时间事件（BPM变化）
        time_events = []
        time_data = chart_dict.get('time', [])
        for time_event in time_data:
            beat = time_event.get('beat', [0, 0, 1])
            bpm = time_event.get('bpm')
            if bpm:
                time_events.append(TimeEvent(beat=beat, bpm=bpm))
                
        # 设置初始BPM
        if time_events and time_events[0].bpm:
            metadata.bpm = time_events[0].bpm
        elif time_data and 'bpm' in time_data[0]:
            metadata.bpm = time_data[0]['bpm']
            
        # 解析音符
        notes = []
        note_data = chart_dict.get('note', [])
        for note_obj in note_data:
            # 跳过音频对象（type=1）
            if note_obj.get('type') == 1:
                continue
                
            beat = note_obj.get('beat', [0, 0, 1])
            column = note_obj.get('column', 0)
            
            # 处理长按
            endbeat = note_obj.get('endbeat')
            
            # 确定音符类型
            note_type = NoteType.TAP
            type_val = note_obj.get('type')
            if type_val == 2:
                note_type = NoteType.HOLD
            elif type_val == 3:
                note_type = NoteType.DRAG
            elif type_val == 4:
                note_type = NoteType.FLICK
                
            # 音效
            sound = note_obj.get('sound')
            volume = note_obj.get('vol', 1.0)
            
            note = Note(
                beat=beat,
                column=column,
                endbeat=endbeat,
                type=note_type,
                sound=sound,
                volume=volume
            )
            notes.append(note)
            
        # 解析效果事件
        effect_events = []
        effect_data = chart_dict.get('effect', [])
        for effect_obj in effect_data:
            beat = effect_obj.get('beat', [0, 0, 1])
            effect_type = effect_obj.get('type', '')
            params = effect_obj.get('params', {})
            
            effect_events.append(EffectEvent(
                beat=beat,
                type=effect_type,
                params=params
            ))
            
        # 创建谱面对象
        chart = Chart(
            metadata=metadata,
            notes=notes,
            time_events=time_events,
            effect_events=effect_events
        )
        
        # 创建时间系统
        from .timing import TimingSystem
        timing = TimingSystem(metadata.bpm)
        for event in time_events:
            # 计算总拍数
            if len(event.beat) == 3:
                whole, num, den = event.beat
                beat_pos = whole + (num / den)
            else:
                beat_pos = float(event.beat[0])
            if event.bpm:
                timing.add_bpm_change(beat_pos, event.bpm)
            
        chart.timing_system = timing
        
        # 解析自定义数据（扩展字段）
        custom_data = {}
        for key, value in chart_dict.items():
            if key not in ['meta', 'time', 'note', 'effect']:
                custom_data[key] = value
                
        chart.custom_data = custom_data
        
        return chart
        
    @staticmethod
    def save_to_file(chart: Chart, file_path: Path, format: str = 'json') -> bool:
        """
        保存谱面到文件
        
        Args:
            chart: 谱面数据
            file_path: 保存路径
            format: 格式 ('json' 或 'binary')
        """
        try:
            if format == 'json':
                return ChartParser._save_json(chart, file_path)
            else:
                return ChartParser._save_binary(chart, file_path)
        except Exception as e:
            logger.error(f"保存谱面失败: {e}")
            return False
            
    @staticmethod
    def _save_json(chart: Chart, file_path: Path) -> bool:
        """保存为JSON格式"""
        chart_dict = ChartParser._chart_to_dict(chart)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(chart_dict, f, indent=2, ensure_ascii=False)
        return True
        
    @staticmethod
    def _save_binary(chart: Chart, file_path: Path) -> bool:
        """保存为二进制格式"""
        # 简化实现
        logger.warning("二进制谱面保存未完整实现")
        return False
        
    @staticmethod
    def _chart_to_dict(chart: Chart) -> Dict[str, Any]:
        """将Chart对象转换为字典"""
        result = {}
        
        # 元数据
        meta = {
            'creator': chart.metadata.charter,
            'background': chart.metadata.background,
            'version': chart.metadata.difficulty,
            'id': 0,
            'mode': 0,
            'time': 0,  # 时间戳
            'song': {
                'title': chart.metadata.title,
                'artist': chart.metadata.artist,
                'id': 0
            },
            'mode_ext': {
                'column': 4,  # 默认4键
                'bar_begin': 0
            }
        }
        
        if chart.metadata.cover:
            meta['cover'] = chart.metadata.cover
        if chart.metadata.preview_time > 0:
            meta['preview'] = chart.metadata.preview_time
            
        result['meta'] = meta
        
        # 时间事件
        time_events = []
        for event in chart.time_events:
            time_event = {'beat': event.beat}
            if event.bpm:
                time_event['bpm'] = event.bpm
            time_events.append(time_event)
            
        result['time'] = time_events
        
        # 音符
        notes = []
        for note in chart.notes:
            note_dict = {
                'beat': note.beat,
                'column': note.column,
                'type': note.type.value
            }
            
            if note.endbeat:
                note_dict['endbeat'] = note.endbeat
            if note.sound:
                note_dict['sound'] = note.sound
            if note.volume != 1.0:
                note_dict['vol'] = note.volume
                
            notes.append(note_dict)
            
        result['note'] = notes
        
        # 效果事件
        if chart.effect_events:
            effects = []
            for event in chart.effect_events:
                effect_dict = {
                    'beat': event.beat,
                    'type': event.type,
                    'params': event.params
                }
                effects.append(effect_dict)
            result['effect'] = effects
            
        # 自定义数据
        for key, value in chart.custom_data.items():
            result[key] = value
            
        return result