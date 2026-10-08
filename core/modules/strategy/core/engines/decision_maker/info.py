"""决策者 ``info``：截至 D 的最近 N 根开市日（K 线 + 策略声明指标）。

本文件:
- load_info_table: 懒加载；小 LRU 缓存在引擎侧
  边界: 窗口右端含 D；不写 session.json；图画留给 UI
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.modules.strategy.core.engines.decision_maker.data_class import LoadBars

logger = logging.getLogger(__name__)

DEFAULT_N = 60
MAX_N = 252
OHLCV = ("date", "open", "high", "low", "close", "volume")
# K 线行里常带、但不是策略指标的字段（勿当 overlay 画上主图）
_BAR_META_KEYS = frozenset(
    {
        "amount",
        "turnover",
        "turnover_rate",
        "turnover_value",
        "pre_close",
        "preclose",
        "change",
        "pct_chg",
        "pct_change",
        "factor",
        "adj_factor",
        "hfq_factor",
        "qfq_factor",
        "code",
        "ts_code",
        "symbol",
        "name",
        "entity_id",
        "stock_id",
    }
)


def parse_info_args(tokens: Sequence[str]) -> Tuple[str, int, Optional[List[str]]]:
    """``<id|code> [N] [col,col]`` → target, N, keep columns or None=default."""
    parts = [str(x).strip() for x in tokens if str(x).strip()]
    if not parts:
        raise ValueError("用法: info <编号|代码> [N] [字段,...]")
    target = parts[0]
    n = DEFAULT_N
    keep: Optional[List[str]] = None
    rest = parts[1:]
    if rest and rest[0].isdigit():
        n = int(rest[0])
        rest = rest[1:]
    if rest:
        joined = ",".join(rest)
        keep = [item.strip() for item in joined.split(",") if item.strip()]
    n = max(1, min(int(n), MAX_N))
    return target, n, keep


def _indicator_field_name(name: str, params: Dict[str, Any]) -> str:
    key = str(name or "").lower()
    length = params.get("length")
    if length is not None and isinstance(length, (int, float, str)):
        return f"{key}{int(length)}"
    parts = [key]
    for param_key in sorted(params.keys()):
        value = params[param_key]
        if isinstance(value, (int, float, str)):
            parts.append(f"{param_key}{value}")
    return "_".join(parts)


def declared_indicator_fields(indicators_cfg: Optional[Dict[str, Any]]) -> List[str]:
    """从 ``settings.data.base.indicators`` 推出默认列名。"""
    cfg = dict(indicators_cfg or {})
    names: List[str] = []
    for name, raw in cfg.items():
        specs = raw if isinstance(raw, list) else [raw]
        for spec in specs:
            params = spec if isinstance(spec, dict) else {}
            field = _indicator_field_name(str(name), params)
            if field and field not in names:
                names.append(field)
    return names


def _apply_indicators(
    rows: List[Dict[str, Any]],
    indicators_cfg: Dict[str, Any],
) -> List[str]:
    """写入指标列，返回实际落盘的字段名（供列发现，避免扫到 amount 等行情元数据）。"""
    if not rows or not indicators_cfg:
        return []
    from core.modules.indicator import Indicator

    written: List[str] = []
    try:
        batch = Indicator.compute_batch(rows, indicators_cfg)
    except (TypeError, ValueError, KeyError) as exc:
        logger.debug("决策者指标计算跳过: %s", exc)
        return []
    for name, cfg, result in batch:
        try:
            if isinstance(result, list):
                field = _indicator_field_name(name, cfg)
                for rec, val in zip(rows, result):
                    rec[field] = val
                if field and field not in written:
                    written.append(field)
            elif isinstance(result, dict):
                # 与报告单股图一致：用 pandas-ta 列名（vtxp_14），勿再拼 name+length
                for key, series in result.items():
                    if not isinstance(series, list):
                        continue
                    field = str(key or "").strip().lower()
                    if not field:
                        continue
                    for rec, val in zip(rows, series):
                        rec[field] = val
                    if field not in written:
                        written.append(field)
        except (TypeError, ValueError, KeyError) as exc:
            logger.debug("决策者指标写入跳过 %s: %s", name, exc)
    return written


def _discover_indicator_columns(
    window: Sequence[Dict[str, Any]],
    declared: Sequence[str],
    written: Sequence[str],
) -> List[str]:
    """只收声明指标 + compute 实际写入列；不扫整行（否则 amount 会当 overlay）。"""
    ohlcv = set(OHLCV)
    ordered: List[str] = []
    seen = set()
    for col in list(declared) + list(written):
        key = str(col or "").strip()
        if not key or key in seen or key in ohlcv or key in _BAR_META_KEYS:
            continue
        if any(key in row for row in window):
            ordered.append(key)
            seen.add(key)
    return ordered


def load_info_table(
    *,
    entity_id: str,
    as_of: str,
    n: int,
    keep: Optional[Sequence[str]],
    indicators_cfg: Optional[Dict[str, Any]],
    load_bars: LoadBars,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """返回 (columns, rows)。rows 按日期升序，右端为 D。"""
    eid = str(entity_id or "").strip()
    cutoff = str(as_of or "").strip()
    width = max(1, min(int(n), MAX_N))
    warmup = 252
    bars = list(load_bars(eid, cutoff, width + warmup) or [])
    bars = [row for row in bars if str(row.get("date") or "").strip() <= cutoff]
    bars.sort(key=lambda row: str(row.get("date") or ""))
    written: List[str] = []
    if indicators_cfg:
        written = _apply_indicators(bars, dict(indicators_cfg))
    window = bars[-width:] if len(bars) > width else bars
    declared = declared_indicator_fields(indicators_cfg)
    if keep:
        cols = ["date"]
        for col in keep:
            key = str(col).strip()
            if key == "date":
                continue
            if key not in cols:
                cols.append(key)
    else:
        ind_cols = _discover_indicator_columns(window, declared, written)
        cols = [c for c in OHLCV if c == "date" or any(c in row for row in window)]
        if "date" not in cols:
            cols.insert(0, "date")
        for col in ind_cols:
            if col not in cols:
                cols.append(col)
    slim: List[Dict[str, Any]] = []
    for row in window:
        slim.append({col: row.get(col) for col in cols})
    return cols, slim


def default_load_bars(entity_id: str, as_of: str, limit: int) -> List[Dict[str, Any]]:
    """现场查库；失败返回空。"""
    try:
        from core.modules.data_manager import DataManager

        dm = DataManager()
        if not getattr(dm, "_initialized", True):
            dm.initialize()
        rows = dm.stock.kline.load_qfq(
            entity_id,
            term="daily",
            end_date=str(as_of or "").strip() or None,
        )
    except Exception as exc:
        logger.debug("决策者 K 线加载失败 %s %s: %s", entity_id, as_of, exc)
        return []
    out = list(rows or [])
    out.sort(key=lambda row: str(row.get("date") or ""))
    if limit > 0:
        out = out[-int(limit) :]
    return out


__all__ = [
    "DEFAULT_N",
    "MAX_N",
    "declared_indicator_fields",
    "default_load_bars",
    "load_info_table",
    "parse_info_args",
]
