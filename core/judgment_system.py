# mystia_rhythm/core/judgment_system.py
"""
判定系统
处理音符命中判定、连击和分数计算
注意：本体不做死亡判定，只计算分数和准确率
"""
from typing import List, Dict, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass
from enum import Enum
import time

if TYPE_CHECKING:
    from .chart_parser import Note

class Judgment(Enum):
    """判定等级"""
    BEST = 0      # 完美
    COOL = 1      # 良好
    GOOD = 2      # 一般
    MISS = 3      # 错过
    NONE = 4      # 未判定
    
@dataclass
class JudgmentWindow:
    """判定时间窗口（毫秒）"""
    best: float   # ±窗口
    cool: float
    good: float
    
    @classmethod
    def default(cls) -> 'JudgmentWindow':
        return cls(best=40, cool=80, good=120)
        
    @classmethod
    def strict(cls) -> 'JudgmentWindow':
        return cls(best=25, cool=50, good=100)
        
    @classmethod
    def lenient(cls) -> 'JudgmentWindow':
        return cls(best=60, cool=120, good=180)

@dataclass  
class JudgmentResult:
    """判定结果"""
    judgment: Judgment
    offset: float  # 时间偏移（毫秒）
    score: int    # 得分
    combo: int    # 当前连击数
    
class ScoreCalculator:
    """分数计算器"""
    
    def __init__(self, max_combo: int = 0):
        self.max_combo = max_combo
        self.combo = 0
        self.score = 0
        self.judgments: Dict[Judgment, int] = {
            Judgment.BEST: 0,
            Judgment.COOL: 0,
            Judgment.GOOD: 0,
            Judgment.MISS: 0
        }
        
        # 分数权重
        self.weights = {
            Judgment.BEST: 100,
            Judgment.COOL: 80,
            Judgment.GOOD: 50,
            Judgment.MISS: 0
        }
        
        # 连击加成
        self.combo_multiplier = 0.01  # 每连击增加1%分数
        
    def add_judgment(self, judgment: Judgment, note_score: int = 100) -> JudgmentResult:
        """添加判定结果"""
        self.judgments[judgment] += 1
        
        # 更新连击
        if judgment == Judgment.MISS:
            self.combo = 0
        else:
            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            
        # 计算基础分数
        base_score = self.weights.get(judgment, 0)
        
        # 应用连击加成
        combo_bonus = 1.0 + (self.combo * self.combo_multiplier)
        final_score = int(base_score * combo_bonus)
        self.score += final_score
        
        return JudgmentResult(
            judgment=judgment,
            offset=0,
            score=final_score,
            combo=self.combo
        )
        
    def get_accuracy(self) -> float:
        """计算准确率"""
        total_notes = sum(self.judgments.values())
        if total_notes == 0:
            return 0.0
            
        weighted_sum = (
            self.judgments[Judgment.BEST] * 1.0 +
            self.judgments[Judgment.COOL] * 0.8 +
            self.judgments[Judgment.GOOD] * 0.5
        )
        
        return weighted_sum / total_notes * 100
        
    def reset(self) -> None:
        """重置分数"""
        self.combo = 0
        self.score = 0
        for key in self.judgments:
            self.judgments[key] = 0


class JudgmentSystem:
    """
    判定系统
    处理实时音符判定
    注意：本体不做死亡判定
    """
    
    def __init__(self, windows: JudgmentWindow = None):
        self.windows = windows or JudgmentWindow.default()
        self.calculator = ScoreCalculator()
        self.active_notes: Dict[int, 'Note'] = {}  # 活跃音符（按ID）
        self.judged_notes: Dict[int, JudgmentResult] = {}  # 已判定音符
        
        # 判定偏移（毫秒）
        self.offset = 0
        
    def set_offset(self, offset_ms: float) -> None:
        """设置判定偏移"""
        self.offset = offset_ms / 1000.0  # 转换为秒
        
    def judge_note(self, note: 'Note', current_time: float, 
                   note_time: float, key_pressed: bool = False) -> Optional[JudgmentResult]:
        """
        判定音符
        
        Args:
            note: 音符对象
            current_time: 当前游戏时间
            note_time: 音符应该被击中的时间
            key_pressed: 按键是否按下（对于长按）
            
        Returns:
            判定结果或None（如果未判定）
        """
        # 计算时间差（考虑偏移）
        time_diff = abs(current_time - note_time) - self.offset
        
        # 转换为毫秒
        time_diff_ms = time_diff * 1000
        
        # 判断是否在判定窗口内
        judgment = Judgment.NONE
        
        if time_diff_ms <= self.windows.best:
            judgment = Judgment.BEST
        elif time_diff_ms <= self.windows.cool:
            judgment = Judgment.COOL
        elif time_diff_ms <= self.windows.good:
            judgment = Judgment.GOOD
        else:
            # 错过判定
            if current_time > note_time + (self.windows.good / 1000):
                judgment = Judgment.MISS
                
        if judgment != Judgment.NONE:
            result = self.calculator.add_judgment(judgment)
            result.offset = time_diff_ms
            return result
            
        return None
        
    def judge_hold_note(self, note: 'Note', start_time: float, end_time: float,
                        current_time: float, key_down: bool) -> Optional[JudgmentResult]:
        """
        判定长按音符
        
        Args:
            note: 长按音符
            start_time: 长按开始时间
            end_time: 长按结束时间
            current_time: 当前时间
            key_down: 按键是否按住
            
        Returns:
            判定结果或None
        """
        # 检查开始判定
        if current_time >= start_time and note.id not in self.judged_notes:
            # 判定开始点
            return self.judge_note(note, current_time, start_time, True)
            
        # 检查过程中（需要持续按住）
        if start_time <= current_time <= end_time:
            if not key_down:
                # 提前松开，判定为MISS
                result = self.calculator.add_judgment(Judgment.MISS)
                result.offset = (current_time - start_time) * 1000
                return result
                
        # 检查结束判定
        if current_time >= end_time and note.id not in self.judged_notes:
            # 判定结束点
            return self.judge_note(note, current_time, end_time, True)
            
        return None
        
    def get_accuracy(self) -> float:
        """获取当前准确率"""
        return self.calculator.get_accuracy()
        
    def get_score(self) -> int:
        """获取当前分数"""
        return self.calculator.score
        
    def get_combo(self) -> int:
        """获取当前连击"""
        return self.calculator.combo
        
    def get_max_combo(self) -> int:
        """获取最大连击"""
        return self.calculator.max_combo
        
    def reset(self) -> None:
        """重置判定系统"""
        self.calculator.reset()
        self.active_notes.clear()
        self.judged_notes.clear()