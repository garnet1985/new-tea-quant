"""Report implementer: step report / ref / stock detail.

Snapshot rows via BFF ``WorkbenchSnapshots``.
"""

from __future__ import annotations

from typing import Any, Dict

from core.modules.strategy.core.enums import WorkbenchStep
from core.modules.strategy.core.helpers.version_id import WorkbenchVersionId
from core.modules.strategy.core.services.discovery import DiscoveryService


class StrategyReportImplementer:
    def __init__(self) -> None:
        self._WorkbenchReports = None
        self._WorkbenchStockDetail = None

    def lazy_load(self) -> "StrategyReportImplementer":
        if self._WorkbenchReports is None:
            from core.bff.APIs.strategy.routes.report.step_report import WorkbenchReports
            from core.bff.APIs.strategy.routes.report.stock_detail import (
                WorkbenchStockDetail,
            )

            self._WorkbenchReports = WorkbenchReports
            self._WorkbenchStockDetail = WorkbenchStockDetail
        return self

    def build_step_report(
        self,
        *,
        strategy_key_or_name: str,
        step: str,
        version_id: str,
    ) -> Dict[str, Any]:
        assert self._WorkbenchReports is not None
        name = DiscoveryService.resolve_strategy_path(strategy_key_or_name)
        norm = WorkbenchStep.parse(step).value
        sid = WorkbenchVersionId.parse(version_id)
        if sid is None:
            raise ValueError("version_id 无效")
        msg = self._WorkbenchReports.build_step_report(
            strategy_name=name,
            normalized_step=norm,
            version=sid,
        )
        if msg is None:
            raise FileNotFoundError("快照不存在")
        return msg

    def build_step_report_ref(
        self,
        *,
        strategy_key_or_name: str,
        step: str,
        version_id: str,
    ) -> Dict[str, Any]:
        assert self._WorkbenchReports is not None
        name = DiscoveryService.resolve_strategy_path(strategy_key_or_name)
        norm = WorkbenchStep.parse(step).value
        sid = WorkbenchVersionId.parse(version_id)
        if sid is None:
            raise ValueError("version_id 无效")
        msg = self._WorkbenchReports.build_step_report_ref(
            strategy_name=name,
            normalized_step=norm,
            version=sid,
        )
        if msg is None:
            raise FileNotFoundError("快照不存在")
        return msg

    def build_stock_detail(
        self,
        *,
        strategy_key_or_name: str,
        step: str,
        version_id: str,
        stock_id: str,
    ) -> Dict[str, Any]:
        assert self._WorkbenchStockDetail is not None
        name = DiscoveryService.resolve_strategy_path(strategy_key_or_name)
        norm = WorkbenchStep.parse(step).value
        sid = WorkbenchVersionId.parse(version_id)
        if sid is None:
            raise ValueError("version_id 无效")
        code = str(stock_id or "").strip()
        if not code:
            raise ValueError("stock_id 无效")
        msg = self._WorkbenchStockDetail.build(
            strategy_name=name,
            normalized_step=norm,
            version=sid,
            stock_id=code,
        )
        if msg is None:
            raise FileNotFoundError("快照不存在")
        return msg


impl = StrategyReportImplementer()
