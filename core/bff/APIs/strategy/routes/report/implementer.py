"""Report implementer: step report / ref / stock detail.

Snapshot rows via launcher ``WorkbenchSnapshots``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.modules.strategy.core.enums import WorkbenchStep


class StrategyReportImplementer:
    def __init__(self) -> None:
        self._DiscoveryService = None
        self._WorkbenchReports = None
        self._WorkbenchStockDetail = None

    def lazy_load(self) -> "StrategyReportImplementer":
        if self._WorkbenchReports is None:
            from core.modules.strategy.core.services.discovery import DiscoveryService

            from core.bff.APIs.strategy.routes.report.step_report import WorkbenchReports
            from core.bff.APIs.strategy.routes.report.stock_detail import (
                WorkbenchStockDetail,
            )

            self._DiscoveryService = DiscoveryService
            self._WorkbenchReports = WorkbenchReports
            self._WorkbenchStockDetail = WorkbenchStockDetail
        return self

    def resolve_strategy_name(self, strategy_key_or_name: str) -> str:
        """``meta.key`` 或 path name → userspace 相对 path（快照 / 产物 API 入参）。"""
        assert self._DiscoveryService is not None
        needle = str(strategy_key_or_name or "").strip()
        if not needle:
            raise ValueError("strategy_key_or_name 不能为空")
        for info in self._DiscoveryService.discover_strategies():
            if info.key == needle or info.id() == needle:
                return str(info.id())
        raise FileNotFoundError(f"策略不存在: {needle!r}")

    @staticmethod
    def normalize_step(step: str) -> Optional[str]:
        parsed = WorkbenchStep.try_parse(step)
        return parsed.value if parsed is not None else None

    @staticmethod
    def parse_version_id(version_id: str) -> Optional[int]:
        text = str(version_id or "").strip()
        if not text:
            return None
        if text.lower().startswith("v"):
            text = text[1:]
        try:
            n = int(text)
            return n if n > 0 else None
        except ValueError:
            return None

    def build_step_report(
        self,
        *,
        strategy_key_or_name: str,
        step: str,
        version_id: str,
    ) -> Dict[str, Any]:
        assert self._WorkbenchReports is not None
        name = self.resolve_strategy_name(strategy_key_or_name)
        norm = WorkbenchStep.parse(step).value
        sid = self.parse_version_id(version_id)
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
        name = self.resolve_strategy_name(strategy_key_or_name)
        norm = WorkbenchStep.parse(step).value
        sid = self.parse_version_id(version_id)
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
        name = self.resolve_strategy_name(strategy_key_or_name)
        norm = WorkbenchStep.parse(step).value
        sid = self.parse_version_id(version_id)
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
