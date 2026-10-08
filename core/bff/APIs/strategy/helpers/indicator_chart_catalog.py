"""Indicator → chart render metadata (panel / kind / pane_group / y_axis).

Shared by workbench stock detail and decision DTO so FE does not guess layout.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

INDICATOR_LINE_COLORS = (
    "#64B5F6",
    "#BA68C8",
    "#4DD0E1",
    "#AED581",
    "#FF8A65",
    "#F06292",
)

_OSCILLATOR_FIXED_0_100 = frozenset(
    {"rsi", "stoch", "stochrsi", "mfi", "cmo", "uo", "aroon"}
)
_OSCILLATOR_DATA_SCALE = frozenset(
    {
        "willr",
        "cci",
        "roc",
        "mom",
        "atr",
        "natr",
        "true_range",
        "adx",
        "vortex",
        "obv",
        "ad",
        "adosc",
        "cmf",
        "efi",
        "pvt",
        "eom",
        "bbb",
        "bbp",
    }
)
_MACD_FAMILY = frozenset({"macd", "ppo", "trix", "kst"})
_OVERLAY_BANDS = frozenset({"bbands", "kc", "donchian", "supertrend", "psar"})
_BBANDS_OVERLAY_PREFIXES = frozenset({"bbl", "bbm", "bbu"})
_VOLUME_FAMILY = frozenset({"obv", "ad", "adosc", "cmf", "efi", "pvt", "eom"})

# pandas-ta 列名前缀 → 策略 indicator 名（decision 宽表列解析用）
_COLUMN_TOKEN_ALIASES = {
    "supert": "supertrend",
    "supertd": "supertrend",
    "supertl": "supertrend",
    "superts": "supertrend",
    "psarl": "psar",
    "psars": "psar",
    "psaraf": "psar",
    "psarr": "psar",
    "vip": "vortex",
    "vim": "vortex",
    "vtxp": "vortex",
    "vtxm": "vortex",
}

# 只留主画线；方向/长短轨副本、加速因子、反转标记不进图
_SKIP_SUPERTREND_TOKENS = frozenset({"supertd", "supertl", "superts"})
_SKIP_PSAR_TOKENS = frozenset({"psaraf", "psarr"})


def _first_token(text: str) -> str:
    raw = str(text or "").strip().lower()
    if not raw:
        return ""
    return raw.split("_")[0]


def should_skip_chart_series(
    *,
    name: str = "",
    sub_key: str = "",
    field_key: str = "",
) -> bool:
    """辅助列 / 行情元数据不进图。"""
    field = str(field_key or "").strip().lower()
    if field in {
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
    }:
        return True
    base = str(name or "").strip().lower()
    token = _first_token(sub_key) or _first_token(field_key)
    if not base and field_key:
        base, _ = _parse_column_base(field_key)
    if token in _SKIP_SUPERTREND_TOKENS:
        return True
    if base == "supertrend" and token.startswith("supert") and token != "supert":
        return True
    if token in _SKIP_PSAR_TOKENS:
        return True
    return False


def _hist_column(sub_key: str) -> bool:
    """pandas-ta hist columns: MACDh_*, PPOh_*, …"""
    token = _first_token(sub_key)
    if token.endswith("h") and len(token) > 1:
        base = token[:-1]
        return base in _MACD_FAMILY or token in {"macdh", "ppoh", "ksth"}
    return False


def _parse_column_base(column: str) -> tuple[str, str]:
    """Best-effort (indicator_name, sub_key) from a kline field name."""
    key = str(column or "").strip().lower()
    if not key:
        return "", ""
    for family in sorted(
        _MACD_FAMILY
        | _OVERLAY_BANDS
        | _VOLUME_FAMILY
        | _OSCILLATOR_FIXED_0_100
        | _OSCILLATOR_DATA_SCALE,
        key=len,
        reverse=True,
    ):
        if key == family or key.startswith(family + "_") or (
            key.startswith(family) and len(key) > len(family) and not key[len(family)].isalpha()
        ):
            rest = key[len(family) :].lstrip("_")
            return family, rest
    # rsi14 / sma20 / SUPERTd_10_3.0 style
    i = 0
    while i < len(key) and key[i].isalpha():
        i += 1
    if i > 0:
        token = key[:i]
        rest = key[i:].lstrip("_")
        aliased = _COLUMN_TOKEN_ALIASES.get(token)
        if aliased:
            return aliased, key if rest else token
        return token, rest
    return key, ""


def _params_fingerprint(params: Optional[Dict[str, Any]]) -> str:
    if not params:
        return ""
    parts: list[str] = []
    for key in sorted(params.keys()):
        value = params[key]
        if isinstance(value, (int, float, str, bool)):
            parts.append(f"{key}{value}")
    return "_".join(parts)


def _macd_pane_group(
    base: str,
    *,
    field_key: str = "",
    params: Optional[Dict[str, Any]] = None,
) -> str:
    fp = _params_fingerprint(params)
    if fp:
        return f"macd:{base}:{fp}"
    key = str(field_key or "").strip().lower()
    if not key:
        return f"macd:{base}"
    cleaned = key
    for token in (
        f"{base}h",
        f"{base}s",
        f"{base}d",
        base,
    ):
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.strip("_")
    return f"macd:{base}:{cleaned}" if cleaned else f"macd:{base}"


def resolve_indicator_render(
    name: str,
    *,
    sub_key: str = "",
    field_key: str = "",
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return chart render hints for one indicator series.

    Keys: panel, kind, pane_group (optional), y_axis (optional), signed (bool).
    """
    base = str(name or "").strip().lower()
    sub = str(sub_key or "").strip()
    field = str(field_key or "").strip().lower()

    if not base and field:
        base, inferred_sub = _parse_column_base(field)
        if not sub:
            sub = inferred_sub

    # bbands sub-series split
    if base == "bbands" and sub:
        prefix = _first_token(sub)
        if prefix in _BBANDS_OVERLAY_PREFIXES:
            return {
                "panel": "overlay",
                "kind": "line",
                "pane_group": None,
                "y_axis": None,
                "signed": False,
            }
        # %B 可超出 0–1（价在轨外）；带宽与 %B 分轴，避免量纲挤在一起
        if prefix == "bbp":
            return {
                "panel": "oscillator",
                "kind": "line",
                "pane_group": "osc:bbp",
                "y_axis": {"scale": True},
                "signed": False,
            }
        return {
            "panel": "oscillator",
            "kind": "line",
            "pane_group": "osc:bbb",
            "y_axis": {"scale": True},
            "signed": False,
        }

    if base in _MACD_FAMILY:
        is_hist = _hist_column(sub) or _hist_column(field)
        return {
            "panel": "macd",
            "kind": "bar" if is_hist else "line",
            "pane_group": _macd_pane_group(base, field_key=field, params=params),
            "y_axis": {"scale": True},
            "signed": bool(is_hist),
        }

    if base in _VOLUME_FAMILY:
        return {
            "panel": "oscillator",
            "kind": "line",
            "pane_group": f"volind:{base}",
            "y_axis": {"scale": True},
            "signed": False,
        }

    if base in _OSCILLATOR_FIXED_0_100:
        return {
            "panel": "oscillator",
            "kind": "line",
            "pane_group": "oscillator",
            "y_axis": {"min": 0, "max": 100, "scale": True},
            "signed": False,
        }

    if base in _OSCILLATOR_DATA_SCALE:
        return {
            "panel": "oscillator",
            "kind": "line",
            "pane_group": f"osc:{base}",
            "y_axis": {"scale": True},
            "signed": False,
        }

    # default overlay (sma/ema/… and unknown)
    return {
        "panel": "overlay",
        "kind": "line",
        "pane_group": None,
        "y_axis": None,
        "signed": False,
    }


def format_indicator_label(
    name: str,
    *,
    sub_key: str = "",
    params: Optional[Dict[str, Any]] = None,
    field_key: str = "",
) -> str:
    """Human-readable series label for chart legend (not raw TA column names)."""
    base = str(name or "").strip().lower()
    sub = str(sub_key or "").strip()
    field = str(field_key or "").strip()
    params = params or {}

    if not base and field:
        base, sub = _parse_column_base(field)

    token = _first_token(sub) if sub else ""
    short_map = {
        "macd": "DIF",
        "macdh": "HIST",
        "macds": "DEA",
        "ppo": "PPO",
        "ppoh": "HIST",
        "ppos": "SIGNAL",
        "trix": "TRIX",
        "trixs": "SIGNAL",
        "kst": "KST",
        "ksts": "SIGNAL",
        "bbl": "下轨",
        "bbm": "中轨",
        "bbu": "上轨",
        "bbb": "带宽",
        "bbp": "%B",
        "stochk": "K",
        "stochd": "D",
        "stochrsik": "K",
        "stochrsid": "D",
        "supert": "主轨",
        "psarl": "多",
        "psars": "空",
        "vip": "VI+",
        "vim": "VI-",
        "vtxp": "VI+",
        "vtxm": "VI-",
    }

    length = params.get("length")
    base_label = base.upper() if base else (field.upper() if field else "IND")

    if token in short_map:
        part = short_map[token]
        if base in _MACD_FAMILY:
            return f"{base.upper()} {part}"
        if base == "bbands":
            return f"BB {part}" + (f"({int(length)})" if length is not None else "")
        if base in {"stoch", "stochrsi"}:
            return f"{base_label} {part}"
        return f"{base_label} {part}"

    if length is not None:
        try:
            return f"{base_label}({int(length)})"
        except (TypeError, ValueError):
            return f"{base_label}({length})"
    if sub:
        return f"{base_label} {token.upper()}" if token else base_label
    return base_label


def resolve_indicator_render_from_column(column: str) -> Dict[str, Any]:
    base, sub = _parse_column_base(column)
    return resolve_indicator_render(base, sub_key=sub, field_key=column)


def apply_render_fields(
    series_row: Dict[str, Any],
    render: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge catalog render into an indicator_series dict (mutates and returns)."""
    series_row["panel"] = render.get("panel") or "overlay"
    series_row["kind"] = render.get("kind") or "line"
    pane_group = render.get("pane_group")
    if pane_group:
        series_row["pane_group"] = pane_group
    y_axis = render.get("y_axis")
    if y_axis:
        series_row["y_axis"] = y_axis
    if render.get("signed"):
        series_row["signed"] = True
        if series_row.get("kind") == "bar":
            series_row["color"] = "signed"
    return series_row


def next_indicator_color(index: int) -> str:
    return INDICATOR_LINE_COLORS[index % len(INDICATOR_LINE_COLORS)]


__all__ = [
    "INDICATOR_LINE_COLORS",
    "apply_render_fields",
    "format_indicator_label",
    "next_indicator_color",
    "resolve_indicator_render",
    "resolve_indicator_render_from_column",
    "should_skip_chart_series",
]
