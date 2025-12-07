"""
OpenRhythm - 模块化音游平台
"""

__version__ = "0.1.0"
__author__ = "OpenRhythm Team"

import sys
import os
from pathlib import Path

# 添加核心库路径
core_lib_path = Path(__file__).parent.parent.parent / "target" / "release"
if core_lib_path.exists():
    sys.path.insert(0, str(core_lib_path))

try:
    from openrhythm_core import *
    _core_available = True
except ImportError:
    _core_available = False
    print("警告: 核心库未找到，请先编译Rust核心")

# 导出公共API
if _core_available:
    __all__ = [
        'CoreConfig',
        'EventBus',
        'ServiceContainer',
        'ModLoader',
    ]
else:
    __all__ = []