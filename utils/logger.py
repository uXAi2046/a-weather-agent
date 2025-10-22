"""
日志配置模块
使用loguru提供结构化日志功能
"""

import sys
import os
from pathlib import Path
from typing import Optional
from loguru import logger

from config.settings import settings


def setup_logger(name: Optional[str] = None, 
                level: Optional[str] = None,
                log_file: Optional[str] = None) -> logger:
    """设置日志配置
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径
        
    Returns:
        配置好的logger实例
    """
    # 使用配置中的默认值
    level = level or settings.log_level
    log_file = log_file or settings.log_file
    
    # 移除默认处理器
    logger.remove()
    
    # 控制台输出格式
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 文件输出格式
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # 添加控制台处理器
    logger.add(
        sys.stdout,
        format=console_format,
        level=level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # 创建日志目录
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 添加文件处理器
    logger.add(
        log_file,
        format=file_format,
        level=level,
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        encoding="utf-8"
    )
    
    # 如果指定了名称，返回绑定的logger
    if name:
        return logger.bind(name=name)
    
    return logger


def get_logger(name: str) -> logger:
    """获取指定名称的logger
    
    Args:
        name: logger名称
        
    Returns:
        logger实例
    """
    return logger.bind(name=name)


# 预配置的logger实例
main_logger = setup_logger("main")
agent_logger = setup_logger("agent")
mcp_logger = setup_logger("mcp")
weather_logger = setup_logger("weather")


if __name__ == "__main__":
    # 测试日志功能
    test_logger = setup_logger("test")
    
    test_logger.debug("这是调试信息")
    test_logger.info("这是信息日志")
    test_logger.warning("这是警告信息")
    test_logger.error("这是错误信息")
    
    try:
        1 / 0
    except Exception as e:
        test_logger.exception("这是异常信息")
    
    print("日志测试完成，请检查日志文件")