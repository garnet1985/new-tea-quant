"""钩子当次要操作的数据。不进 StrategyContext。"""

from __future__ import annotations

from types import MappingProxyType
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

_HIDDEN_FLAGS = frozenset({"as_of_date"})


def _freeze(raw: Optional[Mapping[str, Any]]) -> Mapping[str, Any]:
    return MappingProxyType(dict(raw or {}))


class Series:
    """一条 data key 上、截至当天的序列。

    取行和按下标取行走这里。最低点、波峰波谷一类统计以后也加在这个类型上。
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

    def ids(self) -> List[str]:
        return [str(key).strip() for key in self._entities().keys() if str(key).strip()]

    def records_of(self, entity_id: str) -> Records:
        sid = str(entity_id or "").strip()
        packed = self._entities().get(sid) or {}
        items = packed if isinstance(packed, Mapping) else {}
        return Records(
            entity_id=sid,
            items=items,
            base_data_key=self._base_data_key,
        )


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

    def to_ids(self) -> List[str]:
        return [oid for oid in (self._oid(item) for item in self._items) if oid]

    def get(self, opportunity_id: str) -> Any:
        want = str(opportunity_id or "").strip()
        if not want:
            return None
        for item in self._items:
            if self._oid(item) == want:
                return item
        return None


__all__ = ["CalendarSlice", "Opportunities", "Records", "Series"]
