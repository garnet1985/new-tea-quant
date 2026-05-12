#!/usr/bin/env python3
"""报告数据类基类。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class ReportBase:
    """所有 report dataclass 的轻量基类。"""

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def safe_div(numerator: float, denominator: float) -> float:
        if denominator == 0:
            return 0.0
        return numerator / denominator

    @classmethod
    def collect(cls, source: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    @classmethod
    def compute(cls, collected: Any, **kwargs: Any) -> "ReportBase":
        raise NotImplementedError

    @classmethod
    def load(cls, source: Any, **kwargs: Any) -> "ReportBase":
        raise NotImplementedError

    def write(self, output_dir: Path, **kwargs: Any) -> None:
        raise NotImplementedError

    @classmethod
    def present(cls, **kwargs: Any) -> None:
        raise NotImplementedError

    def to_console_lines(self) -> List[str]:
        return []
