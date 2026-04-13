from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Hashable, List, Mapping, MutableMapping, Optional

from core.modules.data_contract.contract_const import ContractType
from core.modules.data_contract.contracts import DataContract
from core.utils.date.date_utils import DateUtils


@dataclass
class _CursorState:
    """单个数据源通道的游标状态。"""

    rows: List[Dict[str, Any]]
    time_field: Optional[str]
    cursor: int = -1
    acc: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DataCursor:
    """
    面向多个 contract 的运行时前缀视图游标。

    - contract 作为数据真相来源（读取 ``contract.data``）
    - 本类只维护运行期游标状态，返回累计视图
    """

    contracts: Mapping[Hashable, DataContract]
    time_field_overrides: Optional[Mapping[Hashable, Optional[str]]] = None

    _states: MutableMapping[Hashable, _CursorState] = field(init=False, default_factory=dict)

    def __post_init__(self) -> None:
        overrides = dict(self.time_field_overrides or {})

        for source, contract in self.contracts.items():
            payload = contract.data
            if payload is None:
                raise ValueError(
                    f"source={source!r} 的 contract.data 为空；请先 load 再创建 cursor"
                )
            time_field = (
                overrides[source] if source in overrides else self._resolve_time_field(contract)
            )
            self._add_source_state(source, payload, time_field=time_field)

    @classmethod
    def from_rows(
        cls,
        rows_by_source: Mapping[Hashable, List[Dict[str, Any]]],
        *,
        time_field_overrides: Optional[Mapping[Hashable, Optional[str]]] = None,
    ) -> "DataCursor":
        """
        直接从行式数据构建 cursor（适配 strategy 的 ``_current_data`` 结构）。
        """
        cursor = cls(
            contracts={},
            time_field_overrides=time_field_overrides,
        )
        overrides = dict(time_field_overrides or {})
        for source, rows in rows_by_source.items():
            time_field = overrides[source] if source in overrides else "date"
            cursor._add_source_state(source, rows, time_field=time_field)
        return cursor

    def _add_source_state(
        self,
        source: Hashable,
        rows: Any,
        *,
        time_field: Optional[str],
    ) -> None:
        if rows is None:
            raise ValueError(f"source={source!r} 的 rows 为空；请先完成数据加载")
        rows_list = list(rows)
        self._states[source] = _CursorState(rows=rows_list, time_field=time_field)

    def reset(self) -> None:
        for state in self._states.values():
            state.cursor = -1
            state.acc = []

    def until(self, as_of: str) -> Dict[Hashable, List[Dict[str, Any]]]:
        """返回每个数据源在 `as_of`（含）时点的累计前缀视图。"""
        as_of_norm = self._normalize_date(as_of)
        if as_of_norm is None:
            raise ValueError(f"as_of 格式非法：{as_of!r}")

        out: Dict[Hashable, List[Dict[str, Any]]] = {}
        for source, state in self._states.items():
            # 非时序源：不切片，保持全量输出
            if not state.time_field:
                out[source] = list(state.rows)
                continue

            before = state.cursor
            i = before + 1
            n = len(state.rows)
            new_cursor = before

            while i < n:
                rec = state.rows[i]
                raw = rec.get(state.time_field)
                date_norm = self._normalize_date(raw)
                if date_norm is None:
                    i += 1
                    continue
                if date_norm > as_of_norm:
                    break
                state.acc.append(rec)
                new_cursor = i
                i += 1

            state.cursor = new_cursor
            out[source] = state.acc

        return out

    @staticmethod
    def _resolve_time_field(contract: DataContract) -> Optional[str]:
        if contract.meta and isinstance(contract.meta.attrs, dict):
            ctype = contract.meta.attrs.get("type")
            if ctype == ContractType.NON_TIME_SERIES:
                return ""
        if contract.meta and isinstance(contract.meta.attrs, dict):
            tf = contract.meta.attrs.get("time_axis_field")
            if isinstance(tf, str) and tf.strip():
                return tf.strip()
        return "date"

    @staticmethod
    def _normalize_date(value: Any) -> Optional[str]:
        # 统一转成 YYYYMMDD；支持 YYYYMM -> 月初、YYYYQn -> 季度首日
        return DateUtils.normalize(value, fmt=DateUtils.FMT_YYYYMMDD)
