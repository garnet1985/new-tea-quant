"""Strategy workbench service logic."""

import copy
import hashlib
import json
import logging
import multiprocessing as mp
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.infra.project_context.config_manager import ConfigManager
from core.infra.project_context.path_manager import PathManager
from core.modules.strategy.services.progress import ProgressRecorder
from core.modules.strategy.services import EnumeratorRuntimeService
from core.modules.strategy.services.cache.simulator_res_db_cache.settings import (
    StrategySettingsService,
)
from core.modules.strategy.services.cache.simulator_res_db_cache.domain.snapshot_service import (
    StrategyWorkbenchSnapshotService,
)
from core.modules.strategy.services.runtime.run_service import StrategyFingerprintRuntimeService
from core.tables.strategy_workbench_snapshot.model import (
    COL_ENV_FP,
    COL_SETTINGS_FP,
    SysStrategyWorkbenchSnapshotModel,
)
from core.ui.bff.shared.file_ops import atomic_write_text, backup_file
from core.ui.bff.shared.response import error, ok
from .cache_helper import StrategyWorkbenchCacheHelper
from .status_helper import StrategyWorkbenchStatusHelper


logger = logging.getLogger(__name__)

class StrategyWorkbenchImplementation(StrategyWorkbenchStatusHelper, StrategyWorkbenchCacheHelper):
    """策略工作台业务服务（不包含 route 绑定）。"""
    STEP_ENUM = "enum"
    STEP_PRICE = "price"
    STEP_CAPITAL = "capital"
    RUN_STATE_QUEUED = "queued"
    RUN_STATE_RUNNING = "running"
    RUN_STATE_DONE = "done"
    RUN_STATE_FAILED = "failed"
    RUN_STATE_CANCELLED = "cancelled"
    STEP_STATUS_IDLE = "idle"
    STEP_STATUS_RUNNING = "running"
    STEP_STATUS_DONE = "done"
    STEP_STATUS_FAILED = "failed"
    STEP_STATUS_CANCELLED = "cancelled"
    _run_lock = threading.Lock()
    _run_cancel_events = {}
    _run_processes = {}
    _snapshot_model = None
    _sample_stocks = [
        ("600519.SH", "贵州茅台"),
        ("000858.SZ", "五粮液"),
        ("601318.SH", "中国平安"),
        ("600036.SH", "招商银行"),
        ("000333.SZ", "美的集团"),
        ("002594.SZ", "比亚迪"),
        ("601012.SH", "隆基绿能"),
        ("300750.SZ", "宁德时代"),
        ("688981.SH", "中芯国际"),
        ("002415.SZ", "海康威视"),
        ("600276.SH", "恒瑞医药"),
        ("601888.SH", "中国中免"),
    ]
    _sampling_strategy_options = (
        ("continuous", "连续采样（默认）"),
        ("uniform", "均匀采样"),
        ("stratified", "分层采样"),
        ("random", "随机采样"),
        ("pool", "指定股票池采样"),
        ("blacklist", "排除黑名单采样"),
    )
    _allocation_mode_options = (
        ("equal_capital", "每个机会均等资金买入"),
        ("equal_shares", "每个机会均等股数买入"),
        ("kelly", "凯莉公式"),
        ("custom", "自定义"),
    )

    # @staticmethod
    # def _now_iso() -> str:
    #     return datetime.now(timezone.utc).isoformat()

    # todo: move to helper
    @staticmethod
    def _resolve_chain(target_step: str, step_status: dict):
        if target_step == StrategyWorkbenchImplementation.STEP_ENUM:
            return [StrategyWorkbenchImplementation.STEP_ENUM]
        if (step_status or {}).get("enum") == StrategyWorkbenchImplementation.STEP_STATUS_DONE:
            return [target_step]
        return [StrategyWorkbenchImplementation.STEP_ENUM, target_step]

    # todo: move to helper
    @staticmethod
    def _mock_step_summary(step: str):
        # BFF 占位：真实枚举应由策略引擎接入后写入 result_report。
        if step == StrategyWorkbenchImplementation.STEP_ENUM:
            return {
                "opportunities": 128,
                "totalStocks": 42,
                "triggerStocks": 36,
                "completedCount": 120,
                "unfinishedCount": 8,
                "completionRate": 93.75,
            }
        if step == StrategyWorkbenchImplementation.STEP_PRICE:
            return {
                "winRate": 0.0,
                "roi": 0.0,
                "avgHoldDays": 0.0,
                "totalInvestments": 0,
                "totalWinInvestments": 0,
                "totalLossInvestments": 0,
                "totalOpenInvestments": 0,
                "stocksWithOpportunities": 0,
                "avgInvestmentsPerStock": 0.0,
                "avgProfitPerInvestment": 0.0,
                "avgProfitPerStock": 0.0,
                "completionRate": 0.0,
            }
        return {
            "initialCapital": 0,
            "endCapital": 0,
            "profit": 0,
            "retPct": 0.0,
            "totalReturn": 0.0,
            "maxDrawdown": 0.0,
            "winRate": 0.0,
            "totalTrades": 0,
            "buyTrades": 0,
            "sellTrades": 0,
            "winTrades": 0,
            "lossTrades": 0,
            "totalProfit": 0.0,
            "avgPnlPerTrade": 0.0,
            "totalOpportunities": 0,
            "completedOpportunities": 0,
            "unfinishedOpportunities": 0,
            "completionRate": 0.0,
        }

    # todo: move to helper
    @staticmethod
    def _parse_report_types(raw):
        valid = {StrategyWorkbenchImplementation.STEP_ENUM, StrategyWorkbenchImplementation.STEP_PRICE, StrategyWorkbenchImplementation.STEP_CAPITAL}
        if raw is None:
            return [StrategyWorkbenchImplementation.STEP_ENUM, StrategyWorkbenchImplementation.STEP_PRICE, StrategyWorkbenchImplementation.STEP_CAPITAL], ""
        parts = [p.strip() for p in str(raw).split(",") if p.strip()]
        if not parts:
            return [StrategyWorkbenchImplementation.STEP_ENUM, StrategyWorkbenchImplementation.STEP_PRICE, StrategyWorkbenchImplementation.STEP_CAPITAL], ""
        invalid = [p for p in parts if p not in valid]
        if invalid:
            return [], f"report_types 包含无效项: {', '.join(invalid)}"
        dedup = []
        for p in parts:
            if p not in dedup:
                dedup.append(p)
        return dedup, ""

    def parse_report_types_query(self, report_types_raw):
        """Returns (requested_types, error_detail). error_detail empty string when ok."""
        return self._parse_report_types(report_types_raw)

    def resolve_result_report_for_strategy_run(
        self, strategy_name: str, status_payload: dict
    ) -> dict:
        return self._resolve_result_report_for_run(strategy_name, status_payload)

    # todo: move to helper
    @staticmethod
    def _build_reports_payload(result_report: dict, requested_types: list):
        result_report = result_report if isinstance(result_report, dict) else {}
        enum_result = result_report.get("enum") if isinstance(result_report.get("enum"), dict) else None
        price_result = result_report.get("price") if isinstance(result_report.get("price"), dict) else None
        capital_result = result_report.get("capital") if isinstance(result_report.get("capital"), dict) else None

        reports = {}
        available_tabs = []
        for report_type in requested_types:
            if report_type == StrategyWorkbenchImplementation.STEP_ENUM:
                # 枚举步骤完成后即应有报告占位（含 opportunities=0），不因「无数」而隐藏 Tab。
                if not isinstance(enum_result, dict):
                    payload = None
                else:
                    enum_metrics = (
                        enum_result.get("enumMetrics")
                        if isinstance(enum_result.get("enumMetrics"), dict)
                        else None
                    )
                    opportunities = int(enum_result.get("opportunities") or 0)
                    payload = {
                        "opportunities": opportunities,
                        "totalStocks": int(enum_result.get("totalStocks") or 0),
                        "triggerStocks": int(enum_result.get("triggerStocks") or 0),
                        "completedCount": int(enum_result.get("completedCount") or 0),
                        "unfinishedCount": int(enum_result.get("unfinishedCount") or 0),
                        "completionRate": float(enum_result.get("completionRate") or 0.0),
                    }
                    if enum_metrics:
                        payload["enumMetrics"] = enum_metrics
            elif report_type == StrategyWorkbenchImplementation.STEP_PRICE:
                if price_result:
                    payload = {
                        "winRate": float(price_result.get("winRate") or 0.0),
                        "roi": float(price_result.get("roi") or 0.0),
                        "avgHoldDays": float(price_result.get("avgHoldDays") or 0.0),
                        "totalInvestments": int(price_result.get("totalInvestments") or 0),
                        "totalWinInvestments": int(price_result.get("totalWinInvestments") or 0),
                        "totalLossInvestments": int(price_result.get("totalLossInvestments") or 0),
                        "totalOpenInvestments": int(price_result.get("totalOpenInvestments") or 0),
                        "stocksWithOpportunities": int(price_result.get("stocksWithOpportunities") or 0),
                        "avgInvestmentsPerStock": float(price_result.get("avgInvestmentsPerStock") or 0.0),
                        "avgProfitPerInvestment": float(price_result.get("avgProfitPerInvestment") or 0.0),
                        "avgProfitPerStock": float(price_result.get("avgProfitPerStock") or 0.0),
                        "completionRate": float(price_result.get("completionRate") or 0.0),
                    }
                else:
                    payload = None
            else:
                if capital_result:
                    total_return = capital_result.get("totalReturn")
                    if total_return is None:
                        total_return = float(capital_result.get("retPct") or 0.0) / 100.0
                    payload = {
                        "totalReturn": float(total_return or 0.0),
                        "maxDrawdown": float(capital_result.get("maxDrawdown") or 0.0),
                        "winRate": float(capital_result.get("winRate") or 0.0),
                        "initialCapital": float(capital_result.get("initialCapital") or 0.0),
                        "finalEquity": float(capital_result.get("finalEquity") or capital_result.get("endCapital") or 0.0),
                        "totalTrades": int(capital_result.get("totalTrades") or 0),
                        "buyTrades": int(capital_result.get("buyTrades") or 0),
                        "sellTrades": int(capital_result.get("sellTrades") or 0),
                        "winTrades": int(capital_result.get("winTrades") or 0),
                        "lossTrades": int(capital_result.get("lossTrades") or 0),
                        "totalProfit": float(capital_result.get("totalProfit") or capital_result.get("profit") or 0.0),
                        "avgPnlPerTrade": float(capital_result.get("avgPnlPerTrade") or 0.0),
                        "totalOpportunities": int(capital_result.get("totalOpportunities") or 0),
                        "completedOpportunities": int(capital_result.get("completedOpportunities") or 0),
                        "unfinishedOpportunities": int(capital_result.get("unfinishedOpportunities") or 0),
                        "completionRate": float(capital_result.get("completionRate") or 0.0),
                    }
                else:
                    payload = None
            reports[report_type] = payload
            if payload is not None:
                available_tabs.append(report_type)
        return reports, available_tabs

    def _build_stock_rows(self, report_type: str, limit: int):
        rows = []
        for idx, (stock_id, stock_name) in enumerate(self._sample_stocks[: max(1, limit)], start=1):
            if report_type == self.STEP_ENUM:
                rows.append({
                    "stock_id": stock_id,
                    "stock_name": stock_name,
                    "opportunities": max(1, 24 - idx * 2),
                    "completion_rate": round(62 + (idx % 5) * 4.2, 1),
                    "completed_count": max(1, 16 - idx),
                    "unfinished_count": max(0, idx - 3),
                    "trigger_span_days": 4 + (idx % 6),
                })
            elif report_type == self.STEP_PRICE:
                rows.append({
                    "stock_id": stock_id,
                    "stock_name": stock_name,
                    "win_rate": round(48 + (idx % 6) * 3.1, 1),
                    "roi": round(-6 + idx * 1.9, 1),
                    "hold_days": 6 + (idx % 8),
                    "completed_count": max(1, 12 - idx),
                    "unfinished_count": max(0, idx - 4),
                })
            else:
                rows.append({
                    "stock_id": stock_id,
                    "stock_name": stock_name,
                    "trade_count": 8 + idx,
                    "pnl": int(-7000 + idx * 2400),
                    "win_rate": round(44 + (idx % 7) * 4.0, 1),
                    "completed_count": max(1, 10 - idx),
                    "unfinished_count": max(0, idx - 5),
                    "completion_rate": round(58 + (idx % 4) * 6.0, 1),
                })
        return rows

    @staticmethod
    def _parse_single_report_type(raw):
        if raw is None:
            return None, ""
        value = str(raw).strip()
        if not value:
            return None, ""
        if value not in {
            StrategyWorkbenchImplementation.STEP_ENUM,
            StrategyWorkbenchImplementation.STEP_PRICE,
            StrategyWorkbenchImplementation.STEP_CAPITAL,
        }:
            return None, f"report_type 必须是 enum | price | capital: {value}"
        return value, ""

    def _resolve_compare_snapshot(
        self, strategy_name: str, compare_version: str
    ) -> Tuple[Optional[dict], str, str]:
        """
        Resolve a snapshot row for report compare.

        ``compare_version`` may be ``latest`` or ``v{n}`` / integer string.
        Returns ``(row, error_detail, resolved_version_id_str)``; ``error_detail`` empty on success.
        """
        raw = str(compare_version or "").strip()
        if not raw:
            return None, "compare_version 不能为空", compare_version
        lowered = raw.lower()
        model = self._get_snapshot_model()
        if lowered == "latest":
            row = self._get_latest_workbench_snapshot_row(strategy_name)
            if not row:
                return None, "对比快照不存在", compare_version
            sid = int(row.get("snapshot_id") or row.get("version") or 0)
            return row, "", self._format_version_id(sid)
        parsed = self._parse_version_id(raw)
        if parsed is None:
            return None, "compare_version 无效", compare_version
        row = model.load_by_strategy_snapshot_id(strategy_name, int(parsed))
        if not row:
            return None, "对比快照不存在", compare_version
        return row, "", self._format_version_id(int(parsed))

    @staticmethod
    def _build_mock_kline(stock_id: str):
        candles = []
        markers = []
        base_price = 100 + (sum(ord(ch) for ch in stock_id) % 37)
        for i in range(20):
            day = i + 1
            drift = (i % 5) - 2
            open_price = round(base_price + i * 0.8 + drift * 0.4, 2)
            close_price = round(open_price + ((i % 3) - 1) * 0.9, 2)
            high_price = round(max(open_price, close_price) + 1.2, 2)
            low_price = round(min(open_price, close_price) - 1.1, 2)
            candles.append({
                "date": f"2026-01-{day:02d}",
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
            })
        if candles:
            markers.append({"type": "buy", "date": candles[4]["date"], "price": candles[4]["close"]})
            markers.append({"type": "sell", "date": candles[13]["date"], "price": candles[13]["close"]})
        return candles, markers

    @classmethod
    def _get_snapshot_model(cls):
        if cls._snapshot_model is None:
            cls._snapshot_model = SysStrategyWorkbenchSnapshotModel()
        return cls._snapshot_model

    @classmethod
    def _get_latest_workbench_snapshot_row(cls, strategy_name: str):
        rows = cls._get_snapshot_model().list_by_strategy(strategy_name, limit=1)
        return rows[0] if rows else None

    @staticmethod
    def _format_version_id(version: int) -> str:
        return StrategyWorkbenchSnapshotService.format_version_id(version)

    @staticmethod
    def _parse_version_id(version_id: str):
        return StrategyWorkbenchSnapshotService.parse_version_id(version_id)

    @staticmethod
    def _to_iso_or_empty(value):
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.astimezone().isoformat()
        return str(value).strip()

    @staticmethod
    def _stable_json_hash(value: Any) -> str:
        try:
            blob = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
        except Exception:
            blob = str(value)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _step_status_from_result_report(self, result_report: Optional[dict]) -> dict:
        rr = result_report if isinstance(result_report, dict) else {}

        def slot_done(key: str) -> str:
            block = rr.get(key)
            return (
                self.STEP_STATUS_DONE
                if isinstance(block, dict) and bool(block)
                else self.STEP_STATUS_IDLE
            )

        return {
            self.STEP_ENUM: slot_done("enum"),
            self.STEP_PRICE: slot_done("price"),
            self.STEP_CAPITAL: slot_done("capital"),
        }

    def _version_detail_from_snapshot_row(self, row: dict) -> dict:
        sid = int(row.get("snapshot_id") or row.get("version") or 0)
        settings_snapshot = row.get("settings_snapshot") if isinstance(row.get("settings_snapshot"), dict) else {}
        normalized_settings = self._canonicalize_api_settings(settings_snapshot)
        result_report = row.get("result_report") if isinstance(row.get("result_report"), dict) else {}
        return {
            "version_id": self._format_version_id(sid),
            "settings": normalized_settings,
            "step_status": self._step_status_from_result_report(result_report),
            "result_report": result_report,
            "created_at": self._to_iso_or_empty(row.get("created_at")),
            "updated_at": self._to_iso_or_empty(row.get("updated_at")),
        }

    @staticmethod
    def _runtime_to_api_settings_fallback(runtime_settings):
        """
        Lightweight fallback when StrategySettings canonicalization fails.

        Returns the same unified shape as runtime_to_api / StrategySettings.to_dict():
        name, description, is_enabled at root only — no nested ``meta`` key.
        Legacy files may still nest meta; those fields are merged onto root and ``meta`` is dropped.
        """
        if not isinstance(runtime_settings, dict):
            return {}
        api_settings = dict(runtime_settings)
        name = api_settings.get("name", "")
        description = api_settings.get("description", "")
        is_enabled = bool(api_settings.get("is_enabled", False))
        existing_meta = api_settings.get("meta")
        if isinstance(existing_meta, dict):
            name = existing_meta.get("name", name)
            description = existing_meta.get("description", description)
            is_enabled = bool(existing_meta.get("is_enabled", is_enabled))
        api_settings["name"] = name
        api_settings["description"] = description
        api_settings["is_enabled"] = is_enabled
        api_settings.pop("meta", None)
        return api_settings

    @staticmethod
    def _format_python_literal(value, level: int = 0) -> str:
        indent_unit = "    "
        current_indent = indent_unit * level
        next_indent = indent_unit * (level + 1)

        if isinstance(value, dict):
            if not value:
                return "{}"
            lines = ["{"]
            items = list(value.items())
            for idx, (k, v) in enumerate(items):
                comma = "," if idx < len(items) - 1 else ""
                rendered = StrategyWorkbenchImplementation._format_python_literal(v, level + 1)
                if "\n" in rendered:
                    lines.append(f"{next_indent}{repr(k)}: {rendered}{comma}")
                else:
                    lines.append(f"{next_indent}{repr(k)}: {rendered}{comma}")
            lines.append(f"{current_indent}}}")
            return "\n".join(lines)

        if isinstance(value, list):
            if not value:
                return "[]"
            lines = ["["]
            for idx, item in enumerate(value):
                comma = "," if idx < len(value) - 1 else ""
                rendered = StrategyWorkbenchImplementation._format_python_literal(item, level + 1)
                if "\n" in rendered:
                    lines.append(f"{next_indent}{rendered}{comma}")
                else:
                    lines.append(f"{next_indent}{rendered}{comma}")
            lines.append(f"{current_indent}]")
            return "\n".join(lines)

        return repr(value)

    def _build_settings_file_text(self, settings_payload: dict, pretty: bool) -> str:
        if pretty:
            formatted = self._format_python_literal(settings_payload)
        else:
            # First pass writes a raw but valid dict literal quickly.
            formatted = repr(settings_payload)
        return (
            "# Auto-generated by Strategy Workbench BFF API.\n"
            "# Manual edits are allowed, but next save may reformat this file.\n\n"
            f"settings = {formatted}\n"
        )

    def _validate_strategy_exists(self, strategy_name: str):
        strategy_dir = PathManager.strategy(strategy_name)
        settings_file = PathManager.strategy_settings(strategy_name)
        if not strategy_dir.exists() or not strategy_dir.is_dir() or not settings_file.exists():
            return False
        return True

    def _normalize_runtime_settings(self, strategy_name: str, settings: dict):
        return StrategySettingsService.normalize_runtime_settings(
            strategy_name=strategy_name,
            api_settings=settings,
        )

    def _save_runtime_settings_file(self, strategy_name: str, normalized_runtime_settings: dict):
        settings_file = PathManager.strategy_settings(strategy_name)
        backup_file(settings_file)
        raw_output = self._build_settings_file_text(normalized_runtime_settings, pretty=False)
        atomic_write_text(settings_file, raw_output)
        pretty_output = self._build_settings_file_text(normalized_runtime_settings, pretty=True)
        atomic_write_text(settings_file, pretty_output)

    def _fetch_api_settings_for_run(self, strategy_name: str, run_id: Optional[str] = None):
        """
        供枚举等运行时加载 settings（API 形状）。

        规则（避免 UI 只写 DB、磁盘 settings.py 未同步导致指纹永远对齐物理文件）：
        - 只要 sys_strategy_workbench_snapshot 里已有该策略的快照行：只用「最新版本」DB 快照，
          **绝不**回退到 userspace/settings.py。
        - 仅当从未有任何工作台快照时，才读磁盘 settings.py。
        """
        strategy_dir = PathManager.strategy(strategy_name)
        settings_file = PathManager.strategy_settings(strategy_name)
        if not strategy_dir.exists() or not strategy_dir.is_dir() or not settings_file.exists():
            return None

        if run_id:
            status_payload = self._read_status(strategy_name) or {}
            if str(status_payload.get("run_id") or "") == str(run_id):
                run_snap = self._coerce_db_settings_snapshot(
                    status_payload.get("run_settings_snapshot")
                )
                if run_snap:
                    return self._canonicalize_api_settings(run_snap)

        model = self._get_snapshot_model()
        rows = model.list_by_strategy(strategy_name, limit=1)

        if rows:
            row = rows[0]
            snap = self._coerce_db_settings_snapshot(row.get("settings_snapshot"))
            v = int(row.get("snapshot_id") or row.get("version") or 0)
            if snap:
                return self._canonicalize_api_settings(snap)
            logger.error(
                "Workbench enum: 存在快照行但 settings_snapshot 无效或为空 | strategy=%s snapshot_id=%s "
                "（不会回退 userspace/settings.py；请在工作台重新保存配置）",
                strategy_name,
                v,
            )
            return None

        runtime_settings = ConfigManager.load_python(settings_file, var_name="settings")
        if not isinstance(runtime_settings, dict):
            return None
        api = self._runtime_to_api_settings(runtime_settings)
        return api

    def _load_api_settings_for_workbench_enumerator(
        self, strategy_name: str, run_id: Optional[str]
    ) -> Tuple[Optional[dict], Optional[str]]:
        raw_api = self._fetch_api_settings_for_run(strategy_name, run_id=run_id)
        if not raw_api:
            return None, "无法读取策略配置（目录或 settings 缺失）"
        return raw_api, None

    def _normalize_api_settings_for_workbench_enumerator(
        self, strategy_name: str, raw_api: dict
    ) -> Tuple[Optional[dict], Optional[str]]:
        normalized_runtime_settings, detail = self._normalize_runtime_settings(
            strategy_name,
            raw_api,
        )
        if normalized_runtime_settings is None:
            return None, detail or "settings 校验失败"
        return normalized_runtime_settings, None

    @staticmethod
    def _validate_strategy_settings_report_usable(normalized_runtime_settings: dict) -> Optional[str]:
        from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
            StrategySettings,
        )

        validated = StrategySettings(raw_settings=dict(normalized_runtime_settings))
        report = validated.validate()
        if not report.is_usable():
            return "settings 校验失败"
        return None

    def _load_strategy_info_for_workbench_enumerator(
        self, strategy_name: str
    ) -> Tuple[Any, Optional[str]]:
        from core.modules.strategy.strategy_manager import StrategyManager

        strategy_manager = StrategyManager(is_verbose=False)
        strategy_info = strategy_manager.get_strategy_info(strategy_name)
        if strategy_info is None:
            return None, f"策略未被发现或无法加载: {strategy_name}"
        return strategy_info, None

    def _build_opportunity_enumerator_runtime_context(
        self,
        *,
        strategy_name: str,
        strategy_info: Any,
        normalized_runtime_settings: dict,
        run_id: Optional[str],
        force_refresh: bool = False,
    ):
        return EnumeratorRuntimeService.build_context(
            strategy_name=strategy_name,
            strategy_info=strategy_info,
            raw_settings_override=normalized_runtime_settings,
            stock_count=None,
            workbench_strategy_name=strategy_name if run_id else None,
            workbench_run_id=str(run_id) if run_id else None,
            force_refresh=force_refresh,
        )

    def _build_workbench_opportunity_enumerator_flow(
        self,
        strategy_name: str,
        run_id: Optional[str],
        force_refresh: bool = False,
    ) -> Tuple[Any, Any, Optional[str]]:
        """
        构造与真实工作台枚举一致的 OpportunityEnumeratorFlow。
        run_id 为空时不绑定进度文件。
        返回 (flow, strategy_info, error_message)。
        """
        # Step 1: load API-shaped settings (snapshot / run snapshot / userspace).
        raw_api, err = self._load_api_settings_for_workbench_enumerator(strategy_name, run_id)
        if err:
            return None, None, err

        # Step 2: normalize to runtime settings dict.
        normalized_runtime_settings, err = self._normalize_api_settings_for_workbench_enumerator(
            strategy_name, raw_api
        )
        if err:
            return None, None, err

        # Step 3: StrategySettings.validate() usability gate.
        err = self._validate_strategy_settings_report_usable(normalized_runtime_settings)
        if err:
            return None, None, err

        # Step 4: resolve StrategyManager strategy_info.
        strategy_info, err = self._load_strategy_info_for_workbench_enumerator(strategy_name)
        if err:
            return None, None, err

        # Step 5: build flow via EnumeratorRuntimeService.build_context.
        context = self._build_opportunity_enumerator_runtime_context(
            strategy_name=strategy_name,
            strategy_info=strategy_info,
            normalized_runtime_settings=normalized_runtime_settings,
            run_id=run_id,
            force_refresh=force_refresh,
        )
        return context.flow, strategy_info, None

    def _enumerator_fingerprint_for_row_snapshot(
        self,
        strategy_name: str,
        flow_ref: Any,
        strategy_info: Any,
        api_snapshot: dict,
    ) -> Any:
        """
        与 opportunity_enumerator_flow.preprocess 中指纹构造一致：`settings_core` 均经
        StrategySettings 校验/默认补足 + simulator_res_db_cache 语义核剔除（见 build_request_fingerprint）。
        返回 StrategyRunFingerprint，供完整 id 与 scope id 匹配。
        """
        normalized, _ = self._normalize_runtime_settings(strategy_name, api_snapshot)
        if normalized is None:
            return None
        canonical_payload = EnumeratorRuntimeService.build_canonical_settings(normalized).to_dict()
        return StrategyFingerprintRuntimeService.build_fingerprint_for_snapshot_candidate(
            flow_ref=flow_ref,
            strategy_name=strategy_name,
            strategy_info=strategy_info,
            canonical_settings_payload=canonical_payload,
            stock_ids=flow_ref.stock_list,
        )

    def _workbench_enum_preprocess(
        self,
        strategy_name: str,
        run_id: Optional[str],
    ):
        """
        与工作台枚举 run 一致的 preprocess（指纹等）。
        返回 (preprocessed, error_message)；成功时 error_message 为 None。
        """
        flow, strategy_info, err = self._build_workbench_opportunity_enumerator_flow(
            strategy_name, run_id
        )
        if err:
            return None, err
        preprocessed = flow.preprocess(
            strategy_name=strategy_name, strategy_info=strategy_info
        )
        return preprocessed, None

    def _execute_opportunity_enumeration(
        self,
        strategy_name: str,
        run_id: str,
        *,
        force_refresh: bool = False,
    ):
        """
        调用 OpportunityEnumeratorFlow.run（DB 缓存与快照写入在 Flow 内完成）。
        返回 (summary_payload, error_message)；成功时 error_message 为 None。
        """
        try:
            flow, strategy_info, err = self._build_workbench_opportunity_enumerator_flow(
                strategy_name,
                run_id,
                force_refresh=force_refresh,
            )
            if err:
                return None, err

            summary_results = flow.run(
                strategy_name=strategy_name,
                strategy_info=strategy_info,
            )
            if not summary_results or not isinstance(summary_results, list):
                return None, "枚举完成但未返回摘要"
            first = summary_results[0]
            if not isinstance(first, dict):
                return None, "枚举摘要格式无效"
            payload = self._enum_summary_row_to_bff_payload(first)
            enum_report = self._load_enum_report_from_output(strategy_name, payload)
            if enum_report:
                payload.update(enum_report)
            return payload, None
        except Exception as exc:
            logger.exception(
                "策略工作台枚举失败: strategy_name=%s",
                strategy_name,
            )
            return None, str(exc)

    def build_enumerator_reuse_preview_flow(self, strategy_name: str):
        """
        Build OpportunityEnumeratorFlow for reuse preview (no subprocess run).
        Returns (flow, strategy_info, err_message). err_message is set when flow cannot be built.
        """
        return self._build_workbench_opportunity_enumerator_flow(strategy_name, None)

    @staticmethod
    def preprocess_enumerator_reuse_preview(flow, strategy_name: str, strategy_info):
        """Run preprocess（指纹等）。"""
        return flow.preprocess(strategy_name=strategy_name, strategy_info=strategy_info)

    def assemble_enumerator_reuse_preview_payload(self, strategy_name: str, flow, preprocessed):
        """指纹 ID（完整 + scope），供前端展示。"""
        req_fp = preprocessed.request_fingerprint
        fp_id = str(req_fp.fingerprint_id) if req_fp else ""
        scope_id = ""
        if req_fp:
            _, scope_id = StrategyFingerprintRuntimeService.build_ids_from_request_fingerprint(
                req_fp
            )
        return {
            "fingerprint_id": fp_id,
            "scope_fingerprint_id": scope_id or "",
        }

    def _fail_run_step(
        self,
        strategy_name: str,
        run_id: str,
        failed_step: str,
        message: str,
    ) -> None:
        status_payload = self._read_status(strategy_name) or {}
        if str(status_payload.get("run_id") or "") != run_id:
            return
        step_status = (
            status_payload.get("step_status")
            if isinstance(status_payload.get("step_status"), dict)
            else {}
        )
        step_status = dict(step_status)
        step_status[failed_step] = self.STEP_STATUS_FAILED
        status_payload.update({
            "state": self.RUN_STATE_FAILED,
            "step_status": step_status,
            "running_step": "",
            "progress_pct": 0,
            "error_detail": message,
            "updated_at": datetime.now().astimezone().isoformat(),
        })
        self._write_status(strategy_name, status_payload)

    def _run_chain_worker(
        self,
        strategy_name: str,
        run_id: str,
        resolved_chain: list,
        cancel_event,
    ) -> None:
        if cancel_event is None:
            return

        for step in resolved_chain:
            status_payload = self._read_status(strategy_name) or {}
            if str(status_payload.get("run_id") or "") != run_id:
                return

            if cancel_event.is_set():
                step_status = status_payload.get("step_status") or {}
                if isinstance(step_status, dict) and step in step_status:
                    step_status[step] = self.STEP_STATUS_CANCELLED
                status_payload.update({
                    "state": self.RUN_STATE_CANCELLED,
                    "step_status": step_status,
                    "updated_at": datetime.now().astimezone().isoformat(),
                })
                self._write_status(strategy_name, status_payload)
                return

            step_status = status_payload.get("step_status") or {}
            if isinstance(step_status, dict):
                step_status[step] = self.STEP_STATUS_RUNNING

            status_payload.update({
                "state": self.RUN_STATE_RUNNING,
                "running_step": step,
                "progress_pct": 0,
                "step_status": step_status,
                "updated_at": datetime.now().astimezone().isoformat(),
            })
            self._write_status(strategy_name, status_payload)

            if step == self.STEP_ENUM:
                if cancel_event.is_set():
                    step_status = status_payload.get("step_status") or {}
                    if isinstance(step_status, dict):
                        step_status[step] = self.STEP_STATUS_CANCELLED
                    status_payload.update({
                        "state": self.RUN_STATE_CANCELLED,
                        "step_status": step_status,
                        "running_step": "",
                        "updated_at": datetime.now().astimezone().isoformat(),
                    })
                    self._write_status(strategy_name, status_payload)
                    return

                try:
                    status_for_enum = self._read_status(strategy_name) or {}
                    force_run = bool(status_for_enum.get("is_force"))
                    enum_payload, enum_err = self._execute_opportunity_enumeration(
                        strategy_name,
                        run_id,
                        force_refresh=force_run,
                    )

                    status_payload = self._read_status(strategy_name) or {}
                    if str(status_payload.get("run_id") or "") != run_id:
                        return
                    if enum_err:
                        self._fail_run_step(strategy_name, run_id, step, enum_err)
                        return
                    if cancel_event.is_set():
                        step_status = status_payload.get("step_status") or {}
                        if isinstance(step_status, dict):
                            step_status[step] = self.STEP_STATUS_CANCELLED
                        status_payload.update({
                            "state": self.RUN_STATE_CANCELLED,
                            "step_status": step_status,
                            "running_step": "",
                            "updated_at": datetime.now().astimezone().isoformat(),
                        })
                        self._write_status(strategy_name, status_payload)
                        return

                    step_status = status_payload.get("step_status") or {}
                    if isinstance(step_status, dict):
                        step_status[step] = self.STEP_STATUS_DONE
                    result = status_payload.get("result_report")
                    if not isinstance(result, dict):
                        result = {}
                    result[step] = enum_payload
                    status_payload["step_status"] = step_status
                    status_payload["result_report"] = result
                    status_payload["progress_pct"] = 100
                    status_payload["running_step"] = step
                    status_payload["updated_at"] = datetime.now().astimezone().isoformat()
                    self._write_status(strategy_name, status_payload)
                    continue
                finally:
                    try:
                        ProgressRecorder.for_strategy_run_step(
                            strategy_name, run_id, self.STEP_ENUM
                        ).reset()
                    except Exception:
                        pass

            for pct in (20, 40, 60, 80, 100):
                if cancel_event.is_set():
                    break
                current = self._read_status(strategy_name) or {}
                if str(current.get("run_id") or "") != run_id:
                    return
                current["progress_pct"] = pct
                current["updated_at"] = datetime.now().astimezone().isoformat()
                self._write_status(strategy_name, current)
                time.sleep(0.25)

            status_payload = self._read_status(strategy_name) or {}
            if str(status_payload.get("run_id") or "") != run_id:
                return
            step_status = status_payload.get("step_status") or {}
            if isinstance(step_status, dict):
                step_status[step] = (
                    self.STEP_STATUS_CANCELLED if cancel_event.is_set() else self.STEP_STATUS_DONE
                )
            status_payload["step_status"] = step_status
            status_payload["updated_at"] = datetime.now().astimezone().isoformat()

            if cancel_event.is_set():
                status_payload["state"] = self.RUN_STATE_CANCELLED
                self._write_status(strategy_name, status_payload)
                return

            result = status_payload.get("result_report")
            if not isinstance(result, dict):
                result = {}
            result[step] = self._mock_step_summary(step)
            status_payload["result_report"] = result
            self._write_status(strategy_name, status_payload)

        final_payload = self._read_status(strategy_name) or {}
        if str(final_payload.get("run_id") or "") == run_id:
            final_payload["state"] = self.RUN_STATE_DONE
            final_payload["running_step"] = ""
            final_payload["progress_pct"] = 100
            final_payload["updated_at"] = datetime.now().astimezone().isoformat()
            self._write_status(strategy_name, final_payload)

    def get_strategies(self):
        try:
            from core.modules.strategy.services.discovery import StrategyDiscoveryHelper

            strategies = []
            discovered = StrategyDiscoveryHelper.discover_strategies()
            for _name, info in (discovered or {}).items():
                meta = getattr(info.settings, "meta", None)
                strategies.append({
                    "key": str(info.folder.name),
                    "name": str(getattr(meta, "name", info.name)),
                    "description": str(getattr(meta, "description", "") or ""),
                    "is_enabled": bool(getattr(meta, "is_enabled", False)),
                })

            strategies.sort(key=lambda x: x.get("key", ""))
            return ok({"strategies": strategies})
        except Exception as e:
            return error(f"获取策略列表失败: {str(e)}", 500)

    def get_strategy_settings_options_allocation_modes(self):
        try:
            # 该 API 仅返回前端下拉选项，不依赖 capital_allocation settings 导入链，避免循环导入。
            options = [
                {"value": value, "label": label}
                for value, label in self._allocation_mode_options
            ]

            profiles = {
                "equal_capital": {
                    "configurable_fields": [
                        "allocation.max_portfolio_size",
                        "allocation.max_weight_per_stock",
                    ],
                    "required_fields": [],
                },
                "equal_shares": {
                    "configurable_fields": [
                        "allocation.max_portfolio_size",
                        "allocation.max_weight_per_stock",
                        "allocation.lot_size",
                        "allocation.lots_per_trade",
                    ],
                    "required_fields": ["allocation.lot_size", "allocation.lots_per_trade"],
                },
                "kelly": {
                    "configurable_fields": [
                        "allocation.max_portfolio_size",
                        "allocation.max_weight_per_stock",
                        "allocation.kelly_fraction",
                    ],
                    "required_fields": ["allocation.kelly_fraction"],
                },
                "custom": {
                    "configurable_fields": [
                        "allocation.max_portfolio_size",
                        "allocation.max_weight_per_stock",
                    ],
                    "required_fields": [],
                },
            }
            return ok({"options": options, "profiles": profiles})
        except Exception as e:
            return error(f"获取资金分配选项失败: {str(e)}", 500)

    def get_strategy_settings_options_sampling_strategies(self):
        try:
            # 该 API 仅返回前端下拉选项，不依赖 settings 模块导入链，避免运行时循环导入死锁。
            options = [
                {"value": value, "label": label}
                for value, label in self._sampling_strategy_options
            ]

            profiles = {
                "continuous": {
                    "configurable_fields": ["sampling.sampling_amount", "sampling.continuous.start_idx"],
                    "required_fields": [],
                },
                "uniform": {
                    "configurable_fields": ["sampling.sampling_amount"],
                    "required_fields": [],
                },
                "stratified": {
                    "configurable_fields": ["sampling.sampling_amount", "sampling.stratified.seed"],
                    "required_fields": [],
                },
                "random": {
                    "configurable_fields": ["sampling.sampling_amount", "sampling.random.seed"],
                    "required_fields": [],
                },
                "pool": {
                    "configurable_fields": [
                        "sampling.sampling_amount",
                        "sampling.pool.stock_ids",
                        "sampling.pool.file",
                    ],
                    "required_fields": [],
                },
                "blacklist": {
                    "configurable_fields": [
                        "sampling.sampling_amount",
                        "sampling.blacklist.stock_ids",
                        "sampling.blacklist.file",
                    ],
                    "required_fields": [],
                },
            }
            return ok({"options": options, "profiles": profiles})
        except Exception as e:
            return error(f"获取采样策略选项失败: {str(e)}", 500)

    def _runtime_to_api_settings(self, runtime_settings):
        """
        Canonicalize runtime settings via StrategySettings dataclass.
        API shape equals validated runtime shape (single source of truth).
        """
        if not isinstance(runtime_settings, dict):
            return {}
        try:
            return StrategySettingsService.runtime_to_api(runtime_settings)
        except Exception:
            logger.exception(
                "runtime->api settings canonicalization failed; fallback formatter used"
            )
            return self._runtime_to_api_settings_fallback(runtime_settings)

    def _api_to_runtime_settings(self, api_settings):
        return StrategySettingsService.api_to_runtime(api_settings)

    def _canonicalize_api_settings(self, api_settings):
        """
        Normalize any API settings payload to canonical validated shape using StrategySettings.
        """
        return StrategySettingsService.canonicalize_api_settings(api_settings)

    def load_latest_settings_snapshot(self, strategy_name: str):
        """Latest DB row as ``{ "settings": dict, "version_id": "v{n}" }``, or ``None``."""
        row = self._get_latest_workbench_snapshot_row(strategy_name)
        if not row:
            return None
        settings_snap = row.get("settings_snapshot") if isinstance(row.get("settings_snapshot"), dict) else {}
        sid = int(row.get("snapshot_id") or row.get("version") or 0)
        return {
            "settings": settings_snap,
            "version_id": self._format_version_id(sid),
        }

    def get_strategy_settings(self, strategy_name: str):
        try:
            # Step 1: resolve strategy/settings file paths.
            strategy_dir = PathManager.strategy(strategy_name)
            settings_file = PathManager.strategy_settings(strategy_name)

            # Step 2: validate strategy directory exists.
            if not strategy_dir.exists() or not strategy_dir.is_dir():
                return error(f"策略不存在: {strategy_name}", 404)

            # Step 3: validate settings.py exists.
            if not settings_file.exists():
                return error(f"策略缺少 settings.py: {strategy_name}", 404)

            # Step 4: try latest workbench snapshot first.
            latest_row = self._get_latest_workbench_snapshot_row(strategy_name)
            if latest_row:
                snapshot_settings = latest_row.get("settings_snapshot")
                normalized_snapshot_settings = self._canonicalize_api_settings(snapshot_settings or {})
                sid = int(latest_row.get("snapshot_id") or latest_row.get("version") or 0)
                return ok({
                    "strategy_name": strategy_name,
                    "settings": normalized_snapshot_settings,
                    "settings_source": "workbench_snapshot",
                    "workbench_version_id": self._format_version_id(sid),
                })

            # Step 5: fallback to userspace settings.py when snapshot is absent.
            runtime_settings = ConfigManager.load_python(settings_file, var_name="settings")
            if not isinstance(runtime_settings, dict):
                return error(f"策略 settings 无效: {strategy_name}", 500)

            # Step 6: normalize runtime settings to API shape and return.
            api_settings = self._runtime_to_api_settings(runtime_settings)
            return ok({
                "strategy_name": strategy_name,
                "settings": api_settings,
                "settings_source": "userspace",
                "workbench_version_id": "",
            })
        except Exception as e:
            return error(f"读取策略 settings 失败: {str(e)}", 500)

    def apply_strategy_settings_to_userspace(self, strategy_name: str, payload: dict):
        """Write validated settings to userspace strategy settings.py (explicit deploy only)."""
        try:
            if not isinstance(payload, dict):
                return error("请求体必须为对象", 400)
            settings = payload.get("settings")
            if not self._validate_strategy_exists(strategy_name):
                return error(f"策略不存在: {strategy_name}", 404)

            normalized_runtime_settings, detail = self._normalize_runtime_settings(strategy_name, settings)
            if normalized_runtime_settings is None:
                return error(detail, 422)

            self._save_runtime_settings_file(strategy_name, normalized_runtime_settings)

            return ok({
                "strategy_name": strategy_name,
                "applied": True,
            })
        except Exception as e:
            return error(f"应用 settings 到策略目录失败: {str(e)}", 500)

    def start_strategy_run(self, strategy_name: str, payload: dict):
        try:
            body = payload if isinstance(payload, dict) else {}
            target_step = str(body.get("target_step") or "").strip()
            if target_step not in {self.STEP_ENUM, self.STEP_PRICE, self.STEP_CAPITAL}:
                return error("target_step 必须是 enum | price | capital", 400)

            strategy_dir = PathManager.strategy(strategy_name)
            settings_file = PathManager.strategy_settings(strategy_name)
            if not strategy_dir.exists() or not strategy_dir.is_dir() or not settings_file.exists():
                return error(f"策略不存在: {strategy_name}", 404)

            current = self._read_status(strategy_name) or {}
            current_state = str(current.get("state") or "")
            if current_state in {self.RUN_STATE_QUEUED, self.RUN_STATE_RUNNING}:
                return error("当前策略已有执行任务在运行中", 409)

            previous_step_status = current.get("step_status") if isinstance(current.get("step_status"), dict) else {}
            step_status = {
                self.STEP_ENUM: previous_step_status.get(self.STEP_ENUM, self.STEP_STATUS_IDLE),
                self.STEP_PRICE: previous_step_status.get(self.STEP_PRICE, self.STEP_STATUS_IDLE),
                self.STEP_CAPITAL: previous_step_status.get(self.STEP_CAPITAL, self.STEP_STATUS_IDLE),
            }
            resolved_chain = self._resolve_chain(target_step, step_status)

            if resolved_chain[0] == self.STEP_ENUM:
                step_status[self.STEP_ENUM] = self.STEP_STATUS_RUNNING
                if target_step != self.STEP_ENUM:
                    step_status[self.STEP_PRICE] = self.STEP_STATUS_IDLE
                    step_status[self.STEP_CAPITAL] = self.STEP_STATUS_IDLE
            elif resolved_chain[0] == self.STEP_PRICE:
                step_status[self.STEP_ENUM] = self.STEP_STATUS_DONE
                step_status[self.STEP_PRICE] = self.STEP_STATUS_RUNNING
            else:
                step_status[self.STEP_CAPITAL] = self.STEP_STATUS_RUNNING

            run_id = self._build_run_id()
            run_api_settings = None
            if "settings" in body:
                normalized_runtime_settings, detail = self._normalize_runtime_settings(
                    strategy_name,
                    body.get("settings"),
                )
                if normalized_runtime_settings is None:
                    return error(detail or "settings 校验失败", 422)
                run_api_settings = self._runtime_to_api_settings(normalized_runtime_settings)
            row = self._get_latest_workbench_snapshot_row(strategy_name)
            wb_snapshot_v = int(row.get("snapshot_id") or row.get("version") or 0) if row else 0
            if run_api_settings is not None:
                # For run-scoped settings, only persist to DB on successful enum completion.
                wb_snapshot_v = 0
            is_force = bool(body.get("is_force") or body.get("force_refresh"))
            workbench_version_id = str(body.get("workbench_version_id") or "").strip()
            status_payload = {
                "run_id": run_id,
                "strategy_name": strategy_name,
                "state": self.RUN_STATE_RUNNING,
                "target_step": target_step,
                "resolved_chain": resolved_chain,
                "running_step": resolved_chain[0],
                "progress_pct": 0,
                "step_status": step_status,
                "result_report": {},
                "workbench_snapshot_version": wb_snapshot_v,
                "run_settings_snapshot": run_api_settings,
                "is_force": is_force,
                "workbench_version_id": workbench_version_id,
                "updated_at": datetime.now().astimezone().isoformat(),
            }
            self._write_status(strategy_name, status_payload)

            cancel_ev = mp.Event()
            with self._run_lock:
                self._run_cancel_events[run_id] = cancel_ev
                # daemon processes cannot spawn worker processes (enumerator uses ProcessPoolExecutor).
                proc = mp.Process(
                    target=_strategy_workbench_run_chain_entry,
                    args=(strategy_name, run_id, resolved_chain, cancel_ev),
                    daemon=False,
                    name=f"swb_run_{run_id}",
                )
                proc.start()
                self._run_processes[run_id] = proc

            return ok({
                "run_id": run_id,
                "strategy_name": strategy_name,
                "state": self.RUN_STATE_RUNNING,
                "target_step": target_step,
                "resolved_chain": resolved_chain,
            })
        except Exception as e:
            return error(f"启动执行任务失败: {str(e)}", 500)

    def normalize_run_status_step_status(self, status_payload: dict) -> dict:
        step_status = status_payload.get("step_status")
        if not isinstance(step_status, dict):
            return {
                self.STEP_ENUM: self.STEP_STATUS_IDLE,
                self.STEP_PRICE: self.STEP_STATUS_IDLE,
                self.STEP_CAPITAL: self.STEP_STATUS_IDLE,
            }
        return step_status

    def build_run_status_response_body(
        self, run_id: str, status_payload: dict, step_status: dict
    ) -> dict:
        progress_pct = int(status_payload.get("progress_pct") or 0)
        return {
            "run_id": run_id,
            "state": status_payload.get("state", self.RUN_STATE_RUNNING),
            "running_step": status_payload.get("running_step", ""),
            "progress_pct": progress_pct,
            "step_status": step_status,
            "result_report": status_payload.get("result_report") or {},
            "is_force": bool(status_payload.get("is_force")),
            "workbench_version_id": str(status_payload.get("workbench_version_id") or ""),
            "updated_at": status_payload.get(
                "updated_at", datetime.now().astimezone().isoformat()
            ),
        }

    def merge_enumerator_progress_into_run_status(
        self,
        strategy_name: str,
        run_id: str,
        status_payload: dict,
        out: dict,
    ) -> None:
        if str(status_payload.get("running_step") or "") != self.STEP_ENUM:
            return
        base_pct = int(out.get("progress_pct") or 0)
        ep = ProgressRecorder.for_strategy_run_step(
            strategy_name, run_id, self.STEP_ENUM
        ).get_progress()
        if ep:
            out["progress_pct"] = int(ep.get("progress_pct") or base_pct)
            out["enumerator_progress"] = ep

    def finalize_run_worker_handles_if_terminal(
        self, strategy_name: str, run_id: str, status_payload: dict
    ) -> None:
        state = str(status_payload.get("state") or "")
        if state not in {
            self.RUN_STATE_DONE,
            self.RUN_STATE_FAILED,
            self.RUN_STATE_CANCELLED,
        }:
            return
        with self._run_lock:
            self._run_cancel_events.pop(str(run_id), None)
            proc = self._run_processes.pop(str(run_id), None)
        if proc is not None:
            proc.join(timeout=1.0)

    @staticmethod
    def normalize_run_result_report_from_status(status_payload: dict) -> dict:
        """`result_report` from run status file; empty dict if missing/invalid."""
        result_report = status_payload.get("result_report")
        return result_report if isinstance(result_report, dict) else {}

    @staticmethod
    def build_strategy_run_results_payload(run_id: str, result_report: dict) -> dict:
        """Execution panel: per-step summary slots (enum / price / capital) from status."""
        return {
            "run_id": run_id,
            "result": {
                "enum": result_report.get("enum"),
                "price": result_report.get("price"),
                "capital": result_report.get("capital"),
            },
        }

    def resolve_workbench_version_history_ids(self, strategy_name: str) -> list:
        """
        Synthetic ``latest`` plus persisted snapshot version ids, stable order, deduped.
        Caller must ensure strategy exists (e.g. route + ensure_strategy_exists).
        """
        versions = ["latest"]
        rows = self._get_snapshot_model().list_by_strategy(strategy_name, limit=100)
        for row in rows:
            sid = int(row.get("snapshot_id") or row.get("version") or 0)
            if sid > 0:
                versions.append(self._format_version_id(sid))
        deduped = []
        seen = set()
        for item in versions:
            if item in seen:
                continue
            seen.add(item)
            deduped.append(item)
        return deduped

    def _resolve_result_report_for_run(self, strategy_name: str, status_payload: dict) -> dict:
        result_report = (
            status_payload.get("result_report")
            if isinstance(status_payload.get("result_report"), dict)
            else {}
        )
        wb_snapshot_v = int(
            status_payload.get("workbench_snapshot_version")
            or status_payload.get("workbench_snapshot_no")
            or 0
        )
        if wb_snapshot_v > 0:
            row = SysStrategyWorkbenchSnapshotModel().load_by_strategy_snapshot_id(
                strategy_name, wb_snapshot_v
            )
            snap_report = row.get("result_report") if row else None
            if isinstance(snap_report, dict) and isinstance(snap_report.get("enum"), dict):
                result_report = dict(result_report or {})
                result_report["enum"] = snap_report.get("enum")
        enum_in_result = result_report.get("enum") if isinstance(result_report, dict) else None
        enum_needs_backfill = not isinstance(enum_in_result, dict) or not isinstance(
            enum_in_result.get("enumMetrics"), dict
        )
        if enum_needs_backfill:
            rows = SysStrategyWorkbenchSnapshotModel().list_by_strategy(strategy_name, limit=1)
            latest_report = (rows[0].get("result_report") if rows else None) or {}
            if isinstance(latest_report, dict) and isinstance(latest_report.get("enum"), dict):
                result_report = dict(result_report or {})
                result_report["enum"] = latest_report.get("enum")
        return result_report

    def assemble_strategy_reports_message(
        self,
        strategy_name: str,
        run_id: str,
        result_report: dict,
        requested_types: list,
    ) -> dict:
        """Build SWB-11 message body: tab payloads + optional enumMetrics backfill from disk."""
        reports, available_tabs = self._build_reports_payload(result_report, requested_types)
        enum_payload = reports.get(self.STEP_ENUM) if isinstance(reports.get(self.STEP_ENUM), dict) else None
        if enum_payload and not isinstance(enum_payload.get("enumMetrics"), dict):
            enum_report = self._load_enum_report_from_output(strategy_name, enum_payload)
            enum_metrics = enum_report.get("enumMetrics") if isinstance(enum_report.get("enumMetrics"), dict) else None
            if enum_metrics:
                enum_payload["enumMetrics"] = enum_metrics
        return {
            "run_id": run_id,
            "reports": reports,
            "available_tabs": available_tabs,
        }

    def get_strategy_report_stocks(
        self,
        strategy_name: str,
        run_id: str,
        report_type: str,
        limit: int = 10,
        search: str = "",
        sort_by: str = "",
        sort_order: str = "desc",
    ):
        try:
            if not self._validate_strategy_exists(strategy_name):
                return error(f"策略不存在: {strategy_name}", 404)
            if report_type not in {self.STEP_ENUM, self.STEP_PRICE, self.STEP_CAPITAL}:
                return error("report_type 必须是 enum | price | capital", 400)

            status_payload, err = self._require_status_for_run(strategy_name, run_id)
            if err:
                return err

            safe_limit = max(1, min(int(limit or 10), 50))
            result_report = (
                status_payload.get("result_report")
                if isinstance(status_payload.get("result_report"), dict)
                else {}
            )
            rows: list = []
            if report_type == self.STEP_ENUM:
                enum_payload = (
                    result_report.get("enum")
                    if isinstance(result_report.get("enum"), dict)
                    else {}
                )
                enum_rows = enum_payload.get("stockRows") if isinstance(enum_payload, dict) else None
                if isinstance(enum_rows, list):
                    rows = [row for row in enum_rows if isinstance(row, dict)]
            if not rows:
                rows = self._build_stock_rows(report_type, limit=50)

            keyword = str(search or "").strip().lower()
            if keyword:
                rows = [
                    row for row in rows
                    if keyword in str(row.get("stock_id", "")).lower()
                    or keyword in str(row.get("stock_name", "")).lower()
                ]

            sortable_fields = {
                self.STEP_ENUM: {"opportunities", "completion_rate", "trigger_span_days"},
                self.STEP_PRICE: {"win_rate", "roi", "hold_days"},
                self.STEP_CAPITAL: {"trade_count", "pnl", "win_rate"},
            }
            if sort_by and sort_by in sortable_fields.get(report_type, set()):
                reverse = str(sort_order or "desc").lower() != "asc"
                rows = sorted(rows, key=lambda r: r.get(sort_by), reverse=reverse)

            total = len(rows)
            return ok({
                "report_type": report_type,
                "rows": rows[:safe_limit],
                "total": total,
            })
        except Exception as e:
            return error(f"读取报告样本股票失败: {str(e)}", 500)

    def get_strategy_report_stock_kline(self, strategy_name: str, run_id: str, stock_id: str):
        try:
            if not self._validate_strategy_exists(strategy_name):
                return error(f"策略不存在: {strategy_name}", 404)
            if not stock_id:
                return error("stock_id 不能为空", 400)

            status_payload = self._read_status(strategy_name)
            if not isinstance(status_payload, dict):
                return error(f"未找到运行记录: {run_id}", 404)
            if str(status_payload.get("run_id") or "") != str(run_id):
                return error(f"未找到运行记录: {run_id}", 404)

            stock_name = next(
                (name for sid, name in self._sample_stocks if str(sid) == str(stock_id)),
                stock_id,
            )
            candles, markers = self._build_mock_kline(stock_id)
            return ok({
                "stock_id": stock_id,
                "stock_name": stock_name,
                "candles": candles,
                "markers": markers,
            })
        except Exception as e:
            return error(f"读取单股票K线失败: {str(e)}", 500)

    def get_strategy_report_compare(
        self,
        strategy_name: str,
        base_run_id: str,
        compare_version: str,
        report_type_raw=None,
    ):
        try:
            if not self._validate_strategy_exists(strategy_name):
                return error(f"策略不存在: {strategy_name}", 404)
            if not base_run_id:
                return error("base_run_id 不能为空", 400)
            if not compare_version:
                return error("compare_version 不能为空", 400)

            report_type, detail = self._parse_single_report_type(report_type_raw)
            if detail:
                return error(detail, 400)
            requested_types = [report_type] if report_type else [
                self.STEP_ENUM,
                self.STEP_PRICE,
                self.STEP_CAPITAL,
            ]

            status_payload, err = self._require_status_for_run(strategy_name, base_run_id)
            if err:
                return err
            base_result_report = (
                status_payload.get("result_report")
                if isinstance(status_payload.get("result_report"), dict)
                else {}
            )
            base_reports, _ = self._build_reports_payload(base_result_report, requested_types)

            compare_row, compare_detail, resolved_compare_version = self._resolve_compare_snapshot(
                strategy_name,
                compare_version,
            )
            if compare_detail:
                return error(compare_detail, 404)
            compare_result_report = (
                compare_row.get("result_report")
                if isinstance(compare_row.get("result_report"), dict)
                else {}
            )
            compare_reports, _ = self._build_reports_payload(compare_result_report, requested_types)

            if report_type:
                return ok({
                    "base_run_id": base_run_id,
                    "compare_version": resolved_compare_version or compare_version,
                    "report_type": report_type,
                    "base_report": base_reports.get(report_type),
                    "compare_report": compare_reports.get(report_type),
                })

            return ok({
                "base_run_id": base_run_id,
                "compare_version": resolved_compare_version or compare_version,
                "base_report": base_reports,
                "compare_report": compare_reports,
            })
        except Exception as e:
            return error(f"读取报告对比数据失败: {str(e)}", 500)

    def list_strategy_versions(self, strategy_name: str):
        try:
            if not self._validate_strategy_exists(strategy_name):
                return error(f"策略不存在: {strategy_name}", 404)
            rows = self._get_snapshot_model().list_by_strategy(strategy_name, limit=10)
            versions = []
            for row in rows:
                sid = int(row.get("snapshot_id") or row.get("version") or 0)
                versions.append({
                    "version_id": self._format_version_id(sid),
                    "version": sid,
                    "created_at": self._to_iso_or_empty(row.get("created_at")),
                    "updated_at": self._to_iso_or_empty(row.get("updated_at")),
                })
            return ok({
                "versions": versions,
                "retention": {"max_count": 10},
                "truncated": len(rows) >= 10,
            })
        except Exception as e:
            return error(f"读取版本列表失败: {str(e)}", 500)

    def get_strategy_version_detail(self, strategy_name: str, version_id: str):
        try:
            if not self._validate_strategy_exists(strategy_name):
                return error(f"策略不存在: {strategy_name}", 404)
            v = self._parse_version_id(version_id)
            if v is None:
                return error(f"version_id 无效: {version_id}", 400)
            row = self._get_snapshot_model().load_by_strategy_snapshot_id(strategy_name, int(v))
            if not row:
                return error(f"版本不存在: {version_id}", 404)
            return ok(self._version_detail_from_snapshot_row(row))
        except Exception as e:
            return error(f"读取版本详情失败: {str(e)}", 500)

    def restore_strategy_version(self, strategy_name: str, version_id: str):
        """Clone the chosen snapshot to a new latest workbench version (does not touch userspace)."""
        try:
            if not self._validate_strategy_exists(strategy_name):
                return error(f"策略不存在: {strategy_name}", 404)
            v = self._parse_version_id(version_id)
            if v is None:
                return error(f"version_id 无效: {version_id}", 400)
            model = self._get_snapshot_model()
            src = model.load_by_strategy_snapshot_id(strategy_name, int(v))
            if not src:
                return error(f"版本不存在: {version_id}", 404)
            settings_snap = src.get("settings_snapshot") if isinstance(src.get("settings_snapshot"), dict) else {}
            normalized = self._canonicalize_api_settings(settings_snap)
            if not isinstance(normalized, dict) or not normalized:
                return error("恢复版本失败: 快照 settings 非法", 422)
            result_rep = src.get("result_report") if isinstance(src.get("result_report"), dict) else {}
            created = model.create_snapshot(
                strategy_name,
                normalized,
                result_report=dict(result_rep or {}),
                settings_finger_print_id=str(src.get(COL_SETTINGS_FP) or ""),
                env_fingerprint_id=str(src.get(COL_ENV_FP) or ""),
            )
            new_v = int(created.get("snapshot_id") or 0)
            if new_v <= 0:
                return error("恢复工作台版本失败", 500)

            return ok({
                "restored": True,
                "strategy_name": strategy_name,
                "version_id": self._format_version_id(new_v),
                "restored_from_version_id": self._format_version_id(int(v)),
            })
        except Exception as e:
            return error(f"恢复版本失败: {str(e)}", 500)

    def create_strategy_version(self, strategy_name: str, payload: dict):
        try:
            if not self._validate_strategy_exists(strategy_name):
                return error(f"策略不存在: {strategy_name}", 404)
            body = payload if isinstance(payload, dict) else {}
            settings = body.get("settings")
            if not isinstance(settings, dict):
                return error("请求体缺少 settings 或类型错误", 400)

            normalized_runtime_settings, detail = self._normalize_runtime_settings(strategy_name, settings)
            if normalized_runtime_settings is None:
                return error(detail, 422)

            api_settings = self._runtime_to_api_settings(normalized_runtime_settings)
            created = self._get_snapshot_model().create_snapshot(
                strategy_name,
                api_settings,
                result_report={},
            )
            version = int(created.get("snapshot_id") or 0)
            if version <= 0:
                return error("创建版本失败", 500)

            return ok({
                "version_id": self._format_version_id(version),
                "created": True,
            })
        except Exception as e:
            return error(f"固化版本失败: {str(e)}", 500)


def _strategy_workbench_run_chain_entry(
    strategy_name: str,
    run_id: str,
    resolved_chain: list,
    cancel_event,
) -> None:
    """Run the workbench chain in a dedicated child process (main thread); avoids BFF worker threads."""
    service = StrategyWorkbenchImplementation()
    service._run_chain_worker(strategy_name, run_id, resolved_chain, cancel_event)
