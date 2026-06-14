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
    resolve_backtest_period_payload,
    resolve_latest_completed_trading_date,
)
from core.modules.strategy.launcher.workbench import (
    _STOCK_REF_FILENAMES,
    fetch_workbench_by_version,
)
from core.modules.strategy.engines.shared.data_classes.investment_state import (
    InvestmentLifecycle,
    InvestmentOutcome,
    ScanSignalPhase,
)
from core.modules.strategy.services.data.output.enumerator_output_service import (
    STOCK_REF_FILENAME,
)
from core.modules.strategy.engines.shared.report_base import ReportBase
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


def _price_output_dir_candidates(strategy_name: str, row: Dict[str, Any]) -> List[str]:
    """与 ``result_report.price_factor.output_version_run`` 一致的价格产物目录候选列表。"""
    from core.infra.project_context.path_manager import PathManager

    base = PathManager.strategy_simulation_price(strategy_name)
    candidates_dirs: List[str] = []

    rr = row.get("result_report") or {}
    price_raw = rr.get("price_factor")
    if isinstance(price_raw, dict):
        run = price_raw.get("output_version_run")
        if isinstance(run, dict):
            out_d = str(run.get("output_version_dir") or "").strip()
            if out_d:
                candidates_dirs.append(out_d)
            vid = run.get("output_version_id")
            if vid is not None:
                try:
                    vs = str(int(vid))
                    if vs not in candidates_dirs:
                        candidates_dirs.append(vs)
                except (TypeError, ValueError):
                    pass
        vid_top = price_raw.get("output_version_id")
        if vid_top is not None:
            try:
                vs = str(int(vid_top))
                if vs not in candidates_dirs:
                    candidates_dirs.append(vs)
            except (TypeError, ValueError):
                pass

    seen: set[str] = set()
    uniq: List[str] = []
    for d in candidates_dirs:
        if d and d not in seen:
            seen.add(d)
            uniq.append(d)
    return [str(base / d) for d in uniq]


def _resolve_price_output_dir(
    strategy_name: str,
    row: Dict[str, Any],
    stock_id: str,
) -> Tuple[Optional[Path], str]:
    sid = str(stock_id or "").strip()
    for dir_path in _price_output_dir_candidates(strategy_name, row):
        p = Path(dir_path)
        if sid and (p / f"{sid}.json").is_file():
            return p, p.name
        if (p / "0_session_summary.json").is_file():
            return p, p.name
    return None, ""


def _read_price_stock_summary(output_dir: Path, stock_id: str) -> Optional[Dict[str, Any]]:
    path = output_dir / f"{stock_id}.json"
    if not path.is_file():
        return None
    try:
        import json

        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            return raw
    except Exception:
        logger.exception("读取价格回测单股 JSON 失败: %s", path)
    return None


def _is_price_target_win(target: Dict[str, Any]) -> bool:
    weighted = _float_or_none(target.get("weighted_profit"))
    if weighted is not None and weighted != 0:
        return weighted > 0
    profit = _float_or_none(target.get("profit"))
    if profit is not None and profit != 0:
        return profit > 0
    roi = _float_or_none(target.get("profit_ratio"))
    if roi is not None and roi != 0:
        return roi > 0
    target_type = str(target.get("target_type") or "").lower()
    if target_type == "take_profit":
        return True
    if target_type == "stop_loss":
        return False
    name = str(target.get("name") or "").lower()
    if "win" in name:
        return True
    if "loss" in name:
        return False
    return False


def _build_price_markers(
    investments: List[Dict[str, Any]],
    by_date: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """价格回测标记：买入锚在实际 buy_date，目标锚在完成日 sell_date。"""
    markers: List[Dict[str, Any]] = []
    for inv in investments:
        if not isinstance(inv, dict):
            continue
        buy_date = DateUtils.normalize_str(str(inv.get("buy_date") or ""))
        trigger_date = DateUtils.normalize_str(str(inv.get("trigger_date") or ""))
        if buy_date and buy_date in by_date:
            bar = by_date[buy_date]
            markers.append(
                {
                    "date": buy_date,
                    "price": _round_price(_float_or_none(bar.get("low"))),
                    "type": "buy",
                    "label": "买入",
                    "detail": {
                        "opportunity_id": str(inv.get("opportunity_id") or "").strip(),
                        "trigger_date": trigger_date,
                        "buy_date": buy_date,
                        "buy_price": _round_price(_float_or_none(inv.get("buy_price"))),
                        "lifecycle": str(inv.get("lifecycle") or "").strip(),
                        "outcome": str(inv.get("outcome") or "").strip(),
                    },
                }
            )

        for tgt in inv.get("completed_targets") or []:
            if not isinstance(tgt, dict):
                continue
            sell_date = DateUtils.normalize_str(str(tgt.get("sell_date") or ""))
            if not sell_date or sell_date not in by_date:
                continue
            bar = by_date[sell_date]
            is_win = _is_price_target_win(tgt)
            target_detail: Dict[str, Any] = {
                "target_name": str(tgt.get("name") or "").strip(),
                "sell_date": sell_date,
                "sell_price": _round_price(_float_or_none(tgt.get("sell_price"))),
                "profit": _round_price(
                    _float_or_none(tgt.get("weighted_profit") or tgt.get("profit"))
                ),
                "profit_ratio": _round_price(_float_or_none(tgt.get("profit_ratio"))),
                "target_type": str(tgt.get("target_type") or "").strip(),
            }
            markers.append(
                {
                    "date": sell_date,
                    "price": _round_price(_float_or_none(bar.get("high"))),
                    "type": "target_win" if is_win else "target_loss",
                    "label": "目标胜" if is_win else "目标负",
                    "detail": target_detail,
                }
            )
    return markers


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
    report_slot: Optional[str] = None,
) -> Dict[str, str]:
    rr = row.get("result_report") or {}
    slot_keys: List[str] = []
    if report_slot == "price":
        slot_keys = ["price_factor"]
    elif report_slot == "enum":
        slot_keys = ["enum"]
    else:
        slot_keys = ["enum", "price_factor"]
    for key in slot_keys:
        raw = rr.get(key)
        if isinstance(raw, dict):
            bp = _normalize_backtest_period_dict(raw.get("backtest_period"))
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
    term = (
        settings_view.base_kline_term
        if settings_view is not None
        else "daily"
    )
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


def _collect_target_tradability_for_stock(output_dir: Path, stock_id: str) -> Dict[str, int]:
    """仅统计该股 ``{stock_id}_targets.csv`` 的卖出可成交性（与全目录汇总区分）。"""
    from core.modules.strategy.engines.shared.helpers.tradability import row_sell_at_limit_down

    counts = {
        "sell_tradability_sample_count": 0,
        "sell_at_limit_down_count": 0,
    }
    path = output_dir / f"{stock_id}_targets.csv"
    if not path.is_file():
        return counts
    try:
        for row in read_csv_to_dicts(path):
            if not isinstance(row, dict):
                continue
            flagged = row_sell_at_limit_down(row)
            if flagged is None:
                continue
            counts["sell_tradability_sample_count"] += 1
            if flagged:
                counts["sell_at_limit_down_count"] += 1
    except Exception:
        logger.exception("读取单股 targets 可成交性失败: %s", path)
    return counts


def _is_enum_opportunity_goal_completed(row: Dict[str, Any]) -> bool:
    """
    「机会完成」：模拟期内按规则走完目标后结案。

    与 ``EnumeratorReport`` / worker ``report_completed_count`` 一致：
    ``enumeration_end`` / ``backtest_end`` 强制平仓算未完成；``open/active/testing`` 亦未完成。
    """
    sell_reason = str(row.get("sell_reason") or "").lower()
    if sell_reason in {"enumeration_end", "backtest_end"}:
        return False
    lifecycle = str(row.get("lifecycle") or "").lower()
    phase = str(row.get("signal_phase") or "").lower()
    if lifecycle == InvestmentLifecycle.OPEN.value or phase in {
        ScanSignalPhase.ACTIVE.value,
        ScanSignalPhase.TESTING.value,
    }:
        return False
    return lifecycle == InvestmentLifecycle.COMPLETE.value


def _enum_opportunity_win_stats(opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    「机会胜率」：仅在「已完成」机会中，ROI 为正（win）与为负（loss）的占比。

    未完成（回测结束强制平仓等）不参与胜率分母。
    """
    wins = 0
    losses = 0
    for row in opportunities:
        if not isinstance(row, dict) or not _is_enum_opportunity_goal_completed(row):
            continue
        outcome = str(row.get("outcome") or "").lower()
        if outcome == InvestmentOutcome.WIN.value:
            wins += 1
        elif outcome == InvestmentOutcome.LOSS.value:
            losses += 1
        else:
            roi = _float_or_none(row.get("roi"))
            if roi is None:
                continue
            if roi > 0:
                wins += 1
            elif roi < 0:
                losses += 1
    sample = wins + losses
    win_rate = round(ReportBase.safe_div(wins, sample) * 100.0, 1) if sample else 0.0
    return {
        "winCount": wins,
        "lossCount": losses,
        "winRateSampleCount": sample,
        "winRate": win_rate,
    }


def _build_stock_enum_report_metrics(
    stock_id: str,
    opportunities: List[Dict[str, Any]],
    output_dir: Path,
) -> Dict[str, Any]:
    """单股枚举报告指标，与 ``EnumeratorReport.to_bff_payload`` 的 ``enumMetrics`` 同形。"""
    from core.modules.strategy.engines.simulator.enumerator.data_classes.report import (
        EnumeratorReport,
    )

    tagged: List[Dict[str, Any]] = []
    for row in opportunities:
        if not isinstance(row, dict):
            continue
        payload = dict(row)
        payload["stock_id"] = stock_id
        tagged.append(payload)

    target_trad = _collect_target_tradability_for_stock(output_dir, stock_id)
    extra = (
        target_trad
        if int(target_trad.get("sell_tradability_sample_count") or 0) > 0
        else None
    )
    report = EnumeratorReport.from_opportunities_with_total_stocks(
        opportunities=tagged,
        total_stocks_hint=1,
        target_tradability=extra,
    )
    bff = report.to_bff_payload(include_stock_rows=False)
    metrics = bff.get("enumMetrics")
    if not isinstance(metrics, dict):
        return {}
    metrics.update(_enum_opportunity_win_stats(tagged))
    return metrics


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

    enum：读 ``{stock}_opportunities.csv`` + DB K 线；price：读 ``{stock}.json`` 投资与目标标记。
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

    if normalized_step not in ("enum", "price"):
        return {
            **common,
            "step_ready": False,
            "detail_available": False,
            "message": "该步骤单股详情尚未开放（MVP 仅枚举与价格回测）",
            "stock_name": _stock_display_name(sid, row, None),
            "backtest_period": _backtest_period_for_row(row, stock_id=sid, data_manager=DataManager()),
            "candles": [],
            "markers": [],
            "indicator_series": [],
            "report": {"placeholder": True, "message": "即将支持"},
        }

    if normalized_step == "price":
        output_dir, _resolved_name = _resolve_price_output_dir(name, row, sid)
        stock_name = _stock_display_name(sid, row, None)
        backtest_period = _backtest_period_for_row(
            row, stock_id=sid, data_manager=DataManager(), report_slot="price"
        )
        if output_dir is None:
            return {
                **common,
                "step_ready": True,
                "detail_available": False,
                "message": "价格回测产物目录不可用，请重新执行价格回测",
                "stock_name": stock_name,
                "backtest_period": backtest_period,
                "candles": [],
                "markers": [],
                "indicator_series": [],
                "report": {"available": False, "message": "价格回测产物目录不可用"},
            }

        stock_summary = _read_price_stock_summary(output_dir, sid)
        investments = (
            list(stock_summary.get("investments") or [])
            if isinstance(stock_summary, dict)
            else []
        )
        if not investments:
            return {
                **common,
                "step_ready": True,
                "detail_available": False,
                "message": "未找到该股的价格回测交易记录，请重新执行价格回测",
                "stock_name": stock_name,
                "backtest_period": backtest_period,
                "candles": [],
                "markers": [],
                "indicator_series": [],
                "report": {"available": False, "message": "未找到该股的价格回测交易记录"},
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
        markers = _build_price_markers(investments, by_date)

        kline_params: Dict[str, str] = {}
        if settings_view is not None:
            p = settings_view.resolved_base_required_data.get("params") or {}
            kline_params = {
                "data_id": str(settings_view.resolved_base_required_data.get("data_id") or ""),
                "term": settings_view.base_kline_term,
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
            "report": {"available": False, "message": "价格回测单股指标报告即将支持"},
        }

    output_dir, _resolved_name = _resolve_enum_output_dir(name, row)
    stock_name = _stock_display_name(sid, row, output_dir)
    backtest_period = _backtest_period_for_row(
        row, stock_id=sid, data_manager=DataManager(), report_slot="enum"
    )

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
            "report": {"available": False, "message": "枚举产物目录不可用"},
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
            "report": {"available": False, "message": "未找到该股的枚举机会文件"},
        }

    enum_metrics = _build_stock_enum_report_metrics(sid, opportunities, output_dir)

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
                    "lifecycle": str(opp.get("lifecycle") or "").strip(),
                    "outcome": str(opp.get("outcome") or "").strip(),
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
        "report": {
            "available": bool(enum_metrics),
            "enumMetrics": enum_metrics,
        },
    }
