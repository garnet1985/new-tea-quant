"""Adapter 出口协议三层 dataclass。

边界: 协议形状与最小校验；不含 PostProcess 编排、不含可交易局部类型。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple


@dataclass
class Opportunity:
    """标准机会：标的主体 + 触发快照。"""

    id: str
    entity_id: str
    trigger_date: str
    trigger_price: float

    entity_name: str = ""
    entity_exchange: str = ""
    entity_type: str = ""

    trigger_price_raw: float = 0.0
    trigger_price_hfq: float = 0.0

    snapshot: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> Tuple[bool, str]:
        if not str(self.id or "").strip():
            return False, "Opportunity.id 不能为空"
        if not str(self.entity_id or "").strip():
            return False, "Opportunity.entity_id 不能为空"
        if not str(self.trigger_date or "").strip():
            return False, "Opportunity.trigger_date 不能为空"
        try:
            float(self.trigger_price)
        except (TypeError, ValueError):
            return False, "Opportunity.trigger_price 须为数字"
        return True, ""


@dataclass
class StrategyScanReport:
    """标准单策略扫描报告。"""

    strategy_name: str
    scan_date: str
    opportunities: List[Opportunity] = field(default_factory=list)

    strategy_version: str = ""
    goal: Dict[str, Any] = field(default_factory=dict)
    emitted_at: str = ""

    def validate(self) -> Tuple[bool, str]:
        if not str(self.strategy_name or "").strip():
            return False, "StrategyScanReport.strategy_name 不能为空"
        if not str(self.scan_date or "").strip():
            return False, "StrategyScanReport.scan_date 不能为空"
        if not isinstance(self.opportunities, list):
            return False, "StrategyScanReport.opportunities 须为 list"
        if not isinstance(self.goal, dict):
            return False, "StrategyScanReport.goal 须为 dict"
        for i, opp in enumerate(self.opportunities):
            if not isinstance(opp, Opportunity):
                return False, f"StrategyScanReport.opportunities[{i}] 须为 Opportunity"
            ok, err = opp.validate()
            if not ok:
                return False, f"StrategyScanReport.opportunities[{i}]: {err}"
        return True, ""


@dataclass
class ScanSessionReport:
    """标准扫描会话报告（可含多策略）。"""

    scan_date: str
    strategies: List[StrategyScanReport] = field(default_factory=list)
    emitted_at: str = ""

    def validate(self) -> Tuple[bool, str]:
        if not str(self.scan_date or "").strip():
            return False, "ScanSessionReport.scan_date 不能为空"
        if not isinstance(self.strategies, list):
            return False, "ScanSessionReport.strategies 须为 list"
        for i, rep in enumerate(self.strategies):
            if not isinstance(rep, StrategyScanReport):
                return False, f"ScanSessionReport.strategies[{i}] 须为 StrategyScanReport"
            ok, err = rep.validate()
            if not ok:
                return False, f"ScanSessionReport.strategies[{i}]: {err}"
        return True, ""


__all__ = ["Opportunity", "StrategyScanReport", "ScanSessionReport"]
