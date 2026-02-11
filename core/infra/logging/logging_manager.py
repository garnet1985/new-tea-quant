"""
LoggingManager - 集中管理项目日志配置

职责：
- 从 ConfigManager 加载 logging.json（支持 userspace 覆盖）；
- 初始化全局 logging（根 logger 的 level / format / datefmt）；
- 可选地为特定模块设置独立的日志级别（module_levels）。

设计要点：
- idempotent：多次调用 setup_logging() 只会生效一次；
- 不直接写入文件，只配置标准库 logging；
- 不强制要求所有模块使用本模块，只要通过 logging.getLogger(__name__) 即可受控。
"""

from __future__ import annotations

import logging as _logging
from typing import Any, Dict, Optional

from core.infra.project_context.config_manager import ConfigManager


class LoggingManager:
    """集中管理项目日志配置的帮助类。"""

    _configured: bool = False

    @classmethod
    def setup_logging(cls, config: Optional[Dict[str, Any]] = None) -> None:
        """
        初始化全局 logging 配置。

        Args:
            config: 可选的日志配置字典；如果为 None，则通过
                    ConfigManager.load_core_config('logging', ...) 自动加载。
        """
        if cls._configured:
            return

        if config is None:
            # 加载合并后的 logging 配置（core/default_config/logging.json + userspace/config/logging.json）
            config = ConfigManager.load_core_config(
                "logging",
                deep_merge_fields=set(),
                override_fields=set(),
            ) or {}

        # 1. 解析全局级别与格式
        level_name = str(config.get("level", "INFO")).upper()
        level = getattr(_logging, level_name, _logging.INFO)

        log_format = config.get(
            "format",
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        )
        datefmt = config.get("datefmt", "%Y-%m-%d %H:%M:%S")

        root_logger = _logging.getLogger()

        # 2. 如果根 logger 尚未配置 handler，则使用 basicConfig 初始化
        if not root_logger.handlers:
            _logging.basicConfig(level=level, format=log_format, datefmt=datefmt)
        else:
            # 已有 handler 时，仅更新 level
            root_logger.setLevel(level)

        # 3. 为特定模块设置日志级别（可选）
        module_levels = config.get("module_levels", {}) or {}
        for logger_name, logger_level_name in module_levels.items():
            logger_level = getattr(
                _logging,
                str(logger_level_name).upper(),
                level,
            )
            _logging.getLogger(logger_name).setLevel(logger_level)

        cls._configured = True

    @staticmethod
    def get_logger(name: Optional[str] = None) -> _logging.Logger:
        """
        获取 logger，等价于 logging.getLogger(name)。

        Args:
            name: logger 名称；为 None 时返回根 logger。
        """
        return _logging.getLogger(name)

