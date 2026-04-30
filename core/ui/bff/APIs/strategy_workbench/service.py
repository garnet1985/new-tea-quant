"""Strategy workbench service logic."""

import copy
import json
import logging
import multiprocessing as mp
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from uuid import uuid4

from core.infra.project_context.config_manager import ConfigManager
from core.infra.project_context.path_manager import PathManager
from core.modules.strategy.services.progress import ProgressRecorder
from core.tables.ui_bff.strategy_workbench_snapshot.model import SysStrategyWorkbenchSnapshotModel
from core.ui.bff.shared.file_ops import atomic_write_text, backup_file
from core.ui.bff.shared.response import error, ok

logger = logging.getLogger(__name__)


class StrategyWorkbenchService:
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

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _build_run_id() -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"run_{stamp}_{uuid4().hex[:6]}"

    @staticmethod
    def _status_file(strategy_name: str):
        return PathManager.userspace() / ".ntq" / "tmp" / "strategy-workbench" / f"{strategy_name}.json"

    @staticmethod
    def _read_status(strategy_name: str):
        path = StrategyWorkbenchService._status_file(strategy_name)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    @staticmethod
    def _write_status(strategy_name: str, payload: dict) -> None:
        path = StrategyWorkbenchService._status_file(strategy_name)
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        atomic_write_text(path, content)

    @staticmethod
    def _resolve_chain(target_step: str, step_status: dict):
        if target_step == StrategyWorkbenchService.STEP_ENUM:
            return [StrategyWorkbenchService.STEP_ENUM]
        if (step_status or {}).get("enum") == StrategyWorkbenchService.STEP_STATUS_DONE:
            return [target_step]
        return [StrategyWorkbenchService.STEP_ENUM, target_step]

    @staticmethod
    def _mock_step_summary(step: str):
        # BFF 占位：真实枚举应由策略引擎接入后写入 result_summary。
        if step == StrategyWorkbenchService.STEP_ENUM:
            return {
                "opportunities": 128,
                "totalStocks": 42,
                "triggerStocks": 36,
                "completedCount": 120,
                "unfinishedCount": 8,
                "completionRate": 93.75,
            }
        if step == StrategyWorkbenchService.STEP_PRICE:
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

    @staticmethod
    def _parse_report_types(raw):
        valid = {StrategyWorkbenchService.STEP_ENUM, StrategyWorkbenchService.STEP_PRICE, StrategyWorkbenchService.STEP_CAPITAL}
        if raw is None:
            return [StrategyWorkbenchService.STEP_ENUM, StrategyWorkbenchService.STEP_PRICE, StrategyWorkbenchService.STEP_CAPITAL], ""
        parts = [p.strip() for p in str(raw).split(",") if p.strip()]
        if not parts:
            return [StrategyWorkbenchService.STEP_ENUM, StrategyWorkbenchService.STEP_PRICE, StrategyWorkbenchService.STEP_CAPITAL], ""
        invalid = [p for p in parts if p not in valid]
        if invalid:
            return [], f"report_types 包含无效项: {', '.join(invalid)}"
        dedup = []
        for p in parts:
            if p not in dedup:
                dedup.append(p)
        return dedup, ""

    @staticmethod
    def _build_reports_payload(result_summary: dict, requested_types: list):
        result_summary = result_summary if isinstance(result_summary, dict) else {}
        enum_result = result_summary.get("enum") if isinstance(result_summary.get("enum"), dict) else None
        price_result = result_summary.get("price") if isinstance(result_summary.get("price"), dict) else None
        capital_result = result_summary.get("capital") if isinstance(result_summary.get("capital"), dict) else None

        reports = {}
        available_tabs = []
        for report_type in requested_types:
            if report_type == StrategyWorkbenchService.STEP_ENUM:
                # 枚举步骤完成后即应有报告占位（含 opportunities=0），不因「无数」而隐藏 Tab。
                if not isinstance(enum_result, dict):
                    payload = None
                else:
                    opportunities = int(enum_result.get("opportunities") or 0)
                    payload = {
                        "opportunities": opportunities,
                        "totalStocks": int(enum_result.get("totalStocks") or 0),
                        "triggerStocks": int(enum_result.get("triggerStocks") or 0),
                        "completedCount": int(enum_result.get("completedCount") or 0),
                        "unfinishedCount": int(enum_result.get("unfinishedCount") or 0),
                        "completionRate": float(enum_result.get("completionRate") or 0.0),
                    }
            elif report_type == StrategyWorkbenchService.STEP_PRICE:
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
            StrategyWorkbenchService.STEP_ENUM,
            StrategyWorkbenchService.STEP_PRICE,
            StrategyWorkbenchService.STEP_CAPITAL,
        }:
            return None, f"report_type 必须是 enum | price | capital: {value}"
        return value, ""

    def _resolve_compare_snapshot(self, strategy_name: str, compare_version: str):
        model = self._get_snapshot_model()
        raw = str(compare_version or "").strip().lower()
        if not raw:
            return None, "compare_version 不能为空", None
        if raw == "latest":
            rows = model.list_by_strategy(strategy_name, limit=1)
            if not rows:
                return None, f"对比版本不存在: {compare_version}", None
            row = rows[0]
            v = int(row.get("version") or 0)
            if v <= 0:
                return None, f"对比版本不存在: {compare_version}", None
            return row, "", self._format_version_id(v)

        version_num = self._parse_version_id(compare_version)
        if version_num is None:
            return None, f"compare_version 无效: {compare_version}", None
        row = model.load_by_strategy_version(strategy_name, version_num)
        if not row:
            return None, f"对比版本不存在: {compare_version}", None
        return row, "", self._format_version_id(version_num)

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

    @staticmethod
    def _format_version_id(version: int) -> str:
        return f"v{int(version)}"

    @staticmethod
    def _parse_version_id(version_id: str):
        raw = str(version_id or "").strip().lower()
        if not raw:
            return None
        if raw.startswith("v"):
            raw = raw[1:]
        if not raw.isdigit():
            return None
        return int(raw)

    @staticmethod
    def _to_iso_or_empty(value):
        if value is None:
            return ""
        try:
            if hasattr(value, "isoformat"):
                return value.isoformat()
            return str(value)
        except Exception:
            return ""

    @staticmethod
    def _stable_json_hash(value: Any) -> str:
        try:
            canonical = json.dumps(
                value if value is not None else {},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except Exception:
            canonical = "{}"
        import hashlib
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _runtime_to_api_settings_fallback(runtime_settings):
        """Lightweight fallback when heavy settings imports are temporarily locked."""
        if not isinstance(runtime_settings, dict):
            return {}
        api_settings = dict(runtime_settings)
        meta_from_runtime = {
            "name": runtime_settings.get("name", ""),
            "description": runtime_settings.get("description", ""),
            "is_enabled": bool(runtime_settings.get("is_enabled", False)),
        }
        existing_meta = runtime_settings.get("meta")
        if isinstance(existing_meta, dict):
            meta_from_runtime.update({
                "name": existing_meta.get("name", meta_from_runtime["name"]),
                "description": existing_meta.get("description", meta_from_runtime["description"]),
                "is_enabled": bool(existing_meta.get("is_enabled", meta_from_runtime["is_enabled"])),
            })
        api_settings["meta"] = meta_from_runtime
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
                rendered = StrategyWorkbenchService._format_python_literal(v, level + 1)
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
                rendered = StrategyWorkbenchService._format_python_literal(item, level + 1)
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
        if not isinstance(settings, dict):
            return None, "请求体缺少 settings 或类型错误"

        runtime_settings = self._api_to_runtime_settings(settings)
        runtime_settings["name"] = strategy_name

        from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
            StrategySettings,
        )
        validated = StrategySettings(raw_settings=dict(runtime_settings))
        report = validated.validate()
        if not report.is_usable():
            critical_errors = [
                f"{item.get('field_path', 'unknown')}: {item.get('message', '')}"
                for item in (report.errors or [])
                if item.get("level") == "critical"
            ]
            detail = "；".join(critical_errors) if critical_errors else "settings 校验失败"
            return None, detail
        normalized_runtime_settings = validated.to_dict()
        normalized_runtime_settings["name"] = strategy_name
        return normalized_runtime_settings, ""

    def _save_runtime_settings_file(self, strategy_name: str, normalized_runtime_settings: dict):
        settings_file = PathManager.strategy_settings(strategy_name)
        backup_file(settings_file)
        raw_output = self._build_settings_file_text(normalized_runtime_settings, pretty=False)
        atomic_write_text(settings_file, raw_output)
        pretty_output = self._build_settings_file_text(normalized_runtime_settings, pretty=True)
        atomic_write_text(settings_file, pretty_output)

    @staticmethod
    def _coerce_db_settings_snapshot(raw: Any):
        """把表里读出的 settings_snapshot 规整为 dict；无效返回 None。"""
        if raw is None:
            return None
        if isinstance(raw, dict):
            return raw if raw else None
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return None
            if isinstance(parsed, dict) and parsed:
                return parsed
            return None
        return None

    @staticmethod
    def _coerce_db_result_summary(raw: Any):
        """把表里读出的 result_summary 规整为 dict；无效返回空 dict。"""
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return {}
            return parsed if isinstance(parsed, dict) else {}
        return {}

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
            v = int(row.get("version") or 0)
            if snap:
                return self._canonicalize_api_settings(snap)
            logger.error(
                "Workbench enum: 存在快照行但 settings_snapshot 无效或为空 | strategy=%s version=%s "
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

    @staticmethod
    def _enum_summary_row_to_bff_payload(row: dict) -> dict:
        if not isinstance(row, dict):
            row = {}
        return {
            "opportunities": int(row.get("opportunities") or 0),
            "totalStocks": int(row.get("totalStocks") or 0),
            "triggerStocks": int(row.get("triggerStocks") or 0),
            "completedCount": int(row.get("completedCount") or 0),
            "unfinishedCount": int(row.get("unfinishedCount") or 0),
            "completionRate": float(row.get("completionRate") or 0.0),
        }

    def _build_workbench_opportunity_enumerator_flow(
        self,
        strategy_name: str,
        run_id: Optional[str],
    ) -> Tuple[Any, Any, Optional[str]]:
        """
        构造与真实工作台枚举一致的 OpportunityEnumeratorFlow。
        run_id 为空时不绑定进度文件（用于 reuse 预览）。
        返回 (flow, strategy_info, error_message)。
        """
        raw_api = self._fetch_api_settings_for_run(strategy_name, run_id=run_id)
        if not raw_api:
            return None, None, "无法读取策略配置（目录或 settings 缺失）"

        normalized_runtime_settings, detail = self._normalize_runtime_settings(
            strategy_name,
            raw_api,
        )
        if normalized_runtime_settings is None:
            return None, None, detail or "settings 校验失败"

        from core.modules.data_manager import DataManager
        from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
            StrategySettingsView,
        )
        from core.modules.strategy.engines.shared.helpers.stock_sampling import StockSamplingHelper
        from core.modules.strategy.engines.simulator.enumerator import (
            OpportunityEnumeratorFlow,
            OpportunityEnumeratorSettings,
        )
        from core.modules.strategy.strategy_manager import StrategyManager
        from core.utils.date.date_utils import DateUtils

        settings_view = StrategySettingsView.from_dict(normalized_runtime_settings)
        strategy_manager = StrategyManager(is_verbose=False)
        strategy_info = strategy_manager.get_strategy_info(strategy_name)
        if strategy_info is None:
            return None, None, f"策略未被发现或无法加载: {strategy_name}"

        enum_settings = OpportunityEnumeratorSettings.from_base(settings_view)
        data_mgr = DataManager(is_verbose=False)
        all_stocks = data_mgr.service.stock.list.load(filtered=True)
        if enum_settings.use_sampling:
            stock_list = StockSamplingHelper.get_stock_list(
                all_stocks=all_stocks,
                sampling_amount=settings_view.sampling_amount,
                sampling_config=settings_view.sampling_config,
                strategy_name=strategy_name,
            )
        else:
            stock_list = [s["id"] for s in all_stocks]

        latest_date = data_mgr.service.calendar.get_latest_completed_trading_date()
        start_date = (settings_view.start_date or "").strip() or DateUtils.DEFAULT_START_DATE
        end_date = (settings_view.end_date or "").strip() or latest_date

        flow = OpportunityEnumeratorFlow(
            start_date=start_date,
            end_date=end_date,
            stock_list=stock_list,
            max_workers=enum_settings.max_workers,
            base_settings=settings_view,
            force_refresh=False,
            workbench_strategy_name=strategy_name if run_id else None,
            workbench_run_id=str(run_id) if run_id else None,
        )
        return flow, strategy_info, None

    def _enumerator_fingerprint_for_row_snapshot(
        self,
        strategy_name: str,
        flow_ref: Any,
        strategy_info: Any,
        api_snapshot: dict,
    ) -> Any:
        """
        与 opportunity_enumerator_flow.preprocess 中指纹构造完全一致：
        copy.deepcopy(base_settings.to_dict()) + build_request_fingerprint（同一 stock_list / 日期窗）。
        返回 EnumeratorFingerprint，供完整 id 与 scope id 匹配。
        """
        from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
            StrategySettingsView,
        )

        normalized, _ = self._normalize_runtime_settings(strategy_name, api_snapshot)
        if normalized is None:
            return None
        base_alt = StrategySettingsView.from_dict(normalized)
        settings_for_fingerprint = copy.deepcopy(base_alt.to_dict())
        worker_ref = flow_ref._impl.resolve_worker_blueprint(
            strategy_name=strategy_name, strategy_info=strategy_info
        )
        return flow_ref._impl.build_request_fingerprint(
            strategy_name=strategy_name,
            settings_payload=settings_for_fingerprint,
            stock_ids=flow_ref.stock_list,
            worker_ref=worker_ref,
        )

    def _workbench_enum_preprocess(self, strategy_name: str, run_id: Optional[str]):
        """
        与工作台枚举 run 一致的 preprocess（指纹 + plan_reuse），供临时层命中判断与落库。
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

    def _try_workbench_temp_snapshot_enum(
        self, strategy_name: str, run_id: str
    ) -> Optional[Tuple[dict, str, str]]:
        """
        临时层（sys_strategy_workbench_snapshot）：若任一历史版本存过相同 fingerprint 的枚举摘要，直接复用。
        物理目录被 prune 时仍可命中；返回 (bff_enum_payload, fingerprint_id, scope_fingerprint_id)。

        匹配顺序：
        1) enum_meta.fingerprint_id 或 scope_fingerprint_id（不含日期，见 EnumeratorFingerprint）
        2) 历史行按 build_request_fingerprint 重算，完整 id 或 scope id 与当前一致
        """
        from core.modules.strategy.engines.simulator.enumerator.data_classes.fingerprint import (
            EnumeratorFingerprint,
        )

        preprocessed, err = self._workbench_enum_preprocess(strategy_name, run_id)
        if err or not preprocessed or not preprocessed.request_fingerprint:
            return None
        req_fp = preprocessed.request_fingerprint
        fp_id = str(req_fp.fingerprint_id or "")
        if not fp_id:
            return None
        scope_id = EnumeratorFingerprint.compute_enumerator_scope_fingerprint_id(req_fp)
        logger.warning(
            "SWB enum temp-cache check: strategy=%s run_id=%s req_fp=%s req_scope_fp=%s",
            strategy_name,
            run_id,
            fp_id,
            scope_id,
        )
        flow_ref, strategy_info, ferr = self._build_workbench_opportunity_enumerator_flow(
            strategy_name, run_id
        )
        if ferr or not flow_ref or not strategy_info:
            return None
        model = self._get_snapshot_model()
        rows = model.list_by_strategy_enum_fingerprint(
            strategy_name,
            enum_fingerprint_id=fp_id,
            enum_scope_fingerprint_id=scope_id,
            limit=200,
        )
        from_fp_query = True
        if not rows:
            rows = model.list_by_strategy(strategy_name, limit=200)
            from_fp_query = False
        logger.warning(
            "SWB enum temp-cache candidates: strategy=%s run_id=%s source=%s rows=%d",
            strategy_name,
            run_id,
            "fingerprint_index" if from_fp_query else "full_scan",
            len(rows or []),
        )
        no_result_summary = 0
        no_enum_payload = 0
        fp_mismatch = 0
        for row in rows or []:
            rs = self._coerce_db_result_summary(row.get("result_summary"))
            if not rs:
                no_result_summary += 1
                continue
            em = rs.get("enum_meta")
            em = em if isinstance(em, dict) else {}
            row_fp_col = str(row.get("enum_fingerprint_id") or "")
            row_scope_col = str(row.get("enum_scope_fingerprint_id") or "")
            id_ok = row_fp_col == fp_id or str(em.get("fingerprint_id") or "") == fp_id
            scope_ok = (
                row_scope_col == scope_id
                or str(em.get("scope_fingerprint_id") or "") == scope_id
            )
            if not id_ok and not scope_ok:
                fp_mismatch += 1
                continue
            en = rs.get("enum")
            if not isinstance(en, dict):
                no_enum_payload += 1
                continue
            if "opportunities" not in en and "totalStocks" not in en:
                no_enum_payload += 1
                continue
            logger.warning(
                "SWB enum temp-cache HIT(row): strategy=%s run_id=%s version=%s row_fp_col=%s row_scope_col=%s row_fp_meta=%s row_scope_meta=%s",
                strategy_name,
                run_id,
                int(row.get("version") or 0),
                row_fp_col,
                row_scope_col,
                str(em.get("fingerprint_id") or ""),
                str(em.get("scope_fingerprint_id") or ""),
            )
            payload = self._enum_summary_row_to_bff_payload(en)
            return payload, fp_id, scope_id
        # Fingerprint-index query may return an empty-shell row (same fingerprint columns but
        # no enum result_summary yet). In that case, fallback to full scan to find older usable rows.
        if from_fp_query:
            rows_full = model.list_by_strategy(strategy_name, limit=200)
            if rows_full:
                rows = rows_full
                logger.warning(
                    "SWB enum temp-cache fallback full-scan: strategy=%s run_id=%s rows=%d",
                    strategy_name,
                    run_id,
                    len(rows or []),
                )
        recompute_mismatch = 0
        recompute_no_enum = 0
        for row in rows or []:
            rs = self._coerce_db_result_summary(row.get("result_summary"))
            if not rs:
                continue
            en = rs.get("enum")
            if not isinstance(en, dict):
                recompute_no_enum += 1
                continue
            if "opportunities" not in en and "totalStocks" not in en:
                recompute_no_enum += 1
                continue
            snap = row.get("settings_snapshot")
            if not isinstance(snap, dict):
                continue
            fp_row = self._enumerator_fingerprint_for_row_snapshot(
                strategy_name, flow_ref, strategy_info, snap
            )
            if fp_row is None:
                continue
            row_fp = str(fp_row.fingerprint_id)
            row_scope = EnumeratorFingerprint.compute_enumerator_scope_fingerprint_id(fp_row)
            if row_fp != fp_id and row_scope != scope_id:
                recompute_mismatch += 1
                continue
            logger.warning(
                "SWB enum temp-cache HIT(recompute): strategy=%s run_id=%s version=%s row_fp=%s row_scope=%s",
                strategy_name,
                run_id,
                int(row.get("version") or 0),
                row_fp,
                row_scope,
            )
            payload = self._enum_summary_row_to_bff_payload(en)
            return payload, fp_id, scope_id
        logger.warning(
            "SWB enum temp-cache MISS: strategy=%s run_id=%s req_fp=%s req_scope_fp=%s no_result_summary=%d fp_mismatch=%d no_enum_payload=%d recompute_mismatch=%d recompute_no_enum=%d",
            strategy_name,
            run_id,
            fp_id,
            scope_id,
            no_result_summary,
            fp_mismatch,
            no_enum_payload,
            recompute_mismatch,
            recompute_no_enum,
        )
        return None

    def _write_enum_to_workbench_snapshot(
        self,
        strategy_name: str,
        run_id: str,
        enum_payload: dict,
        fingerprint_id: str,
        scope_fingerprint_id: str = "",
    ) -> None:
        """将本次枚举摘要写入当前 run 对应的快照版本行（含完整指纹与 scope 指纹，供临时层命中）。"""
        try:
            status_payload = self._read_status(strategy_name) or {}
            if str(status_payload.get("run_id") or "") != str(run_id):
                return
            v = int(status_payload.get("workbench_snapshot_version") or 0)
            if v <= 0 or not fingerprint_id:
                run_snap = self._coerce_db_settings_snapshot(
                    status_payload.get("run_settings_snapshot")
                )
                if not run_snap:
                    return
                model = self._get_snapshot_model()
                # Merge-on-fingerprint: if an existing snapshot already has the same
                # enum fingerprint (or scope fingerprint), reuse it instead of creating
                # a duplicated version row.
                matched_rows = model.list_by_strategy_enum_fingerprint(
                    strategy_name,
                    enum_fingerprint_id=fingerprint_id,
                    enum_scope_fingerprint_id=scope_fingerprint_id or "",
                    limit=1,
                )
                if matched_rows:
                    mv = int((matched_rows[0] or {}).get("version") or 0)
                    if mv > 0:
                        rs0 = (matched_rows[0] or {}).get("result_summary")
                        rs = dict(rs0) if isinstance(rs0, dict) else {}
                        rs["enum"] = dict(enum_payload)
                        rs["enum_meta"] = {
                            "fingerprint_id": fingerprint_id,
                            "scope_fingerprint_id": scope_fingerprint_id or "",
                            "updated_at": self._now_iso(),
                        }
                        model.update_result_summary(
                            strategy_name,
                            mv,
                            rs,
                            enum_fingerprint_id=fingerprint_id,
                            enum_scope_fingerprint_id=scope_fingerprint_id or "",
                        )
                        status_payload["workbench_snapshot_version"] = mv
                        status_payload["updated_at"] = self._now_iso()
                        self._write_status(strategy_name, status_payload)
                        return
                created = model.create_version(
                    strategy_name=strategy_name,
                    settings_snapshot=self._canonicalize_api_settings(run_snap),
                    result_summary={
                        "enum": dict(enum_payload),
                        "enum_meta": {
                            "fingerprint_id": fingerprint_id,
                            "scope_fingerprint_id": scope_fingerprint_id or "",
                            "updated_at": self._now_iso(),
                        },
                    },
                    enum_fingerprint_id=fingerprint_id,
                    enum_scope_fingerprint_id=scope_fingerprint_id or "",
                )
                new_v = int(created.get("version") or 0)
                if new_v > 0:
                    status_payload["workbench_snapshot_version"] = new_v
                    status_payload["updated_at"] = self._now_iso()
                    self._write_status(strategy_name, status_payload)
                return
            model = self._get_snapshot_model()
            current = model.load_by_strategy_version(strategy_name, v)
            if not current:
                return
            rs0 = current.get("result_summary")
            rs: Dict[str, Any] = dict(rs0) if isinstance(rs0, dict) else {}
            rs["enum"] = dict(enum_payload)
            rs["enum_meta"] = {
                "fingerprint_id": fingerprint_id,
                "scope_fingerprint_id": scope_fingerprint_id or "",
                "updated_at": self._now_iso(),
            }
            model.update_result_summary(
                strategy_name,
                v,
                rs,
                enum_fingerprint_id=fingerprint_id,
                enum_scope_fingerprint_id=scope_fingerprint_id or "",
            )
        except Exception:
            logger.exception(
                "写入工作台枚举快照失败: strategy_name=%s run_id=%s",
                strategy_name,
                run_id,
            )

    def _execute_opportunity_enumeration(self, strategy_name: str, run_id: str):
        """
        调用核心 OpportunityEnumeratorFlow（含 fingerprint 复用缓存）。
        返回 (summary_payload, error_message)；成功时 error_message 为 None。
        """
        try:
            flow, strategy_info, err = self._build_workbench_opportunity_enumerator_flow(
                strategy_name, run_id
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
            return payload, None
        except Exception as exc:
            logger.exception(
                "策略工作台枚举失败: strategy_name=%s",
                strategy_name,
            )
            return None, str(exc)

    def get_enumerator_reuse_preview(self, strategy_name: str):
        """
        仅做 preprocess / plan_reuse，不跑子进程枚举。
        若将 REUSE_FULL，则根据磁盘 0_metadata 返回与 build_reuse_summary 一致的 enum 摘要，供前端先展示再决定是否跑任务。
        """
        try:
            if not self._validate_strategy_exists(strategy_name):
                return error(f"策略不存在: {strategy_name}", 404)

            from core.modules.strategy.enums import ReuseAction

            flow, strategy_info, err = self._build_workbench_opportunity_enumerator_flow(
                strategy_name, None
            )
            if err:
                return error(err, 422)

            preprocessed = flow.preprocess(
                strategy_name=strategy_name, strategy_info=strategy_info
            )
            req_fp = preprocessed.request_fingerprint
            out: dict = {
                "fingerprint_id": str(req_fp.fingerprint_id) if req_fp else "",
                "reuse_action": preprocessed.reuse_action.value,
                "would_reuse_full": preprocessed.reuse_action == ReuseAction.REUSE_FULL,
                "not_reused_because": preprocessed.not_reused_because.value,
            }

            if preprocessed.reuse_action == ReuseAction.REUSE_FULL:
                if preprocessed.reuse_version_dir:
                    summaries = flow._impl.build_reuse_summary(
                        strategy_name=strategy_name,
                        version_dir=preprocessed.reuse_version_dir,
                        reuse_action=ReuseAction.REUSE_FULL,
                        not_reused_because=preprocessed.not_reused_because,
                    )
                    if summaries and isinstance(summaries[0], dict):
                        out["enum_result_preview"] = self._enum_summary_row_to_bff_payload(
                            summaries[0]
                        )
                    out["cached_version_dir"] = str(preprocessed.reuse_version_dir)
            elif preprocessed.reuse_action == ReuseAction.RUN_DIFF_STOCKS:
                out["cached_version_dir"] = (
                    str(preprocessed.reuse_version_dir)
                    if preprocessed.reuse_version_dir
                    else ""
                )
                missing = preprocessed.missing_stock_ids or []
                out["missing_stock_count"] = len(missing)
                out["missing_stock_ids_sample"] = missing[:50]

            return ok(out)
        except Exception as e:
            logger.exception("枚举复用预览失败: strategy_name=%s", strategy_name)
            return error(f"枚举复用预览失败: {str(e)}", 500)

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
            "updated_at": self._now_iso(),
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
                    "updated_at": self._now_iso(),
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
                "updated_at": self._now_iso(),
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
                        "updated_at": self._now_iso(),
                    })
                    self._write_status(strategy_name, status_payload)
                    return

                try:
                    # 1) 临时层（DB 快照，按 fingerprint）→ 2) 否则物理缓存/运算在 flow.run 内
                    temp_hit = self._try_workbench_temp_snapshot_enum(strategy_name, run_id)
                    if temp_hit is not None:
                        enum_payload, enum_fp, scope_fp = temp_hit
                        self._write_enum_to_workbench_snapshot(
                            strategy_name,
                            run_id,
                            enum_payload,
                            enum_fp,
                            scope_fingerprint_id=scope_fp,
                        )
                        enum_err = None
                    else:
                        enum_payload, enum_err = self._execute_opportunity_enumeration(
                            strategy_name, run_id
                        )
                        if not enum_err:
                            pp, perr = self._workbench_enum_preprocess(strategy_name, run_id)
                            if (
                                not perr
                                and pp
                                and pp.request_fingerprint
                            ):
                                from core.modules.strategy.engines.simulator.enumerator.data_classes.fingerprint import (
                                    EnumeratorFingerprint,
                                )

                                scope_fp = EnumeratorFingerprint.compute_enumerator_scope_fingerprint_id(
                                    pp.request_fingerprint
                                )
                                self._write_enum_to_workbench_snapshot(
                                    strategy_name,
                                    run_id,
                                    enum_payload,
                                    str(pp.request_fingerprint.fingerprint_id),
                                    scope_fingerprint_id=scope_fp,
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
                            "updated_at": self._now_iso(),
                        })
                        self._write_status(strategy_name, status_payload)
                        return

                    step_status = status_payload.get("step_status") or {}
                    if isinstance(step_status, dict):
                        step_status[step] = self.STEP_STATUS_DONE
                    result = status_payload.get("result_summary")
                    if not isinstance(result, dict):
                        result = {}
                    result[step] = enum_payload
                    status_payload["step_status"] = step_status
                    status_payload["result_summary"] = result
                    status_payload["progress_pct"] = 100
                    status_payload["running_step"] = step
                    status_payload["updated_at"] = self._now_iso()
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
                current["updated_at"] = self._now_iso()
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
            status_payload["updated_at"] = self._now_iso()

            if cancel_event.is_set():
                status_payload["state"] = self.RUN_STATE_CANCELLED
                self._write_status(strategy_name, status_payload)
                return

            result = status_payload.get("result_summary")
            if not isinstance(result, dict):
                result = {}
            result[step] = self._mock_step_summary(step)
            status_payload["result_summary"] = result
            self._write_status(strategy_name, status_payload)

        final_payload = self._read_status(strategy_name) or {}
        if str(final_payload.get("run_id") or "") == run_id:
            final_payload["state"] = self.RUN_STATE_DONE
            final_payload["running_step"] = ""
            final_payload["progress_pct"] = 100
            final_payload["updated_at"] = self._now_iso()
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
            from core.modules.strategy.engines.shared.data_classes.strategy_settings.strategy_settings import (
                StrategySettings,
            )
            validated = StrategySettings(raw_settings=dict(runtime_settings))
            report = validated.validate()
            if not report.is_usable():
                return {}
            return validated.to_dict()
        except Exception:
            logger.exception(
                "runtime->api settings canonicalization failed; fallback formatter used"
            )
            return self._runtime_to_api_settings_fallback(runtime_settings)

    def _api_to_runtime_settings(self, api_settings):
        if not isinstance(api_settings, dict):
            return {}
        runtime = dict(api_settings)
        # Backward compatibility: old API payloads may still carry meta block.
        meta = runtime.pop("meta", None)
        if isinstance(meta, dict):
            runtime["name"] = meta.get("name", runtime.get("name", ""))
            runtime["description"] = meta.get("description", runtime.get("description", ""))
            runtime["is_enabled"] = bool(meta.get("is_enabled", runtime.get("is_enabled", False)))
        return runtime

    def _canonicalize_api_settings(self, api_settings):
        """
        Normalize any API settings payload to canonical validated shape using StrategySettings.
        """
        runtime = self._api_to_runtime_settings(api_settings)
        return self._runtime_to_api_settings(runtime)

    def _get_latest_workbench_snapshot_row(self, strategy_name: str):
        model = self._get_snapshot_model()
        rows = model.list_by_strategy(strategy_name, limit=1)
        return rows[0] if rows else None

    def get_strategy_settings(self, strategy_name: str):
        try:
            strategy_dir = PathManager.strategy(strategy_name)
            settings_file = PathManager.strategy_settings(strategy_name)
            if not strategy_dir.exists() or not strategy_dir.is_dir():
                return error(f"策略不存在: {strategy_name}", 404)
            if not settings_file.exists():
                return error(f"策略缺少 settings.py: {strategy_name}", 404)

            row = self._get_latest_workbench_snapshot_row(strategy_name)
            if row:
                settings_snapshot = row.get("settings_snapshot")
                if isinstance(settings_snapshot, dict) and settings_snapshot:
                    v = int(row.get("version") or 0)
                    return ok({
                        "strategy_name": strategy_name,
                        "settings": self._canonicalize_api_settings(settings_snapshot),
                        "settings_source": "workbench_snapshot",
                        "workbench_version_id": self._format_version_id(v) if v > 0 else "",
                    })

            runtime_settings = ConfigManager.load_python(settings_file, var_name="settings")
            if not isinstance(runtime_settings, dict):
                return error(f"策略 settings 无效: {strategy_name}", 500)

            return ok({
                "strategy_name": strategy_name,
                "settings": self._runtime_to_api_settings(runtime_settings),
                "settings_source": "userspace",
                "workbench_version_id": "",
            })
        except Exception as e:
            return error(f"读取策略 settings 失败: {str(e)}", 500)

    def save_strategy_settings(self, strategy_name: str, payload: dict):
        """Persist workbench draft as a new row in sys_strategy_workbench_snapshot (never writes userspace)."""
        try:
            if not isinstance(payload, dict):
                return error("请求体必须为对象", 400)
            settings = payload.get("settings")
            if not self._validate_strategy_exists(strategy_name):
                return error(f"策略不存在: {strategy_name}", 404)

            normalized_runtime_settings, detail = self._normalize_runtime_settings(strategy_name, settings)
            if normalized_runtime_settings is None:
                return error(detail, 422)

            api_settings = self._runtime_to_api_settings(normalized_runtime_settings)
            model = self._get_snapshot_model()
            # Deduplicate identical snapshots: same canonical settings should reuse existing row
            # instead of creating a new version.
            target_hash = self._stable_json_hash(api_settings)
            rows = model.list_by_strategy(strategy_name, limit=200)
            for row in rows or []:
                snap = self._coerce_db_settings_snapshot(row.get("settings_snapshot"))
                if not isinstance(snap, dict):
                    continue
                if self._stable_json_hash(snap) != target_hash:
                    continue
                existing_v = int(row.get("version") or 0)
                if existing_v > 0:
                    return ok({
                        "strategy_name": strategy_name,
                        "saved": True,
                        "merged": True,
                        "version_id": self._format_version_id(existing_v),
                    })
            created = model.create_version(
                strategy_name=strategy_name,
                settings_snapshot=api_settings,
                result_summary={},
            )
            version = int(created.get("version") or 0)
            if version <= 0:
                return error("写入工作台快照失败", 500)

            return ok({
                "strategy_name": strategy_name,
                "saved": True,
                "merged": False,
                "version_id": self._format_version_id(version),
            })
        except Exception as e:
            return error(f"保存策略 settings 失败: {str(e)}", 500)

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
            wb_snapshot_v = int(row.get("version") or 0) if row else 0
            if run_api_settings is not None:
                # For run-scoped settings, only persist to DB on successful enum completion.
                wb_snapshot_v = 0
            status_payload = {
                "run_id": run_id,
                "strategy_name": strategy_name,
                "state": self.RUN_STATE_RUNNING,
                "target_step": target_step,
                "resolved_chain": resolved_chain,
                "running_step": resolved_chain[0],
                "progress_pct": 0,
                "step_status": step_status,
                "result_summary": {},
                "workbench_snapshot_version": wb_snapshot_v,
                "run_settings_snapshot": run_api_settings,
                "updated_at": self._now_iso(),
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

    def get_strategy_run_status(self, strategy_name: str, run_id: str):
        try:
            status_payload = self._read_status(strategy_name)
            if not isinstance(status_payload, dict):
                return error(f"未找到运行记录: {run_id}", 404)
            if str(status_payload.get("run_id") or "") != str(run_id):
                return error(f"未找到运行记录: {run_id}", 404)

            step_status = status_payload.get("step_status")
            if not isinstance(step_status, dict):
                step_status = {
                    self.STEP_ENUM: self.STEP_STATUS_IDLE,
                    self.STEP_PRICE: self.STEP_STATUS_IDLE,
                    self.STEP_CAPITAL: self.STEP_STATUS_IDLE,
                }

            progress_pct = int(status_payload.get("progress_pct") or 0)
            out: dict = {
                "run_id": run_id,
                "state": status_payload.get("state", self.RUN_STATE_RUNNING),
                "running_step": status_payload.get("running_step", ""),
                "progress_pct": progress_pct,
                "step_status": step_status,
                "result_summary": status_payload.get("result_summary") or {},
                "updated_at": status_payload.get("updated_at", self._now_iso()),
            }
            if str(status_payload.get("running_step") or "") == self.STEP_ENUM:
                ep = ProgressRecorder.for_strategy_run_step(
                    strategy_name, run_id, self.STEP_ENUM
                ).get_progress()
                if ep:
                    out["progress_pct"] = int(ep.get("progress_pct") or progress_pct)
                    out["enumerator_progress"] = ep

            state = str(status_payload.get("state") or "")
            if state in {
                self.RUN_STATE_DONE,
                self.RUN_STATE_FAILED,
                self.RUN_STATE_CANCELLED,
            }:
                with self._run_lock:
                    self._run_cancel_events.pop(str(run_id), None)
                    proc = self._run_processes.pop(str(run_id), None)
                if proc is not None:
                    proc.join(timeout=1.0)

            return ok(out)
        except Exception as e:
            return error(f"读取执行状态失败: {str(e)}", 500)

    def cancel_strategy_run(self, strategy_name: str, run_id: str):
        try:
            status_payload = self._read_status(strategy_name)
            if not isinstance(status_payload, dict):
                return error(f"未找到运行记录: {run_id}", 404)
            if str(status_payload.get("run_id") or "") != str(run_id):
                return error(f"未找到运行记录: {run_id}", 404)

            with self._run_lock:
                cancel_event = self._run_cancel_events.get(run_id)
                if cancel_event:
                    cancel_event.set()

            return ok({"run_id": run_id, "cancelled": True})
        except Exception as e:
            return error(f"取消执行任务失败: {str(e)}", 500)

    def get_strategy_run_results(self, strategy_name: str, run_id: str):
        try:
            status_payload = self._read_status(strategy_name)
            if not isinstance(status_payload, dict):
                return error(f"未找到运行记录: {run_id}", 404)
            if str(status_payload.get("run_id") or "") != str(run_id):
                return error(f"未找到运行记录: {run_id}", 404)

            result_summary = status_payload.get("result_summary")
            if not isinstance(result_summary, dict):
                result_summary = {}

            return ok({
                "run_id": run_id,
                "result": {
                    "enum": result_summary.get("enum"),
                    "price": result_summary.get("price"),
                    "capital": result_summary.get("capital"),
                },
            })
        except Exception as e:
            return error(f"读取执行摘要结果失败: {str(e)}", 500)

    def get_strategy_compare_options(self, strategy_name: str):
        try:
            if not self._validate_strategy_exists(strategy_name):
                return error(f"策略不存在: {strategy_name}", 404)

            model = self._get_snapshot_model()
            rows = model.list_by_strategy(strategy_name, limit=100)
            versions = ["latest"]
            for row in rows or []:
                v = int(row.get("version") or 0)
                if v <= 0:
                    continue
                versions.append(self._format_version_id(v))

            deduped = []
            seen = set()
            for item in versions:
                if item in seen:
                    continue
                seen.add(item)
                deduped.append(item)

            return ok({"versions": deduped})
        except Exception as e:
            return error(f"读取对比版本选项失败: {str(e)}", 500)

    def get_strategy_reports(self, strategy_name: str, run_id: str, report_types_raw=None):
        try:
            if not self._validate_strategy_exists(strategy_name):
                return error(f"策略不存在: {strategy_name}", 404)
            requested_types, detail = self._parse_report_types(report_types_raw)
            if detail:
                return error(detail, 400)

            status_payload = self._read_status(strategy_name)
            if not isinstance(status_payload, dict):
                return error(f"未找到运行记录: {run_id}", 404)
            if str(status_payload.get("run_id") or "") != str(run_id):
                return error(f"未找到运行记录: {run_id}", 404)

            result_summary = status_payload.get("result_summary") if isinstance(status_payload.get("result_summary"), dict) else {}
            reports, available_tabs = self._build_reports_payload(result_summary, requested_types)
            return ok({
                "run_id": run_id,
                "reports": reports,
                "available_tabs": available_tabs,
            })
        except Exception as e:
            return error(f"读取报告主数据失败: {str(e)}", 500)

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

            status_payload = self._read_status(strategy_name)
            if not isinstance(status_payload, dict):
                return error(f"未找到运行记录: {run_id}", 404)
            if str(status_payload.get("run_id") or "") != str(run_id):
                return error(f"未找到运行记录: {run_id}", 404)

            safe_limit = max(1, min(int(limit or 10), 50))
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

            status_payload = self._read_status(strategy_name)
            if not isinstance(status_payload, dict):
                return error(f"未找到运行记录: {base_run_id}", 404)
            if str(status_payload.get("run_id") or "") != str(base_run_id):
                return error(f"未找到运行记录: {base_run_id}", 404)
            base_result_summary = (
                status_payload.get("result_summary")
                if isinstance(status_payload.get("result_summary"), dict)
                else {}
            )
            base_reports, _ = self._build_reports_payload(base_result_summary, requested_types)

            compare_row, compare_detail, resolved_compare_version = self._resolve_compare_snapshot(
                strategy_name,
                compare_version,
            )
            if compare_detail:
                return error(compare_detail, 404)
            compare_result_summary = (
                compare_row.get("result_summary")
                if isinstance(compare_row.get("result_summary"), dict)
                else {}
            )
            compare_reports, _ = self._build_reports_payload(compare_result_summary, requested_types)

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
            model = self._get_snapshot_model()
            rows = model.list_by_strategy(strategy_name, limit=100)
            versions = []
            for row in rows or []:
                v = int(row.get("version") or 0)
                if v <= 0:
                    continue
                versions.append({
                    "version_id": self._format_version_id(v),
                    "version": v,
                    "created_at": self._to_iso_or_empty(row.get("created_at")),
                    "updated_at": self._to_iso_or_empty(row.get("updated_at")),
                })
            return ok({
                "versions": versions,
                "retention": {"max_count": 100},
                "truncated": False,
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

            model = self._get_snapshot_model()
            row = model.load_by_strategy_version(strategy_name, v)
            if not row:
                return error(f"版本不存在: {version_id}", 404)

            settings_snapshot = row.get("settings_snapshot") or {}
            result_summary = row.get("result_summary")
            if not isinstance(result_summary, dict):
                result_summary = {}
            return ok({
                "version_id": self._format_version_id(v),
                "settings": settings_snapshot,
                "result_summary": result_summary,
            })
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
            row = model.load_by_strategy_version(strategy_name, v)
            if not row:
                return error(f"版本不存在: {version_id}", 404)

            settings_snapshot = row.get("settings_snapshot") or {}
            normalized_runtime_settings, detail = self._normalize_runtime_settings(
                strategy_name,
                settings_snapshot,
            )
            if normalized_runtime_settings is None:
                return error(detail, 422)
            api_settings = self._runtime_to_api_settings(normalized_runtime_settings)
            created = model.create_version(
                strategy_name=strategy_name,
                settings_snapshot=api_settings,
                result_summary={},
            )
            new_v = int(created.get("version") or 0)
            if new_v <= 0:
                return error("恢复工作台版本失败", 500)

            return ok({
                "restored": True,
                "strategy_name": strategy_name,
                "version_id": self._format_version_id(new_v),
                "restored_from_version_id": self._format_version_id(v),
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

            model = self._get_snapshot_model()
            created = model.create_version(
                strategy_name=strategy_name,
                settings_snapshot=self._runtime_to_api_settings(normalized_runtime_settings),
                result_summary={},
            )
            version = int(created.get("version") or 0)
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
    service = StrategyWorkbenchService()
    service._run_chain_worker(strategy_name, run_id, resolved_chain, cancel_event)
