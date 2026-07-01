from __future__ import annotations

from typing import Any, Optional

from core.modules.data_contract.core.contract.contracts import DataContract
from core.modules.data_contract.core.contract.data_class.contract_info import TimeRange
from core.modules.data_contract.core.registry.contract_const import ContractType
from core.utils.date.date_utils import DateUtils


def contract_type(contract: DataContract) -> ContractType | None:
    if not contract.meta or not isinstance(contract.meta.attrs, dict):
        return None
    raw = contract.meta.attrs.get("type")
    return raw if isinstance(raw, ContractType) else None


def time_axis_field(contract: DataContract) -> str | None:
    ctype = contract_type(contract)
    if ctype == ContractType.NON_TIME_SERIES:
        return None
    if contract.meta and isinstance(contract.meta.attrs, dict):
        tf = contract.meta.attrs.get("time_axis_field")
        if isinstance(tf, str) and tf.strip():
            return tf.strip()
    if hasattr(contract, "time_axis_field"):
        field = getattr(contract, "time_axis_field", None)
        if isinstance(field, str) and field.strip():
            return field
    return "date"


def time_axis_format(contract: DataContract) -> str | None:
    if contract.meta and isinstance(contract.meta.attrs, dict):
        fmt = contract.meta.attrs.get("time_axis_format")
        if isinstance(fmt, str) and fmt.strip():
            return fmt.strip()
    if hasattr(contract, "time_axis_format"):
        fmt = getattr(contract, "time_axis_format", None)
        if isinstance(fmt, str) and fmt.strip():
            return fmt
    return None


def require_time_series(contract: DataContract) -> None:
    if contract_type(contract) == ContractType.NON_TIME_SERIES:
        raise ValueError(f"非时序 data_key={contract.meta.data_id.value} 无时间窗")


def require_loaded(contract: DataContract) -> None:
    if contract.data is None:
        raise ValueError(f"contract={contract.meta.data_id.value} 的 data 未加载")


def user_start(contract: DataContract) -> Optional[str]:
    require_time_series(contract)
    raw = contract.loader_params.get("start")
    return str(raw) if raw is not None else None


def user_end(contract: DataContract) -> Optional[str]:
    require_time_series(contract)
    raw = contract.loader_params.get("end")
    return str(raw) if raw is not None else None


def user_data_window(contract: DataContract) -> Optional[TimeRange]:
    start = user_start(contract)
    end = user_end(contract)
    if start is None or end is None:
        return None
    return TimeRange(start=start, end=end)


def _normalize_axis_value(value: Any, fmt: str | None) -> Optional[str]:
    if fmt:
        return DateUtils.normalize(value, fmt=fmt)
    return DateUtils.normalize(value, fmt=DateUtils.FMT_YYYYMMDD)


def _iter_row_axis_values(contract: DataContract) -> list[str]:
    require_loaded(contract)
    require_time_series(contract)
    field = time_axis_field(contract)
    if not field:
        return []
    fmt = time_axis_format(contract)
    rows = contract.data
    if not isinstance(rows, list):
        return []
    out: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        norm = _normalize_axis_value(row.get(field), fmt)
        if norm is not None:
            out.append(norm)
    return out


def data_edge_start(contract: DataContract) -> Optional[str]:
    values = _iter_row_axis_values(contract)
    return min(values) if values else None


def data_edge_end(contract: DataContract) -> Optional[str]:
    values = _iter_row_axis_values(contract)
    return max(values) if values else None


def data_window_edge(contract: DataContract) -> Optional[TimeRange]:
    start = data_edge_start(contract)
    end = data_edge_end(contract)
    if start is None or end is None:
        return None
    return TimeRange(start=start, end=end)
