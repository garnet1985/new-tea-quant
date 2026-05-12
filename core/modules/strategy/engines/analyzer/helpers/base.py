#!/usr/bin/env python3
"""
BaseAnalyzer - 分析器基类
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class AnalysisContext:
    strategy_name: str
    sim_type: str
    sim_version_dir: Path
    raw_settings: Dict[str, Any]
    enum_version_dir: Optional[Path] = None
    data_manager: Optional[Any] = None


class BaseAnalyzer(ABC):
    def __init__(self, context: AnalysisContext) -> None:
        self.context = context

    @abstractmethod
    def run(self) -> Dict[str, Any]:
        raise NotImplementedError


__all__ = ["AnalysisContext", "BaseAnalyzer"]
