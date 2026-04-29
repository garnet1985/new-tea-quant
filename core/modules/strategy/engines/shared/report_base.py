#!/usr/bin/env python3
"""报告数据类基类。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List


@dataclass
class ReportBase:
    """所有 report dataclass 的轻量基类。"""

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_console_lines(self) -> List[str]:
        return []
