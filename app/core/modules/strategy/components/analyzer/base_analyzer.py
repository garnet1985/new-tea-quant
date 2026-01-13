#!/usr/bin/env python3
"""
BaseAnalyzer - 分析器基类

职责：
- 定义分析器的抽象接口
- 提供 AnalysisContext 数据类，封装分析所需的环境信息
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class AnalysisContext:
    """
    分析上下文，封装分析器运行所需的环境信息。
    """

    strategy_name: str
    sim_type: str  # "price_factor" 或 "capital_allocation"
    sim_version_dir: Path
    raw_settings: Dict[str, Any]

    # 可选字段（后续可扩展）
    enum_version_dir: Optional[Path] = None
    data_manager: Optional[Any] = None


class BaseAnalyzer(ABC):
    """
    分析器基类。

    所有分析器（StatisticalAnalyzer、MLAnalyzer）都应继承此类。
    """

    def __init__(self, context: AnalysisContext) -> None:
        """
        初始化分析器。

        Args:
            context: 分析上下文
        """
        self.context = context

    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """
        执行分析并返回结构化报告（Python dict）。

        Returns:
            分析报告字典，格式由各子类自行定义
        """
        raise NotImplementedError
