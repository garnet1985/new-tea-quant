"""Series 序列运算：纯函数，不依赖 Series 实例。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union

NumberOrField = Union[str, int, float]

_FLAT_EPS = 1e-12


def _as_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return number


def _row_float(row: Any, field: str) -> Optional[float]:
    if not isinstance(row, dict):
        return None
    return _as_float(row.get(field))


def _row_date(row: Any) -> str:
    if not isinstance(row, dict):
        return ""
    return str(row.get("date") or "").strip()


def _resolve_index(length: int, index: int) -> Optional[int]:
    if length <= 0:
        return None
    if index < 0:
        index = length + index
    if index < 0 or index >= length:
        return None
    return index


def _window_floats(rows: Sequence[Any], field: str, n: int) -> List[float]:
    count = int(n)
    if count <= 0 or not rows:
        return []
    window = list(rows)[-count:]
    out: List[float] = []
    for row in window:
        number = _row_float(row, field)
        if number is not None:
            out.append(number)
    return out


def _side_value(
    rows: Sequence[Any],
    side: NumberOrField,
    index: int,
) -> Optional[float]:
    if isinstance(side, str):
        return _row_float(rows[index], side)
    return _as_float(side)


def at(rows: Sequence[Any], field: str, index: int = -1) -> Optional[float]:
    pos = _resolve_index(len(rows), int(index))
    if pos is None:
        return None
    return _row_float(rows[pos], field)


def min_of(rows: Sequence[Any], field: str, n: int) -> Optional[float]:
    values = _window_floats(rows, field, n)
    return min(values) if values else None


def max_of(rows: Sequence[Any], field: str, n: int) -> Optional[float]:
    values = _window_floats(rows, field, n)
    return max(values) if values else None


def mean_of(rows: Sequence[Any], field: str, n: int) -> Optional[float]:
    values = _window_floats(rows, field, n)
    if not values:
        return None
    return sum(values) / len(values)


def pct_change(rows: Sequence[Any], field: str = "close", n: int = 1) -> Optional[float]:
    steps = int(n)
    if steps <= 0 or len(rows) < steps + 1:
        return None
    last = _row_float(rows[-1], field)
    prev = _row_float(rows[-(steps + 1)], field)
    if last is None or prev is None or prev == 0:
        return None
    return (last - prev) / prev


def crossed_above(
    rows: Sequence[Any],
    field_a: str,
    field_b: NumberOrField,
    *,
    lookback: int = 1,
) -> bool:
    steps = int(lookback)
    if steps != 1 or len(rows) < 2:
        return False
    prev_a = _row_float(rows[-2], field_a)
    curr_a = _row_float(rows[-1], field_a)
    prev_b = _side_value(rows, field_b, -2)
    curr_b = _side_value(rows, field_b, -1)
    if None in (prev_a, curr_a, prev_b, curr_b):
        return False
    return prev_a <= prev_b and curr_a > curr_b


def crossed_below(
    rows: Sequence[Any],
    field_a: str,
    field_b: NumberOrField,
    *,
    lookback: int = 1,
) -> bool:
    steps = int(lookback)
    if steps != 1 or len(rows) < 2:
        return False
    prev_a = _row_float(rows[-2], field_a)
    curr_a = _row_float(rows[-1], field_a)
    prev_b = _side_value(rows, field_b, -2)
    curr_b = _side_value(rows, field_b, -1)
    if None in (prev_a, curr_a, prev_b, curr_b):
        return False
    return prev_a >= prev_b and curr_a < curr_b


def rising(rows: Sequence[Any], field: str = "close", n: int = 1) -> bool:
    steps = int(n)
    if steps <= 0 or len(rows) < steps + 1:
        return False
    for offset in range(steps):
        newer = _row_float(rows[-(offset + 1)], field)
        older = _row_float(rows[-(offset + 2)], field)
        if newer is None or older is None or newer <= older:
            return False
    return True


def falling(rows: Sequence[Any], field: str = "close", n: int = 1) -> bool:
    steps = int(n)
    if steps <= 0 or len(rows) < steps + 1:
        return False
    for offset in range(steps):
        newer = _row_float(rows[-(offset + 1)], field)
        older = _row_float(rows[-(offset + 2)], field)
        if newer is None or older is None or newer >= older:
            return False
    return True


def streak(rows: Sequence[Any], field: str = "close") -> int:
    if len(rows) < 2:
        return 0
    first_newer = _row_float(rows[-1], field)
    first_older = _row_float(rows[-2], field)
    if first_newer is None or first_older is None or first_newer == first_older:
        return 0
    direction = 1 if first_newer > first_older else -1
    count = 1
    for index in range(len(rows) - 2, 0, -1):
        newer = _row_float(rows[index], field)
        older = _row_float(rows[index - 1], field)
        if newer is None or older is None or newer == older:
            break
        step = 1 if newer > older else -1
        if step != direction:
            break
        count += 1
    return direction * count


def _is_strict_extremum(
    values: Sequence[Optional[float]],
    index: int,
    order: int,
    *,
    peak: bool,
) -> bool:
    center = values[index]
    if center is None:
        return False
    for offset in range(1, order + 1):
        left = values[index - offset]
        right = values[index + offset]
        if left is None or right is None:
            return False
        if peak:
            if not (center > left and center > right):
                return False
        else:
            if not (center < left and center < right):
                return False
    return True


def _swing_point(
    rows: Sequence[Any],
    index: int,
    field: str,
    kind: str,
) -> Dict[str, Any]:
    value = _row_float(rows[index], field)
    return {
        "index": index,
        "date": _row_date(rows[index]),
        "value": float(value) if value is not None else 0.0,
        "kind": kind,
    }


def find_peaks(
    rows: Sequence[Any],
    field: str = "high",
    order: int = 2,
) -> List[Dict[str, Any]]:
    width = int(order)
    if width <= 0 or len(rows) < 2 * width + 1:
        return []
    values = [_row_float(row, field) for row in rows]
    out: List[Dict[str, Any]] = []
    for index in range(width, len(rows) - width):
        if _is_strict_extremum(values, index, width, peak=True):
            out.append(_swing_point(rows, index, field, "peak"))
    return out


def find_valleys(
    rows: Sequence[Any],
    field: str = "low",
    order: int = 2,
) -> List[Dict[str, Any]]:
    width = int(order)
    if width <= 0 or len(rows) < 2 * width + 1:
        return []
    values = [_row_float(row, field) for row in rows]
    out: List[Dict[str, Any]] = []
    for index in range(width, len(rows) - width):
        if _is_strict_extremum(values, index, width, peak=False):
            out.append(_swing_point(rows, index, field, "valley"))
    return out


def swing_points(
    rows: Sequence[Any],
    order: int = 2,
    high_field: str = "high",
    low_field: str = "low",
) -> List[Dict[str, Any]]:
    merged = find_peaks(rows, field=high_field, order=order) + find_valleys(
        rows, field=low_field, order=order
    )
    merged.sort(key=lambda item: int(item["index"]))
    return merged


def to_trend(
    rows: Sequence[Any],
    field: str = "close",
    *,
    order: int = 2,
    high_field: str = "high",
    low_field: str = "low",
) -> List[Dict[str, Any]]:
    _ = field  # 第一版只用 high/low swing；保留参数供后续模式
    swings = swing_points(rows, order=order, high_field=high_field, low_field=low_field)
    if len(swings) < 2:
        return []
    segments: List[Dict[str, Any]] = []
    for left, right in zip(swings, swings[1:]):
        start_value = float(left["value"])
        end_value = float(right["value"])
        if abs(end_value - start_value) < _FLAT_EPS:
            direction = "flat"
        elif left["kind"] == "valley" and right["kind"] == "peak":
            direction = "up"
        elif left["kind"] == "peak" and right["kind"] == "valley":
            direction = "down"
        elif end_value > start_value:
            direction = "up"
        elif end_value < start_value:
            direction = "down"
        else:
            direction = "flat"
        segments.append(
            {
                "start_index": int(left["index"]),
                "end_index": int(right["index"]),
                "start_date": str(left.get("date") or ""),
                "end_date": str(right.get("date") or ""),
                "direction": direction,
                "start_value": start_value,
                "end_value": end_value,
            }
        )
    return segments


def body(
    rows: Sequence[Any],
    index: int = -1,
    *,
    open_field: str = "open",
    close_field: str = "close",
) -> Optional[float]:
    pos = _resolve_index(len(rows), int(index))
    if pos is None:
        return None
    open_ = _row_float(rows[pos], open_field)
    close = _row_float(rows[pos], close_field)
    if open_ is None or close is None:
        return None
    return abs(close - open_)


def upper_wick(
    rows: Sequence[Any],
    index: int = -1,
    *,
    open_field: str = "open",
    high_field: str = "high",
    close_field: str = "close",
) -> Optional[float]:
    pos = _resolve_index(len(rows), int(index))
    if pos is None:
        return None
    open_ = _row_float(rows[pos], open_field)
    high = _row_float(rows[pos], high_field)
    close = _row_float(rows[pos], close_field)
    if None in (open_, high, close):
        return None
    return high - max(open_, close)


def lower_wick(
    rows: Sequence[Any],
    index: int = -1,
    *,
    open_field: str = "open",
    low_field: str = "low",
    close_field: str = "close",
) -> Optional[float]:
    pos = _resolve_index(len(rows), int(index))
    if pos is None:
        return None
    open_ = _row_float(rows[pos], open_field)
    low = _row_float(rows[pos], low_field)
    close = _row_float(rows[pos], close_field)
    if None in (open_, low, close):
        return None
    return min(open_, close) - low


def true_range(
    rows: Sequence[Any],
    index: int = -1,
    *,
    high_field: str = "high",
    low_field: str = "low",
    close_field: str = "close",
) -> Optional[float]:
    pos = _resolve_index(len(rows), int(index))
    if pos is None:
        return None
    high = _row_float(rows[pos], high_field)
    low = _row_float(rows[pos], low_field)
    if high is None or low is None:
        return None
    span = high - low
    if pos == 0:
        return span
    prev_close = _row_float(rows[pos - 1], close_field)
    if prev_close is None:
        return span
    return max(span, abs(high - prev_close), abs(low - prev_close))


def is_bullish(
    rows: Sequence[Any],
    index: int = -1,
    *,
    open_field: str = "open",
    close_field: str = "close",
) -> bool:
    pos = _resolve_index(len(rows), int(index))
    if pos is None:
        return False
    open_ = _row_float(rows[pos], open_field)
    close = _row_float(rows[pos], close_field)
    if open_ is None or close is None:
        return False
    return close > open_


def is_bearish(
    rows: Sequence[Any],
    index: int = -1,
    *,
    open_field: str = "open",
    close_field: str = "close",
) -> bool:
    pos = _resolve_index(len(rows), int(index))
    if pos is None:
        return False
    open_ = _row_float(rows[pos], open_field)
    close = _row_float(rows[pos], close_field)
    if open_ is None or close is None:
        return False
    return close < open_


def breakout_above(
    rows: Sequence[Any],
    field: str = "high",
    n: int = 20,
    *,
    compare_field: str = "close",
) -> bool:
    count = int(n)
    if count <= 0 or len(rows) < count + 1:
        return False
    prior = _window_floats(list(rows)[-(count + 1) : -1], field, count)
    if len(prior) < count:
        return False
    current = _row_float(rows[-1], compare_field)
    if current is None:
        return False
    return current > max(prior)


def breakdown_below(
    rows: Sequence[Any],
    field: str = "low",
    n: int = 20,
    *,
    compare_field: str = "close",
) -> bool:
    count = int(n)
    if count <= 0 or len(rows) < count + 1:
        return False
    prior = _window_floats(list(rows)[-(count + 1) : -1], field, count)
    if len(prior) < count:
        return False
    current = _row_float(rows[-1], compare_field)
    if current is None:
        return False
    return current < min(prior)


def gap(
    rows: Sequence[Any],
    *,
    open_field: str = "open",
    close_field: str = "close",
) -> Optional[Dict[str, Any]]:
    if len(rows) < 2:
        return None
    open_ = _row_float(rows[-1], open_field)
    prev_close = _row_float(rows[-2], close_field)
    if open_ is None or prev_close is None or prev_close == 0:
        return None
    delta = open_ - prev_close
    if abs(delta) < _FLAT_EPS:
        kind = "none"
    elif delta > 0:
        kind = "up"
    else:
        kind = "down"
    return {"kind": kind, "pct": delta / prev_close, "delta": delta}


def retracement(
    rows: Sequence[Any],
    field: str = "close",
    *,
    from_peak: bool = True,
    order: int = 2,
    high_field: str = "high",
    low_field: str = "low",
) -> Optional[float]:
    """相对最近一波摆动的回撤比例（0~1+；不足则 None）。"""
    swings = swing_points(rows, order=order, high_field=high_field, low_field=low_field)
    if len(swings) < 2:
        return None
    current = _row_float(rows[-1], field)
    if current is None:
        return None
    want = "peak" if from_peak else "valley"
    end_index = None
    for index in range(len(swings) - 1, -1, -1):
        if swings[index]["kind"] == want:
            end_index = index
            break
    if end_index is None or end_index == 0:
        return None
    end = swings[end_index]
    start = None
    for index in range(end_index - 1, -1, -1):
        if swings[index]["kind"] != want:
            start = swings[index]
            break
    if start is None:
        return None
    span = float(end["value"]) - float(start["value"])
    if abs(span) < _FLAT_EPS:
        return None
    if from_peak:
        # 从峰回落：相对上一谷→峰涨幅
        return (float(end["value"]) - current) / span
    # 从谷反弹：相对上一峰→谷跌幅（span 为负）
    return (current - float(end["value"])) / (-span)
