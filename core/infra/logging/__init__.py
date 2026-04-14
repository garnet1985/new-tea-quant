"""
Logging package for New Tea Quant.

职责：
- 提供集中化的日志初始化入口；
- 基于 ConfigManager 加载 logging.json 配置；
- 为 core 内部模块提供一致的 logger 行为。
"""

from core.infra.logging.logging_manager import LoggingManager

__all__ = ["LoggingManager"]

