"""Strategy workbench service logic."""

import json
import threading
import time
from datetime import datetime, timezone
from uuid import uuid4

from core.infra.project_context.config_manager import ConfigManager
from core.infra.project_context.path_manager import PathManager
from core.tables.ui_bff.strategy_workbench_snapshot.model import SysStrategyWorkbenchSnapshotModel
from core.ui.bff.shared.file_ops import atomic_write_text, backup_file
from core.ui.bff.shared.response import error, ok


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
        if step == StrategyWorkbenchService.STEP_ENUM:
            return {
                "opportunities": 0,
                "totalStocks": 0,
                "triggerStocks": 0,
                "completedCount": 0,
                "unfinishedCount": 0,
                "completionRate": 0.0,
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
                opportunities = int((enum_result or {}).get("opportunities") or 0)
                payload = (
                    {
                        "opportunities": opportunities,
                        "totalStocks": int((enum_result or {}).get("totalStocks") or 0),
                        "triggerStocks": int((enum_result or {}).get("triggerStocks") or 0),
                        "completedCount": int((enum_result or {}).get("completedCount") or 0),
                        "unfinishedCount": int((enum_result or {}).get("unfinishedCount") or 0),
                        "completionRate": float((enum_result or {}).get("completionRate") or 0.0),
                    }
                    if opportunities > 0
                    else None
                )
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

    def _run_chain_worker(self, strategy_name: str, run_id: str, resolved_chain: list):
        cancel_event = None
        with self._run_lock:
            cancel_event = self._run_cancel_events.get(run_id)

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
            from core.modules.strategy.helpers.strategy_discovery_helper import StrategyDiscoveryHelper

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
            from core.modules.strategy.engines.shared.data_classes.strategy_settings.capital_allocation_settings import (
                _VALID_MODES,
            )

            ordered = (
                ("equal_capital", "每个机会均等资金买入"),
                ("equal_shares", "每个机会均等股数买入"),
                ("kelly", "凯莉公式"),
                ("custom", "自定义"),
            )
            options = [{"value": v, "label": lbl} for v, lbl in ordered if v in _VALID_MODES]
            missing = _VALID_MODES - {o["value"] for o in options}
            if missing:
                for v in sorted(missing):
                    options.append({"value": v, "label": v})

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
            from core.modules.strategy.engines.shared.data_classes.strategy_settings.sampling_settings import (
                KNOWN_STRATEGIES,
            )

            ordered = (
                ("continuous", "连续采样（默认）"),
                ("uniform", "均匀采样"),
                ("stratified", "分层采样"),
                ("random", "随机采样"),
                ("pool", "指定股票池采样"),
                ("blacklist", "排除黑名单采样"),
            )
            options = [{"value": v, "label": lbl} for v, lbl in ordered if v in KNOWN_STRATEGIES]
            missing = KNOWN_STRATEGIES - {o["value"] for o in options}
            if missing:
                for v in sorted(missing):
                    options.append({"value": v, "label": v})

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

    def _api_to_runtime_settings(self, api_settings):
        if not isinstance(api_settings, dict):
            return {}
        runtime = dict(api_settings)
        meta = runtime.get("meta")
        if isinstance(meta, dict):
            runtime["name"] = meta.get("name", runtime.get("name", ""))
            runtime["description"] = meta.get("description", runtime.get("description", ""))
            runtime["is_enabled"] = bool(meta.get("is_enabled", runtime.get("is_enabled", False)))
        return runtime

    def get_strategy_settings(self, strategy_name: str):
        try:
            strategy_dir = PathManager.strategy(strategy_name)
            settings_file = PathManager.strategy_settings(strategy_name)
            if not strategy_dir.exists() or not strategy_dir.is_dir():
                return error(f"策略不存在: {strategy_name}", 404)
            if not settings_file.exists():
                return error(f"策略缺少 settings.py: {strategy_name}", 404)

            runtime_settings = ConfigManager.load_python(settings_file, var_name="settings")
            if not isinstance(runtime_settings, dict):
                return error(f"策略 settings 无效: {strategy_name}", 500)

            return ok({
                "strategy_name": strategy_name,
                "settings": self._runtime_to_api_settings(runtime_settings),
            })
        except Exception as e:
            return error(f"读取策略 settings 失败: {str(e)}", 500)

    def save_strategy_settings(self, strategy_name: str, payload: dict):
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
                "saved": True,
            })
        except Exception as e:
            return error(f"保存策略 settings 失败: {str(e)}", 500)

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
                "updated_at": self._now_iso(),
            }
            self._write_status(strategy_name, status_payload)

            with self._run_lock:
                self._run_cancel_events[run_id] = threading.Event()
                worker = threading.Thread(
                    target=self._run_chain_worker,
                    args=(strategy_name, run_id, resolved_chain),
                    daemon=True,
                )
                worker.start()

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

            return ok({
                "run_id": run_id,
                "state": status_payload.get("state", self.RUN_STATE_RUNNING),
                "running_step": status_payload.get("running_step", ""),
                "progress_pct": int(status_payload.get("progress_pct") or 0),
                "step_status": step_status,
                "result_summary": status_payload.get("result_summary") or {},
                "updated_at": status_payload.get("updated_at", self._now_iso()),
            })
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
            return ok({
                "version_id": self._format_version_id(v),
                "settings": settings_snapshot,
            })
        except Exception as e:
            return error(f"读取版本详情失败: {str(e)}", 500)

    def restore_strategy_version(self, strategy_name: str, version_id: str):
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
            self._save_runtime_settings_file(strategy_name, normalized_runtime_settings)

            return ok({
                "restored": True,
                "strategy_name": strategy_name,
                "version_id": self._format_version_id(v),
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
