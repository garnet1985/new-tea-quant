#!/usr/bin/env python3
"""Unified enumerator runtime facade for CLI and BFF."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.infra.project_context import PathManager
from core.modules.data_manager import DataManager
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.stock_sampling import StockSamplingHelper
from core.modules.strategy.engines.simulator.enumerator import (
    OpportunityEnumeratorFlow,
    OpportunityEnumeratorSettings,
)
from core.modules.strategy.services.fingerprint.manager import StrategyFingerprintManager
from core.modules.strategy.services.fingerprint.runtime_service import (
    StrategyFingerprintRuntimeService,
)
from core.modules.strategy.strategy_manager import StrategyManager
from core.tables.ui_bff.strategy_workbench_snapshot.model import (
    SysStrategyWorkbenchSnapshotModel,
)
from core.utils.date.date_utils import DateUtils

logger = logging.getLogger(__name__)


@dataclass
class EnumeratorRuntimeContext:
    strategy_name: str
    strategy_info: Any
    settings_view: StrategySettingsView
    enum_settings: OpportunityEnumeratorSettings
    stock_list: List[str]
    start_date: str
    end_date: str
    flow: OpportunityEnumeratorFlow


class EnumeratorRuntimeService:
    """Single owner for canonical enumerate runtime/fingerprint/snapshot orchestration."""

    @staticmethod
    def build_canonical_settings(raw_settings: Dict[str, Any]) -> StrategySettingsView:
        return StrategySettingsView.from_dict(
            StrategyFingerprintManager.canonicalize_settings(raw_settings)
        )

    @classmethod
    def build_context(
        cls,
        *,
        strategy_name: str,
        strategy_info: Any,
        raw_settings_override: Optional[Dict[str, Any]] = None,
        stock_count: Optional[int] = None,
        force_refresh: bool = False,
        workbench_run_id: Optional[str] = None,
        workbench_strategy_name: Optional[str] = None,
    ) -> EnumeratorRuntimeContext:
        raw_settings = raw_settings_override if raw_settings_override is not None else strategy_info.settings.to_dict()
        settings_view = cls.build_canonical_settings(raw_settings)
        enum_settings = OpportunityEnumeratorSettings.from_base(settings_view)
        data_manager = DataManager(is_verbose=False)
        all_stocks = data_manager.service.stock.list.load(filtered=True)
        if enum_settings.use_sampling:
            sampling_amount = stock_count if stock_count is not None else settings_view.sampling_amount
            sampling_config = (
                {"strategy": "continuous", "continuous": {"start_idx": 0}}
                if stock_count is not None
                else settings_view.sampling_config
            )
            stock_list = StockSamplingHelper.get_stock_list(
                all_stocks=all_stocks,
                sampling_amount=sampling_amount,
                sampling_config=sampling_config,
                strategy_name=settings_view.name,
            )
        else:
            stock_list = [s["id"] for s in all_stocks]
        latest_date = data_manager.service.calendar.get_latest_completed_trading_date()
        start_date = settings_view.start_date or DateUtils.DEFAULT_START_DATE
        end_date = settings_view.end_date or latest_date
        flow = OpportunityEnumeratorFlow(
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            max_workers=enum_settings.max_workers,
            base_settings=settings_view,
            force_refresh=bool(force_refresh),
            workbench_strategy_name=workbench_strategy_name,
            workbench_run_id=workbench_run_id,
        )
        return EnumeratorRuntimeContext(
            strategy_name=strategy_name,
            strategy_info=strategy_info,
            settings_view=settings_view,
            enum_settings=enum_settings,
            stock_list=stock_list,
            start_date=start_date,
            end_date=end_date,
            flow=flow,
        )

    @staticmethod
    def run_enum(context: EnumeratorRuntimeContext) -> List[Dict[str, Any]]:
        return context.flow.run(
            strategy_name=context.strategy_name,
            strategy_info=context.strategy_info,
        )

    @staticmethod
    def build_fingerprints(context: EnumeratorRuntimeContext) -> tuple[str, str]:
        return StrategyFingerprintRuntimeService.build_ids_for_runtime_context(context)

    @staticmethod
    def preprocess(context: EnumeratorRuntimeContext) -> Any:
        return context.flow.preprocess(
            strategy_name=context.strategy_name,
            strategy_info=context.strategy_info,
        )

    @staticmethod
    def build_ids_from_preprocessed(preprocessed: Any) -> tuple[str, str]:
        request_fp = getattr(preprocessed, "request_fingerprint", None)
        return StrategyFingerprintRuntimeService.build_ids_from_request_fingerprint(request_fp)

    @classmethod
    def sync_force_refresh_snapshot(
        cls,
        *,
        context: EnumeratorRuntimeContext,
        summary_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        first = (summary_results or [{}])[0] if isinstance(summary_results, list) else {}
        if not isinstance(first, dict):
            first = {}
        version_dir = str(first.get("version_dir") or "").strip()
        if not version_dir:
            raise ValueError("summary missing version_dir")

        output_dir = (
            PathManager.strategy_opportunity_enums(
                strategy_name=context.strategy_name,
                use_sampling=bool(getattr(context.enum_settings, "use_sampling", False)),
            )
            / version_dir
        )
        report_path = output_dir / "0_report_enum.json"
        if not report_path.exists():
            raise FileNotFoundError(str(report_path))
        report_payload = json.loads(report_path.read_text(encoding="utf-8"))
        report_payload = report_payload if isinstance(report_payload, dict) else {}
        enum_metrics = report_payload.get("enumMetrics")

        fp_id, scope_id = cls.build_fingerprints(context)
        model = SysStrategyWorkbenchSnapshotModel()
        matched_rows = model.list_by_strategy_enum_fingerprint(
            context.strategy_name,
            enum_fingerprint_id=fp_id,
            enum_scope_fingerprint_id=scope_id,
            limit=1,
        )
        enum_payload: Dict[str, Any] = {
            "opportunities": int(first.get("opportunities") or 0),
            "totalStocks": int(first.get("totalStocks") or len(context.stock_list)),
            "triggerStocks": int(first.get("triggerStocks") or 0),
            "completedCount": int(first.get("completedCount") or 0),
            "unfinishedCount": int(first.get("unfinishedCount") or 0),
            "completionRate": float(first.get("completionRate") or 0.0),
            "version_dir": version_dir,
        }
        if isinstance(enum_metrics, dict):
            enum_payload["enumMetrics"] = enum_metrics

        result_summary = {
            "enum": enum_payload,
            "enum_meta": {
                "fingerprint_id": fp_id,
                "scope_fingerprint_id": scope_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "source": "enum_runtime_service_force_refresh",
            },
        }
        if matched_rows:
            matched = matched_rows[0] or {}
            matched_version = int(matched.get("version") or 0)
            new_version = matched_version
            if matched_version > 0:
                current_summary = matched.get("result_summary")
                merged_summary = dict(current_summary) if isinstance(current_summary, dict) else {}
                merged_summary["enum"] = result_summary["enum"]
                merged_summary["enum_meta"] = result_summary["enum_meta"]
                model.update_result_summary(
                    context.strategy_name,
                    matched_version,
                    merged_summary,
                    enum_fingerprint_id=fp_id,
                    enum_scope_fingerprint_id=scope_id,
                )
        else:
            created = model.create_version(
                strategy_name=context.strategy_name,
                settings_snapshot=context.settings_view.to_dict(),
                result_summary=result_summary,
                enum_fingerprint_id=fp_id,
                enum_scope_fingerprint_id=scope_id,
            )
            new_version = int((created or {}).get("version") or 0)
        logger.warning(
            "force-refresh snapshot synchronized | strategy=%s mode=%s new_version=%s fp=%s",
            context.strategy_name,
            "update" if matched_rows else "create",
            new_version,
            fp_id,
        )
        return {"cleared": 0, "version": new_version, "fingerprint_id": fp_id}


__all__ = ["EnumeratorRuntimeContext", "EnumeratorRuntimeService"]
