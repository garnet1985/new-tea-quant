"""工作台单股详情：K 线（回测区间）+ 步骤 markers（V2-07c，enum MVP）。"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.modules.indicator.indicator_service import IndicatorService

from core.modules.data_manager import DataManager
from core.modules.strategy.engines.shared.data_classes.strategy_settings.dict_view_settings import (
    StrategySettingsView,
)
from core.modules.strategy.engines.shared.helpers.backtest_date_resolve import (
    _normalize_backtest_period_dict,
    kline_term_from_settings_view,
    resolve_backtest_period_payload,
    resolve_latest_completed_trading_date,
)
from core.modules.strategy.launcher.workbench import (
    _STOCK_REF_FILENAMES,
    fetch_workbench_by_version,
)
from core.modules.strategy.services.data.output.enumerator_output_service import (
    STOCK_REF_FILENAME,
)
from core.utils.date.date_utils import DateUtils
from core.utils.io.csv_io import read_csv_to_dicts

logger = logging.getLogger(__name__)

_OSCILLATOR_INDICATORS = frozenset(
    {"rsi", "stoch", "stochrsi", "willr", "mfi", "cmo", "cci", "uo", "aroon"}
)

_INDICATOR_LINE_COLORS = (
    "#64B5F6",
    "#BA68C8",
    "#4DD0E1",
    "#AED581",
    "#FF8A65",
    "#F06292",
)


def _enum_output_dir_candidates(strategy_name: str, row: Dict[str, Any]) -> List[str]:
    """与 ``build_step_report_ref_message`` 一致的枚举产物目录候选列表。"""
    from core.infra.project_context.path_manager import PathManager

    version = int(row.get("version") or 0)
    base = PathManager.strategy_simulation_enum(strategy_name)
    candidates_dirs: List[str] = []

    rr = row.get("result_report") or {}
    enum_raw = rr.get("enum")
    if isinstance(enum_raw, dict):
        out_d = str(enum_raw.get("enumerator_output_dir") or "").strip()
        if out_d:
            candidates_dirs.append(out_d)
        vid = enum_raw.get("output_version_id")
        if vid is not None:
            try:
                vs = str(int(vid))
                if vs not in candidates_dirs:
                    candidates_dirs.append(vs)
            except (TypeError, ValueError):
                pass

    if version > 0:
        sid_s = str(int(version))
        if sid_s not in candidates_dirs:
            candidates_dirs.append(sid_s)

    seen: set[str] = set()
    uniq: List[str] = []
    for d in candidates_dirs:
        if d and d not in seen:
            seen.add(d)
            uniq.append(d)
    return [str(base / d) for d in uniq]


def _resolve_enum_output_dir(strategy_name: str, row: Dict[str, Any]) -> Tuple[Optional[Path], str]:
    for dir_path in _enum_output_dir_candidates(strategy_name, row):
        p = Path(dir_path)
        for fname in _STOCK_REF_FILENAMES:
            if (p / fname).is_file():
                return p, p.name
    return None, ""


def _settings_view_from_row(row: Dict[str, Any]) -> Optional[StrategySettingsView]:
    snap = row.get("settings_snapshot")
    if not isinstance(snap, dict) or not snap:
        return None
    try:
        return StrategySettingsView.from_dict(snap)
    except Exception:
        return None


def _backtest_period_for_row(
    row: Dict[str, Any],
    *,
    stock_id: str,
    data_manager: Any,
) -> Dict[str, str]:
    rr = row.get("result_report") or {}
    enum_raw = rr.get("enum")
    if isinstance(enum_raw, dict):
        bp = _normalize_backtest_period_dict(enum_raw.get("backtest_period"))
        if bp:
            return bp

    view = _settings_view_from_row(row)
    if view is None:
        return {}
    latest = resolve_latest_completed_trading_date(data_manager)
    return resolve_backtest_period_payload(
        settings_view=view,
        stock_ids=[stock_id],
        data_manager=data_manager,
        latest_completed_trading_date=latest,
    )


def _round_price(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), 2)


def _load_stock_klines(
    kline_svc: Any,
    *,
    stock_id: str,
    term: str,
    start: str,
    end: str,
    adjust: str,
) -> List[Dict[str, Any]]:
    """按复权口径加载；``open/high/low/close`` 即为该口径下的价格。"""
    adj = str(adjust or "qfq").strip().lower() or "qfq"
    if adj == "qfq":
        return list(
            kline_svc.load_qfq_split(
                stock_id,
                term=term,
                start_date=start,
                end_date=end,
            )
            or []
        )
    return list(
        kline_svc.load_raw(
            stock_id,
            term=term,
            start_date=start,
            end_date=end,
        )
        or []
    )


def _api_candle_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """BFF 对外 K 线：仅 ``date + OHLC``。"""
    date_key = DateUtils.normalize_str(str(row.get("date") or ""))
    if not date_key:
        return None
    open_ = _round_price(_float_or_none(row.get("open")))
    close = _round_price(_float_or_none(row.get("close")))
    if open_ is None or close is None:
        return None
    high = _round_price(_float_or_none(row.get("high")))
    low = _round_price(_float_or_none(row.get("low")))
    if high is None:
        high = close
    if low is None:
        low = close
    if high is not None and low is not None and high < low:
        high, low = low, high
    return {
        "date": date_key,
        "open": open_,
        "close": close,
        "high": high,
        "low": low,
    }


def _build_indicator_field_name(name: str, params: Dict[str, Any]) -> str:
    name = str(name or "").lower()
    length = params.get("length")
    if length is not None:
        try:
            return f"{name}{int(length)}"
        except (TypeError, ValueError):
            pass
    parts = [name]
    for key in sorted(params.keys()):
        value = params[key]
        if isinstance(value, (int, float, str)):
            parts.append(f"{key}{value}")
    return "_".join(parts)


def _indicator_panel(name: str) -> str:
    base = str(name or "").lower().split("_")[0]
    return "oscillator" if base in _OSCILLATOR_INDICATORS else "overlay"


def _indicator_label(name: str, params: Dict[str, Any], *, suffix: str = "") -> str:
    base = str(name or "").upper()
    length = params.get("length")
    if suffix:
        return f"{base} {suffix.upper()}({length})" if length is not None else f"{base} {suffix.upper()}"
    return f"{base}({int(length)})" if length is not None else base


def _float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        fv = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(fv) or math.isinf(fv):
        return None
    return fv


def _align_indicator_values(values: List[Any], size: int) -> List[Optional[float]]:
    out: List[Optional[float]] = []
    for idx in range(size):
        raw = values[idx] if idx < len(values) else None
        out.append(_round_price(_float_or_none(raw)))
    return out


def _compute_indicator_series(
    klines: List[Dict[str, Any]],
    indicators_cfg: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not klines or not indicators_cfg:
        return []

    series_out: List[Dict[str, Any]] = []
    color_idx = 0
    try:
        batch = IndicatorService.compute_batch(klines, indicators_cfg)
    except Exception:
        logger.exception("单股指标批量计算失败")
        return []

    for name, cfg, result in batch:
        if not isinstance(cfg, dict):
            cfg = {}
        if isinstance(result, list):
            rows = [
                {
                    "key": _build_indicator_field_name(name, cfg),
                    "label": _indicator_label(name, cfg),
                    "panel": _indicator_panel(name),
                    "color": _INDICATOR_LINE_COLORS[color_idx % len(_INDICATOR_LINE_COLORS)],
                    "data": _align_indicator_values(result, len(klines)),
                }
            ]
            color_idx += 1
            series_out.extend(rows)
            continue
        if isinstance(result, dict):
            for sub_key, sub_values in result.items():
                if not isinstance(sub_values, list):
                    continue
                rows = [
                    {
                        "key": _build_indicator_field_name(f"{name}_{sub_key}", cfg),
                        "label": _indicator_label(name, cfg, suffix=str(sub_key)),
                        "panel": _indicator_panel(name),
                        "color": _INDICATOR_LINE_COLORS[color_idx % len(_INDICATOR_LINE_COLORS)],
                        "data": _align_indicator_values(sub_values, len(klines)),
                    }
                ]
                color_idx += 1
                series_out.extend(rows)

    return [row for row in series_out if any(v is not None for v in row.get("data") or [])]


def _load_candles_and_indicators(
    *,
    stock_id: str,
    settings_view: StrategySettingsView,
    backtest_period: Dict[str, str],
    data_manager: Any,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    base = settings_view.resolved_base_required_data
    params = base.get("params") or {}
    term = str(params.get("term") or kline_term_from_settings_view(settings_view) or "daily").strip()
    adjust = str(params.get("adjust") or settings_view.adjust_type or "qfq").strip() or "qfq"
    start = str(backtest_period.get("start_date") or "").strip()
    end = str(backtest_period.get("end_date") or "").strip()
    if not start or not end:
        return [], []

    kline_svc = data_manager.service.stock.kline
    rows = _load_stock_klines(
        kline_svc,
        stock_id=stock_id,
        term=term,
        start=start,
        end=end,
        adjust=adjust,
    )
    candles = [c for row in rows if (c := _api_candle_row(row)) is not None]

    indicators_cfg = settings_view.indicators if settings_view is not None else {}
    indicator_series = _compute_indicator_series(rows, indicators_cfg)
    return candles, indicator_series


def _candle_index_by_date(candles: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for c in candles:
        d = str(c.get("date") or "").strip()
        if d:
            out[d] = c
    return out


def _read_enum_opportunities(output_dir: Path, stock_id: str) -> List[Dict[str, Any]]:
    path = output_dir / f"{stock_id}_opportunities.csv"
    if not path.is_file():
        return []
    try:
        rows = read_csv_to_dicts(path)
    except Exception:
        logger.exception("读取枚举机会 CSV 失败: %s", path)
        return []
    return [dict(r) for r in rows if isinstance(r, dict)]


def _stock_display_name(
    stock_id: str,
    row: Dict[str, Any],
    output_dir: Optional[Path],
) -> str:
    if output_dir is not None:
        ref_path = output_dir / STOCK_REF_FILENAME
        if ref_path.is_file():
            try:
                import json

                raw = json.loads(ref_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    payload = raw.get(stock_id)
                    if isinstance(payload, dict):
                        nm = str(payload.get("stock_name") or "").strip()
                        if nm and nm != stock_id:
                            return nm
            except Exception:
                pass
    try:
        dm = DataManager()
        rec = dm.service.stock.list.load_single(stock_id)
        if isinstance(rec, dict):
            nm = str(rec.get("name") or "").strip()
            if nm:
                return nm
    except Exception:
        pass
    return stock_id


def build_stock_detail_message(
    *,
    strategy_name: str,
    normalized_step: str,
    version: int,
    stock_id: str,
) -> Optional[Dict[str, Any]]:
    """
    单股详情正文。快照不存在 → ``None``（路由 404）。

    enum：读 ``{stock}_opportunities.csv`` + DB K 线；price/capital MVP 返回 ``step_ready=False``。
    """
    name = str(strategy_name or "").strip()
    sid = str(stock_id or "").strip()
    if not name or version <= 0 or not sid:
        return None

    row = fetch_workbench_by_version(name, int(version))
    if not row:
        return None

    common = {
        "version_id": f"v{int(version)}",
        "strategy_name": name,
        "step": normalized_step,
        "stock_id": sid,
    }

    if normalized_step != "enum":
        return {
            **common,
            "step_ready": False,
            "detail_available": False,
            "message": "该步骤单股详情尚未开放（MVP 仅枚举）",
            "stock_name": _stock_display_name(sid, row, None),
            "backtest_period": _backtest_period_for_row(row, stock_id=sid, data_manager=DataManager()),
            "candles": [],
            "markers": [],
            "indicator_series": [],
            "report": {"placeholder": True, "message": "即将支持"},
        }

    output_dir, _resolved_name = _resolve_enum_output_dir(name, row)
    stock_name = _stock_display_name(sid, row, output_dir)
    backtest_period = _backtest_period_for_row(row, stock_id=sid, data_manager=DataManager())

    if output_dir is None:
        return {
            **common,
            "step_ready": True,
            "detail_available": False,
            "message": "枚举产物目录不可用，请重新执行枚举",
            "stock_name": stock_name,
            "backtest_period": backtest_period,
            "candles": [],
            "markers": [],
            "indicator_series": [],
            "report": {"placeholder": True, "message": "逐股明细列待定义"},
        }

    opportunities = _read_enum_opportunities(output_dir, sid)
    if not opportunities:
        return {
            **common,
            "step_ready": True,
            "detail_available": False,
            "message": "未找到该股的枚举机会文件，请重新执行枚举",
            "stock_name": stock_name,
            "backtest_period": backtest_period,
            "candles": [],
            "markers": [],
            "indicator_series": [],
            "report": {"placeholder": True, "message": "逐股明细列待定义"},
        }

    settings_view = _settings_view_from_row(row)
    candles: List[Dict[str, Any]] = []
    indicator_series: List[Dict[str, Any]] = []
    if settings_view is not None:
        try:
            candles, indicator_series = _load_candles_and_indicators(
                stock_id=sid,
                settings_view=settings_view,
                backtest_period=backtest_period,
                data_manager=DataManager(),
            )
        except Exception:
            logger.exception("加载单股 K 线失败: %s", sid)

    by_date = _candle_index_by_date(candles)
    markers: List[Dict[str, Any]] = []
    seen_dates: set[str] = set()
    for opp in opportunities:
        trigger = DateUtils.normalize_str(str(opp.get("trigger_date") or ""))
        if not trigger or trigger in seen_dates:
            continue
        seen_dates.add(trigger)
        bar = by_date.get(trigger)
        chart_close = _round_price(_float_or_none(bar.get("close"))) if bar else None
        chart_high = _round_price(_float_or_none(bar.get("high"))) if bar else None
        marker_price = chart_high if chart_high is not None else chart_close
        if marker_price is None:
            continue
        markers.append(
            {
                "date": trigger,
                "price": marker_price,
                "type": "opportunity",
                "label": "机会",
                "detail": {
                    "opportunity_id": str(opp.get("opportunity_id") or "").strip(),
                    "trigger_date": trigger,
                    "chart_close": chart_close,
                    "engine_trigger_price": _round_price(_float_or_none(opp.get("trigger_price"))),
                    "buy_date": str(opp.get("buy_date") or "").strip(),
                    "sell_date": str(opp.get("sell_date") or "").strip(),
                    "status": str(opp.get("status") or "").strip(),
                    "sell_reason": str(opp.get("sell_reason") or "").strip(),
                },
            }
        )

    kline_params: Dict[str, str] = {}
    if settings_view is not None:
        p = settings_view.resolved_base_required_data.get("params") or {}
        kline_params = {
            "term": str(p.get("term") or "daily").strip(),
            "adjust": str(p.get("adjust") or "qfq").strip(),
        }

    return {
        **common,
        "step_ready": True,
        "detail_available": bool(candles),
        "message": "" if candles else "K 线数据为空，请检查数据导入与回测区间",
        "stock_name": stock_name,
        "backtest_period": backtest_period,
        "kline_params": kline_params,
        "candles": candles,
        "markers": markers,
        "indicator_series": indicator_series,
        "report": {"placeholder": True, "message": "逐股明细列待定义"},
    }
