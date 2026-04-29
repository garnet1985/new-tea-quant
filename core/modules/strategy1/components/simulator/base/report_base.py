#!/usr/bin/env python3
"""
报告数据类基类。

职责：
- 统一 dict 输出（固定模板）
- 统一控制台展示（后端命令行）
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, List


@dataclass
class ReportBase:
    """所有 report dataclass 的轻量基类。"""

    def to_dict(self) -> Dict:
        """导出结构化数据（固定模板）。"""
        return asdict(self)

    def to_console_lines(self) -> List[str]:
        """导出结构化展示文本（后端命令行）。"""
        return []

