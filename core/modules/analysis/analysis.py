"""Analysis Facade — 回测后 inputs→outputs 归因入口。

本文件:
- Analysis: 对外唯一门面
  边界: 本版本只占位；不读产物、不算归因、不写报告
"""

from __future__ import annotations


class Analysis:
    """回测结果归因门面（骨架）。

    设计未完成前不提供行为方法。调用方仅可 import 本类以确认模块存在。
    """


__all__ = ["Analysis"]
