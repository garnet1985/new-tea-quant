"""钩子当次要操作的数据。不进 StrategyContext。"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Union

from . import series_ops

_HIDDEN_FLAGS = frozenset({"as_of_date"})

NumberOrField = Union[str, int, float]


def _freeze(raw: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    return MappingProxyType(dict(raw or {}))


class Series:
    """一条 data key 上、截至当天的序列。

    取行、窗口统计、穿越、波峰波谷与趋势段都挂在这个类型上。
    """

    def __init__(self, rows: Optional[Sequence[Any]] = None) -> None:
        self._rows = list(rows or [])

    def __iter__(self):
        return iter(self._rows)

    def __len__(self) -> int:
        return len(self._rows)

    def __getitem__(self, index: int) -> Any:
        return self._rows[index]

    def _row_at(self, index: int) -> Optional[Dict[str, Any]]:
        if index < 0 or index >= len(self._rows):
            return None
        row = self._rows[index]
        return row if isinstance(row, dict) else None

    @property
    def latest(self) -> Optional[Dict[str, Any]]:
        """最后一行。空序列或最后一行不是 dict 时为 None。"""
        if not self._rows:
            return None
        row = self._rows[-1]
        return row if isinstance(row, dict) else None

    @property
    def first(self) -> Optional[Dict[str, Any]]:
        """第一行。空序列或第一行不是 dict 时为 None。"""
        if not self._rows:
            return None
        row = self._rows[0]
        return row if isinstance(row, dict) else None

    def get_by_date(self, date: str) -> Optional[Dict[str, Any]]:
        """该日期的第一行。没有则 None。"""
        index = self.index_of(date)
        if index is None:
            return None
        return self._row_at(index)

    def index_of(self, date: str) -> Optional[int]:
        """该日期第一次出现的下标。没有则 None。"""
        day = str(date or "").strip()
        if not day:
            return None
        for index, row in enumerate(self._rows):
            if isinstance(row, dict) and str(row.get("date") or "").strip() == day:
                return index
        return None

    def last_index_of(self, date: str) -> Optional[int]:
        """该日期最后一次出现的下标。没有则 None。"""
        day = str(date or "").strip()
        if not day:
            return None
        for index in range(len(self._rows) - 1, -1, -1):
            row = self._rows[index]
            if isinstance(row, dict) and str(row.get("date") or "").strip() == day:
                return index
        return None

    def last(self, amount: int) -> List[Any]:
        """末尾 ``amount`` 行。``amount`` <= 0 时为空列表。"""
        count = int(amount)
        if count <= 0:
            return []
        return self._rows[-count:]

    def at(self, field: str, index: int = -1) -> Optional[float]:
        return series_ops.at(self._rows, field, index)

    def min_of(self, field: str, n: int) -> Optional[float]:
        return series_ops.min_of(self._rows, field, n)

    def max_of(self, field: str, n: int) -> Optional[float]:
        return series_ops.max_of(self._rows, field, n)

    def mean_of(self, field: str, n: int) -> Optional[float]:
        return series_ops.mean_of(self._rows, field, n)

    def pct_change(self, field: str = "close", n: int = 1) -> Optional[float]:
        return series_ops.pct_change(self._rows, field, n)

    def crossed_above(
        self,
        field_a: str,
        field_b: NumberOrField,
        *,
        lookback: int = 1,
    ) -> bool:
        return series_ops.crossed_above(
            self._rows, field_a, field_b, lookback=lookback
        )

    def crossed_below(
        self,
        field_a: str,
        field_b: NumberOrField,
        *,
        lookback: int = 1,
    ) -> bool:
        return series_ops.crossed_below(
            self._rows, field_a, field_b, lookback=lookback
        )

    def rising(self, field: str = "close", n: int = 1) -> bool:
        return series_ops.rising(self._rows, field, n)

    def falling(self, field: str = "close", n: int = 1) -> bool:
        return series_ops.falling(self._rows, field, n)

    def streak(self, field: str = "close") -> int:
        return series_ops.streak(self._rows, field)

    def find_peaks(self, field: str = "high", order: int = 2) -> List[Dict[str, Any]]:
        return series_ops.find_peaks(self._rows, field=field, order=order)

    def find_valleys(self, field: str = "low", order: int = 2) -> List[Dict[str, Any]]:
        return series_ops.find_valleys(self._rows, field=field, order=order)

    def swing_points(
        self,
        order: int = 2,
        high_field: str = "high",
        low_field: str = "low",
    ) -> List[Dict[str, Any]]:
        return series_ops.swing_points(
            self._rows, order=order, high_field=high_field, low_field=low_field
        )

    def to_trend(
        self,
        field: str = "close",
        *,
        order: int = 2,
        high_field: str = "high",
        low_field: str = "low",
    ) -> List[Dict[str, Any]]:
        return series_ops.to_trend(
            self._rows,
            field,
            order=order,
            high_field=high_field,
            low_field=low_field,
        )

    def body(
        self,
        index: int = -1,
        *,
        open_field: str = "open",
        close_field: str = "close",
    ) -> Optional[float]:
        return series_ops.body(
            self._rows, index, open_field=open_field, close_field=close_field
        )

    def upper_wick(
        self,
        index: int = -1,
        *,
        open_field: str = "open",
        high_field: str = "high",
        close_field: str = "close",
    ) -> Optional[float]:
        return series_ops.upper_wick(
            self._rows,
            index,
            open_field=open_field,
            high_field=high_field,
            close_field=close_field,
        )

    def lower_wick(
        self,
        index: int = -1,
        *,
        open_field: str = "open",
        low_field: str = "low",
        close_field: str = "close",
    ) -> Optional[float]:
        return series_ops.lower_wick(
            self._rows,
            index,
            open_field=open_field,
            low_field=low_field,
            close_field=close_field,
        )

    def true_range(
        self,
        index: int = -1,
        *,
        high_field: str = "high",
        low_field: str = "low",
        close_field: str = "close",
    ) -> Optional[float]:
        return series_ops.true_range(
            self._rows,
            index,
            high_field=high_field,
            low_field=low_field,
            close_field=close_field,
        )

    def is_bullish(
        self,
        index: int = -1,
        *,
        open_field: str = "open",
        close_field: str = "close",
    ) -> bool:
        return series_ops.is_bullish(
            self._rows, index, open_field=open_field, close_field=close_field
        )

    def is_bearish(
        self,
        index: int = -1,
        *,
        open_field: str = "open",
        close_field: str = "close",
    ) -> bool:
        return series_ops.is_bearish(
            self._rows, index, open_field=open_field, close_field=close_field
        )

    def breakout_above(
        self,
        field: str = "high",
        n: int = 20,
        *,
        compare_field: str = "close",
    ) -> bool:
        return series_ops.breakout_above(
            self._rows, field, n, compare_field=compare_field
        )

    def breakdown_below(
        self,
        field: str = "low",
        n: int = 20,
        *,
        compare_field: str = "close",
    ) -> bool:
        return series_ops.breakdown_below(
            self._rows, field, n, compare_field=compare_field
        )

    def gap(
        self,
        *,
        open_field: str = "open",
        close_field: str = "close",
    ) -> Optional[Dict[str, Any]]:
        return series_ops.gap(
            self._rows, open_field=open_field, close_field=close_field
        )

    def retracement(
        self,
        field: str = "close",
        *,
        from_peak: bool = True,
        order: int = 2,
        high_field: str = "high",
        low_field: str = "low",
    ) -> Optional[float]:
        return series_ops.retracement(
            self._rows,
            field,
            from_peak=from_peak,
            order=order,
            high_field=high_field,
            low_field=low_field,
        )


class Records:
    """一只股票、当前 as-of 下各数据键的序列。"""

    def __init__(
        self,
        *,
        entity_id: str = "",
        entity_info: Optional[Mapping[str, Any]] = None,
        items: Optional[Mapping[str, Any]] = None,
        base_data_key: str = "",
        position: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.entity_id = str(entity_id or "").strip()
        self.entity_info = _freeze(entity_info)
        self.items = _freeze(items)
        self.base_data_key = str(base_data_key or "").strip()
        self.position = _freeze(position)

    def _rows(self, data_key: str) -> List[Any]:
        raw = self.items.get(str(data_key or "").strip())
        return list(raw) if isinstance(raw, list) else []

    def series(self, data_key: str = "") -> Series:
        """一条注入序列。空 key 表示 base。"""
        return Series(self._rows(data_key or self.base_data_key))

    @property
    def latest(self) -> Optional[Dict[str, Any]]:
        return self.series().latest

    @property
    def first(self) -> Optional[Dict[str, Any]]:
        return self.series().first

    def get_by_date(self, date: str) -> Optional[Dict[str, Any]]:
        return self.series().get_by_date(date)

    def index_of(self, date: str) -> Optional[int]:
        return self.series().index_of(date)

    def last_index_of(self, date: str) -> Optional[int]:
        return self.series().last_index_of(date)

    def last(self, amount: int) -> List[Any]:
        return self.series().last(amount)

    def keys(self) -> List[str]:
        """当前注入且非空的 data key（稳定排序）。"""
        out: List[str] = []
        for key in sorted(str(k).strip() for k in self.items.keys() if str(k).strip()):
            if self.has(key):
                out.append(key)
        return out

    def has(self, data_key: str) -> bool:
        """``items`` 中该键是否存在且为非空序列。"""
        key = str(data_key or "").strip()
        if not key:
            return False
        raw = self.items.get(key)
        return isinstance(raw, list) and len(raw) > 0

    def field(self, name: str, data_key: str = "") -> Optional[float]:
        """最新一行上的数值字段；空 ``data_key`` 表示 base。"""
        return self.series(data_key).at(name)

    def info(self, key: str, default: Any = None) -> Any:
        """读 ``entity_info``；缺省返回 ``default``。"""
        name = str(key or "").strip()
        if not name:
            return default
        if name not in self.entity_info:
            return default
        return self.entity_info[name]

    @property
    def in_position(self) -> bool:
        """``position.remaining_ratio`` 有效持仓。"""
        try:
            remaining = float(self.position.get("remaining_ratio") or 0.0)
        except (TypeError, ValueError):
            return False
        return remaining > 1e-12

    def unrealized_pnl_pct(
        self,
        price_field: str = "close",
        *,
        entry_field: str = "entry_price",
        data_key: str = "",
    ) -> Optional[float]:
        """``(最新价 - 入场价) / 入场价``；无持仓或缺价时 ``None``。"""
        if not self.in_position:
            return None
        try:
            entry = float(self.position.get(entry_field) or 0.0)
        except (TypeError, ValueError):
            return None
        if entry <= 0:
            return None
        price = self.series(data_key).at(price_field)
        if price is None:
            return None
        return (price - entry) / entry

    def holding_bars(self, data_key: str = "") -> Optional[int]:
        """入场日至 as-of（含）在序列上的根数；缺 ``entry_date`` 或对不齐时 ``None``。"""
        entry_date = str(self.position.get("entry_date") or "").strip()
        if not entry_date:
            return None
        series = self.series(data_key)
        if not series:
            return None
        start = series.index_of(entry_date)
        if start is None:
            start = None
            for index, row in enumerate(series):
                if not isinstance(row, dict):
                    continue
                day = str(row.get("date") or "").strip()
                if day and day >= entry_date:
                    start = index
                    break
        if start is None:
            return None
        return len(series) - start

    def align(
        self,
        other_key: str,
        *,
        on: str = "date",
        as_of: Optional[str] = None,
        base_key: str = "",
    ) -> Optional[Dict[str, Any]]:
        """把 ``other_key`` 对齐到 base（或指定）as-of：先精确匹配，否则最近不晚于该日的一行。"""
        _ = on  # 第一版只按 date
        day = str(as_of or "").strip()
        if not day:
            latest = self.series(base_key).latest
            if not isinstance(latest, dict):
                return None
            day = str(latest.get("date") or "").strip()
        if not day:
            return None
        other = self.series(other_key)
        exact = other.get_by_date(day)
        if exact is not None:
            return exact
        matched: Optional[Dict[str, Any]] = None
        for row in other:
            if not isinstance(row, dict):
                continue
            row_day = str(row.get("date") or "").strip()
            if not row_day or row_day > day:
                continue
            matched = row
        return matched

    def both_rising(
        self,
        field: str = "close",
        key_a: str = "",
        key_b: str = "",
        *,
        n: int = 1,
    ) -> bool:
        """两路序列同时 ``rising``；``key_b`` 必填。"""
        other = str(key_b or "").strip()
        if not other:
            return False
        return self.series(key_a).rising(field, n) and self.series(other).rising(
            field, n
        )

    def crossed_on(
        self,
        data_key: str,
        field_a: str,
        field_b: NumberOrField,
        *,
        below: bool = False,
        lookback: int = 1,
    ) -> bool:
        """指定 data key 上的穿越；``below=True`` 为向下穿越。"""
        series = self.series(data_key)
        if below:
            return series.crossed_below(field_a, field_b, lookback=lookback)
        return series.crossed_above(field_a, field_b, lookback=lookback)


class CalendarSlice:
    """当日横截面。日期不在表面上；读股票序列时才组包。"""

    def __init__(
        self,
        *,
        flags: Optional[Mapping[str, Any]] = None,
        base_data_key: str = "",
        loader: Optional[Callable[[], Mapping[str, Any]]] = None,
    ) -> None:
        self._flags = dict(flags or {})
        self._base_data_key = str(base_data_key or "").strip()
        self._loader = loader
        self._by_entity: Optional[Mapping[str, Any]] = None

    def _entities(self) -> Mapping[str, Any]:
        if self._by_entity is None:
            loaded = self._loader() if self._loader is not None else {}
            self._by_entity = loaded if isinstance(loaded, Mapping) else {}
        return self._by_entity

    @property
    def flags(self) -> Mapping[str, Any]:
        visible = {
            key: value
            for key, value in self._flags.items()
            if key not in _HIDDEN_FLAGS
        }
        return MappingProxyType(visible)

    @property
    def is_period_start(self) -> bool:
        return bool(self._flags.get("is_period_start"))

    @property
    def is_period_end(self) -> bool:
        return bool(self._flags.get("is_period_end"))

    @property
    def is_first_open_of_month(self) -> bool:
        return bool(self._flags.get("is_first_open_of_month"))

    @property
    def is_last_open_of_month(self) -> bool:
        return bool(self._flags.get("is_last_open_of_month"))

    @property
    def is_first_open_of_year(self) -> bool:
        return bool(self._flags.get("is_first_open_of_year"))

    @property
    def is_last_open_of_year(self) -> bool:
        return bool(self._flags.get("is_last_open_of_year"))

    def __len__(self) -> int:
        return len(self.ids())

    @property
    def count(self) -> int:
        return len(self)

    @property
    def as_of(self) -> str:
        """当日 as-of；不出现在 ``flags`` 里，需要时显式读。"""
        return str(self._flags.get("as_of_date") or "").strip()

    def ids(self) -> List[str]:
        return [str(key).strip() for key in self._entities().keys() if str(key).strip()]

    def has(self, entity_id: str) -> bool:
        sid = str(entity_id or "").strip()
        if not sid:
            return False
        return sid in self._entities()

    def records_of(self, entity_id: str) -> Records:
        sid = str(entity_id or "").strip()
        packed = self._entities().get(sid) or {}
        items = packed if isinstance(packed, Mapping) else {}
        return Records(
            entity_id=sid,
            items=items,
            base_data_key=self._base_data_key,
        )

    def iter_records(self):
        """按 ``ids()`` 顺序产出 ``Records``。"""
        for entity_id in self.ids():
            yield self.records_of(entity_id)


class Opportunities:
    """当日可选机会。"""

    def __init__(
        self,
        items: Optional[Sequence[Any]] = None,
        *,
        account: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self._items = tuple(items or ())
        self.account = _freeze(account)

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    @staticmethod
    def _oid(item: Any) -> str:
        meta = getattr(item, "meta", None)
        return str(getattr(meta, "opportunity_id", "") or "").strip()

    @staticmethod
    def entity_id(item: Any) -> str:
        """机会对应股票 id。"""
        stock_id = getattr(item, "stock_id", None)
        if stock_id is not None and str(stock_id).strip():
            return str(stock_id).strip()
        stock = getattr(item, "stock", None)
        if isinstance(stock, Mapping):
            return str(stock.get("id") or "").strip()
        return str(getattr(stock, "id", "") or "").strip()

    @property
    def remaining_slots(self) -> int:
        try:
            return max(0, int(self.account.get("remaining_slots") or 0))
        except (TypeError, ValueError):
            return 0

    @property
    def held_ids(self) -> frozenset:
        raw = self.account.get("held_entity_ids") or ()
        if isinstance(raw, (str, bytes)):
            return frozenset()
        return frozenset(
            str(item).strip() for item in raw if str(item or "").strip()
        )

    def is_held(self, entity_id: str) -> bool:
        sid = str(entity_id or "").strip()
        return bool(sid) and sid in self.held_ids

    def to_ids(self) -> List[str]:
        return [oid for oid in (self._oid(item) for item in self._items) if oid]

    def entities(self) -> List[str]:
        """机会对应股票 id（到达序，可重复）。"""
        return [eid for eid in (self.entity_id(item) for item in self._items) if eid]

    def get(self, opportunity_id: str) -> Any:
        want = str(opportunity_id or "").strip()
        if not want:
            return None
        for item in self._items:
            if self._oid(item) == want:
                return item
        return None

    def head(self, n: int) -> List[Any]:
        """前 ``n`` 个（到达序，不排序）。``n`` <= 0 时为空。"""
        count = int(n)
        if count <= 0:
            return []
        return list(self._items[:count])

    def exclude_held(self) -> List[Any]:
        """去掉已持有标的，保持到达序。"""
        held = self.held_ids
        if not held:
            return list(self._items)
        return [
            item
            for item in self._items
            if self.entity_id(item) not in held
        ]


__all__ = ["CalendarSlice", "Opportunities", "Records", "Series"]