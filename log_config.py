# mystia_rhythm/log_config.py
"""
全局日志配置
"""
import logging
import sys
from pathlib import Path

def setup_global_logging():
    """设置全局日志配置"""
    # 获取项目根目录
    root_dir = Path(__file__).parent
    
    # 创建日志目录
    log_dir = root_dir / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # 日志文件
    log_file = log_dir / 'mystia_rhythm.log'
    
    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 主日志器
    main_logger = logging.getLogger('mystia')
    main_logger.setLevel(logging.DEBUG)
    main_logger.propagate = False
    
    # 清空现有处理器
    main_logger.handlers.clear()
    
    # 添加处理器
    main_logger.addHandler(file_handler)
    main_logger.addHandler(console_handler)
    
    # 配置kivy日志器
    kivy_logger = logging.getLogger('kivy')
    kivy_logger.setLevel(logging.WARNING)
    
    return main_logger

# 创建全局日志器
logger = setup_global_logging()