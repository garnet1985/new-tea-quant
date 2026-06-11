"""
sys_adj_factor_events 数值精度：入库前舍入，避免 DOUBLE 长尾小数。

默认（可被 userspace/system/config/data.json 覆盖）：
- factor: 4 位（Tushare 前链校验）
- price（qfq_anchor / raw_anchor）: price_places，默认 3
- qfq_diff: diff_places，默认 4
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Optional

_FLOAT_FIELDS = ("factor", "qfq_anchor", "raw_anchor", "qfq_diff")


def _load_places() -> tuple[int, int, int]:
    factor_places = 4
    price_places = 3
    diff_places = 4
    try:
        from core.infra.project_context import ConfigManager

        data = ConfigManager.load_data_config() or {}
        block = data.get("adj_factor_event") or {}
        if isinstance(block, dict):
            factor_places = int(block.get("factor_places", factor_places))
            price_places = int(block.get("price_places", price_places))
            diff_places = int(block.get("diff_places", diff_places))
        else:
            dp = ConfigManager.get_decimal_places()
            if dp is not None:
                price_places = max(2, int(dp))
    except Exception:
        pass
    return (
        max(0, factor_places),
        max(0, price_places),
        max(0, diff_places),
    )


def factor_places() -> int:
    return _load_places()[0]


def price_places() -> int:
    return _load_places()[1]


def diff_places() -> int:
    return _load_places()[2]


def factor_tolerance() -> float:
    """前链 factor 比对容差（与 factor 小数位一致）。"""
    p = factor_places()
    return 10 ** (-p) if p > 0 else 1e-6


def _quantize(value: Any, places: int) -> Optional[float]:
    """
    入库舍入：仅接受 float/int（数据源 / 内存计算产物）。

    不接受 Decimal——DB 读出已在 infra connector 转为 float；
    此处再兼容 Decimal 会掩盖混用问题。
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise TypeError("adj_factor 数值字段不接受 bool")
    if isinstance(value, Decimal):
        raise TypeError(
            "adj_factor 数值字段仅接受 float/int；Decimal 应在 DB 读出口已转为 float"
        )
    if not isinstance(value, (int, float)):
        raise TypeError(
            f"adj_factor 数值字段仅接受 float/int，收到 {type(value).__name__}"
        )
    d = Decimal(str(value))
    q = Decimal("1").scaleb(-places)
    return float(d.quantize(q, rounding=ROUND_HALF_UP))


def round_factor(value: Any) -> Optional[float]:
    return _quantize(value, factor_places())


def round_price(value: Any) -> Optional[float]:
    return _quantize(value, price_places())


def round_diff(value: Any) -> Optional[float]:
    return _quantize(value, diff_places())


def normalize_event_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """入库/导出前规范化浮点字段。"""
    out = dict(row)
    if "factor" in out and out["factor"] is not None:
        out["factor"] = round_factor(out["factor"])
    if "qfq_anchor" in out:
        out["qfq_anchor"] = round_price(out["qfq_anchor"])
    if "raw_anchor" in out and out["raw_anchor"] is not None:
        out["raw_anchor"] = round_price(out["raw_anchor"])
    if "qfq_diff" in out and out["qfq_diff"] is not None:
        out["qfq_diff"] = round_diff(out["qfq_diff"])
    return out


def decimal_length_for_field(field_name: str) -> str:
    """schema DECIMAL(p,s) 的 length 字符串。"""
    if field_name == "factor":
        return f"12,{factor_places()}"
    if field_name in ("qfq_anchor", "raw_anchor"):
        return f"12,{price_places()}"
    if field_name == "qfq_diff":
        return f"12,{diff_places()}"
    return "12,4"
