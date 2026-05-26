#!/usr/bin/env python3
"""
统一回测起止日解析。

优先级（start）：
1. ``settings.sampling.start_date``
2. 样本 ``stock_ids`` 在 K 线 ``term`` 下的最早交易日
3. ``DateUtils.DEFAULT_START_DATE``

end：``settings.sampling.end_date`` 或调用方传入的 ``latest_completed_trading_date``。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.utils.date.date_utils import DateUtils

SOURCE_SETTINGS = "settings"
SOURCE_SAMPLE_EARLIEST_KLINE = "sample_earliest_kline"
SOURCE_DEFAULT = "default"
SOURCE_LATEST_TRADING_DAY = "latest_trading_day"
SOURCE_MISSING = "missing"
SOURCE_FLOW = "flow"

SOURCE_LABELS_ZH: Dict[str, str] = {
    SOURCE_SETTINGS: "策略配置",
    SOURCE_SAMPLE_EARLIEST_KLINE: "样本池最早 K 线",
    SOURCE_DEFAULT: "系统默认起点",
    SOURCE_LATEST_TRADING_DAY: "最新已完成交易日",
    SOURCE_FLOW: "本次运行",
    SOURCE_MISSING: "未解析",
}


@dataclass(frozen=True)
class ResolvedBacktestDate:
    date: str
    source: str


@dataclass(frozen=True)
class BacktestDateRange:
    start_date: str
    end_date: str
    start_source: str
    end_source: str

    def as_tuple(self) -> Tuple[str, str]:
        return self.start_date, self.end_date


def resolve_latest_completed_trading_date(data_manager: Any) -> str:
    """全系统 latest completed 统一读入口（``CalendarService.get_latest_completed_trading_date``）。"""
    cal_svc = _calendar_service(data_manager)
    if cal_svc is None:
        return ""
    try:
        return str(cal_svc.get_latest_completed_trading_date() or "").strip()
    except Exception:
        return ""


def _calendar_service(data_manager: Any) -> Any:
    if hasattr(data_manager, "service"):
        return data_manager.service.calendar
    if hasattr(data_manager, "stock"):
        return getattr(data_manager, "calendar", None) or data_manager.service.calendar
    return None


def kline_term_from_settings_view(view: StrategySettingsView) -> str:
    base = view.data.get("base_required_data")
    if not isinstance(base, dict):
        return "daily"
    p = StrategySettingsView.normalize_base_required_data(base).get("params") or {}
    term = str(p.get("term", "") or "").strip()
    return term or "daily"


def _load_earliest_kline_date(
    *,
    data_manager: Any,
    term: str,
    stock_ids: Sequence[str],
) -> str:
    if hasattr(data_manager, "service"):
        svc = data_manager.service.stock.kline
    elif hasattr(data_manager, "stock"):
        svc = data_manager.stock.kline
    else:
        return ""
    ids = [str(s).strip() for s in stock_ids if str(s).strip()]
    try:
        return str(svc.load_earliest_date(term, stock_ids=ids or None) or "").strip()
    except Exception:
        return ""


def resolve_backtest_start_date(
    *,
    settings_view: StrategySettingsView,
    stock_ids: Sequence[str],
    data_manager: Optional[Any] = None,
    kline_term: Optional[str] = None,
) -> ResolvedBacktestDate:
    configured = settings_view.start_date.strip()
    if configured:
        return ResolvedBacktestDate(configured, SOURCE_SETTINGS)

    term = (kline_term or kline_term_from_settings_view(settings_view)).strip() or "daily"
    if data_manager is not None:
        earliest = _load_earliest_kline_date(
            data_manager=data_manager,
            term=term,
            stock_ids=stock_ids,
        )
        if earliest:
            return ResolvedBacktestDate(earliest, SOURCE_SAMPLE_EARLIEST_KLINE)

    return ResolvedBacktestDate(DateUtils.DEFAULT_START_DATE, SOURCE_DEFAULT)


def resolve_backtest_end_date(
    *,
    settings_view: StrategySettingsView,
    latest_completed_trading_date: str,
) -> ResolvedBacktestDate:
    configured = settings_view.end_date.strip()
    latest = str(latest_completed_trading_date or "").strip()
    if configured:
        if latest and configured > latest:
            return ResolvedBacktestDate(latest, SOURCE_LATEST_TRADING_DAY)
        return ResolvedBacktestDate(configured, SOURCE_SETTINGS)
    if latest:
        return ResolvedBacktestDate(latest, SOURCE_LATEST_TRADING_DAY)
    return ResolvedBacktestDate("", SOURCE_MISSING)


def resolve_backtest_universe(
    *,
    list_svc: Any,
    settings_view: StrategySettingsView,
    latest_completed_trading_date: str = "",
    data_manager: Optional[Any] = None,
    kline_term: Optional[str] = None,
) -> Tuple[BacktestDateRange, List[Dict[str, Any]]]:
    """
    解析回测日历窗，并 ``list_svc.load(period_start=..., period_end=...)`` 取 PIT 参与者。

    未配置 ``start_date`` 时：先用默认起点拉 universe，再按样本最早 K 线收紧
    ``period_start`` 后必要时二次 ``load``。
    """
    dm = data_manager
    latest = str(latest_completed_trading_date or "").strip()
    if not latest:
        if dm is None:
            from core.modules.data_manager import DataManager

            dm = DataManager(is_verbose=False)
        latest = resolve_latest_completed_trading_date(dm)
    elif dm is None and not settings_view.start_date.strip():
        from core.modules.data_manager import DataManager

        dm = DataManager(is_verbose=False)

    end = resolve_backtest_end_date(
        settings_view=settings_view,
        latest_completed_trading_date=latest,
    )
    if not end.date:
        raise ValueError("无法解析回测结束日（请配置 sampling.end_date 或确保交易日历可用）")

    configured_start = settings_view.start_date.strip()
    provisional_start = configured_start or DateUtils.DEFAULT_START_DATE
    universe = list_svc.load(
        period_start=provisional_start,
        period_end=end.date,
    )
    bootstrap_ids = [str(r["id"]).strip() for r in universe if r.get("id")]

    period = resolve_backtest_date_range(
        settings_view=settings_view,
        stock_ids=bootstrap_ids,
        latest_completed_trading_date=latest,
        data_manager=dm,
        kline_term=kline_term,
    )
    if period.start_date != provisional_start:
        universe = list_svc.load(
            period_start=period.start_date,
            period_end=period.end_date,
        )
    return period, universe


def resolve_backtest_date_range(
    *,
    settings_view: StrategySettingsView,
    stock_ids: Sequence[str],
    latest_completed_trading_date: str = "",
    data_manager: Optional[Any] = None,
    kline_term: Optional[str] = None,
) -> BacktestDateRange:
    dm = data_manager
    latest = str(latest_completed_trading_date or "").strip()
    if not latest:
        if dm is None:
            from core.modules.data_manager import DataManager

            dm = DataManager(is_verbose=False)
        latest = resolve_latest_completed_trading_date(dm)
    elif dm is None and not settings_view.start_date.strip():
        from core.modules.data_manager import DataManager

        dm = DataManager(is_verbose=False)

    start = resolve_backtest_start_date(
        settings_view=settings_view,
        stock_ids=stock_ids,
        data_manager=dm,
        kline_term=kline_term,
    )
    end = resolve_backtest_end_date(
        settings_view=settings_view,
        latest_completed_trading_date=latest,
    )
    return BacktestDateRange(
        start_date=start.date,
        end_date=end.date,
        start_source=start.source,
        end_source=end.source,
    )


def backtest_period_to_dict(period: BacktestDateRange) -> Dict[str, str]:
    """工作台 ``result_report.*.backtest_period`` 与磁盘 metadata 共用形态。"""
    return {
        "start_date": str(period.start_date or "").strip(),
        "end_date": str(period.end_date or "").strip(),
        "start_source": str(period.start_source or "").strip(),
        "end_source": str(period.end_source or "").strip(),
    }


def resolve_backtest_period_payload(
    *,
    settings_view: Optional[StrategySettingsView],
    stock_ids: Sequence[str],
    data_manager: Optional[Any] = None,
    latest_completed_trading_date: str = "",
    fallback_start_date: str = "",
    fallback_end_date: str = "",
) -> Dict[str, str]:
    """
    解析带回溯来源的 ``backtest_period`` dict。

    无 ``settings_view`` 时仅用 ``fallback_*`` 日期（``start_source`` / ``end_source`` 为 ``flow``）。
    """
    if settings_view is None:
        return {
            "start_date": str(fallback_start_date or "").strip(),
            "end_date": str(fallback_end_date or "").strip(),
            "start_source": "flow" if fallback_start_date else "",
            "end_source": "flow" if fallback_end_date else "",
        }
    period = resolve_backtest_date_range(
        settings_view=settings_view,
        stock_ids=stock_ids,
        latest_completed_trading_date=latest_completed_trading_date,
        data_manager=data_manager,
    )
    return backtest_period_to_dict(period)


def format_backtest_date_display(ymd: str) -> str:
    s = str(ymd or "").strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return s


def _normalize_backtest_period_dict(raw: Any) -> Dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    start = str(raw.get("start_date") or "").strip()
    end = str(raw.get("end_date") or "").strip()
    if not (start and end):
        return {}
    return {
        "start_date": start,
        "end_date": end,
        "start_source": str(raw.get("start_source") or "").strip(),
        "end_source": str(raw.get("end_source") or "").strip(),
    }


def read_backtest_period_from_json_file(path: Path) -> Dict[str, str]:
    """从单个 JSON 摘要读取 ``backtest_period``（含顶层 ``start_date``/``end_date`` 兜底）。"""
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    bp = _normalize_backtest_period_dict(payload.get("backtest_period"))
    if bp:
        return bp
    nested = payload.get("session_summary")
    if isinstance(nested, dict):
        bp = _normalize_backtest_period_dict(nested.get("backtest_period"))
        if bp:
            return bp
    legacy_start = str(payload.get("start_date") or "").strip()
    legacy_end = str(payload.get("end_date") or "").strip()
    if legacy_start and legacy_end:
        return {
            "start_date": legacy_start,
            "end_date": legacy_end,
            "start_source": "",
            "end_source": "",
        }
    return {}


def read_backtest_period_from_enum_output_dir(output_dir: Path) -> Dict[str, str]:
    """从枚举产物目录读取 ``backtest_period``（``0_report_enum.json`` → ``0_metadata.json``）。"""
    base = Path(output_dir)
    for name in ("0_report_enum.json", "0_metadata.json"):
        bp = read_backtest_period_from_json_file(base / name)
        if bp:
            return bp
    return {}


def read_backtest_period_from_price_output_dir(output_version_dir: Path) -> Dict[str, str]:
    """价格因子模拟目录：``0_session_summary.json`` → ``0_metadata.json``。"""
    base = Path(output_version_dir)
    for name in ("0_session_summary.json", "0_metadata.json"):
        bp = read_backtest_period_from_json_file(base / name)
        if bp:
            return bp
    return {}


def read_backtest_period_from_capital_output_dir(output_version_dir: Path) -> Dict[str, str]:
    """资金模拟目录：``summary_strategy.json`` → ``0_metadata.json``。"""
    base = Path(output_version_dir)
    for name in ("summary_strategy.json", "0_metadata.json"):
        bp = read_backtest_period_from_json_file(base / name)
        if bp:
            return bp
    return {}


def backtest_period_console_lines(period: Optional[Dict[str, str]]) -> List[str]:
    """CLI / 日志用回测区间说明行。"""
    bp = _normalize_backtest_period_dict(period)
    if not bp:
        return []
    start_hint = SOURCE_LABELS_ZH.get(bp["start_source"], bp["start_source"] or "—")
    end_hint = SOURCE_LABELS_ZH.get(bp["end_source"], bp["end_source"] or "—")
    return [
        "📅 回测区间: "
        f"{format_backtest_date_display(bp['start_date'])} — "
        f"{format_backtest_date_display(bp['end_date'])}",
        f"   开始日来源: {start_hint}",
        f"   结束日来源: {end_hint}",
    ]


__all__ = [
    "BacktestDateRange",
    "ResolvedBacktestDate",
    "backtest_period_console_lines",
    "backtest_period_to_dict",
    "format_backtest_date_display",
    "read_backtest_period_from_capital_output_dir",
    "read_backtest_period_from_enum_output_dir",
    "read_backtest_period_from_json_file",
    "read_backtest_period_from_price_output_dir",
    "SOURCE_DEFAULT",
    "SOURCE_LATEST_TRADING_DAY",
    "SOURCE_SAMPLE_EARLIEST_KLINE",
    "SOURCE_SETTINGS",
    "kline_term_from_settings_view",
    "resolve_backtest_universe",
    "resolve_backtest_date_range",
    "resolve_backtest_end_date",
    "resolve_backtest_period_payload",
    "resolve_backtest_start_date",
    "resolve_latest_completed_trading_date",
]
