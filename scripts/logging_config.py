from typing import Optional
import os
import logging
import time

def setup_logger(name: str, log_dir: Optional[str] = None) -> logging.Logger:
    """
    设置统一的日志配置
    Param:
        name: logger name
        log_dir: logger directory
    Returns:
        配置好的logger实例
    """
    logging.getLogger().setLevel(logging.DEBUG)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate=False

    if logger.handlers:
        return logger

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)

    if log_dir is None:
        log_dir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file=os.path.join(log_dir, f"{name}.log")
    file_handler = logging.FileHandler(log_file,encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


"""
SUCCESS_ICON = "✓"
ERROR_ICON = "✗"
WAIT_ICON = "🔄"
"""
