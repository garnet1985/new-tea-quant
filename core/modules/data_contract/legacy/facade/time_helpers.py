from __future__ import annotations

from typing import Any, ClassVar, Optional

from core.modules.data_contract.core.contract.contracts import DataContract
from core.modules.data_contract.core.contract.data_class.contract_info import TimeRange
from core.modules.data_contract.core.registry.contract_const import ContractType
from core.utils.date.date_utils import DateUtils


class ContractTimeHelper:
    """Contract time-axis introspection and normalization."""

    _AXIS_FORMAT_LABELS: ClassVar[dict[str, str]] = {
        "YYYYMMDD": DateUtils.FMT_YYYYMMDD,
        "YYYY-MM-DD": DateUtils.FMT_YYYY_MM_DD,
        "YYYYMM": DateUtils.FMT_YYYYMM,
        "YYYYQ": DateUtils.FMT_YYYYQ,
    }

    @classmethod
    def contract_type(cls, contract: DataContract) -> ContractType | None:
        if not contract.meta or not isinstance(contract.meta.attrs, dict):
            return None
        raw = contract.meta.attrs.get("type")
        return raw if isinstance(raw, ContractType) else None

    @classmethod
    def time_axis_field(cls, contract: DataContract) -> str | None:
        ctype = cls.contract_type(contract)
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

    @classmethod
    def time_axis_format(cls, contract: DataContract) -> str | None:
        if contract.meta and isinstance(contract.meta.attrs, dict):
            fmt = contract.meta.attrs.get("time_axis_format")
            if isinstance(fmt, str) and fmt.strip():
                return fmt.strip()
        if hasattr(contract, "time_axis_format"):
            fmt = getattr(contract, "time_axis_format", None)
            if isinstance(fmt, str) and fmt.strip():
                return fmt
        return None

    @classmethod
    def require_time_series(cls, contract: DataContract) -> None:
        if cls.contract_type(contract) == ContractType.NON_TIME_SERIES:
            raise ValueError(f"非时序 data_key={contract.meta.data_id.value} 无时间窗")

    @classmethod
    def require_loaded(cls, contract: DataContract) -> None:
        if contract.data is None:
            raise ValueError(f"contract={contract.meta.data_id.value} 的 data 未加载")

    @classmethod
    def user_start(cls, contract: DataContract) -> Optional[str]:
        cls.require_time_series(contract)
        raw = contract.loader_params.get("start")
        return str(raw) if raw is not None else None

    @classmethod
    def user_end(cls, contract: DataContract) -> Optional[str]:
        cls.require_time_series(contract)
        raw = contract.loader_params.get("end")
        return str(raw) if raw is not None else None

    @classmethod
    def user_data_window(cls, contract: DataContract) -> Optional[TimeRange]:
        start = cls.user_start(contract)
        end = cls.user_end(contract)
        if start is None or end is None:
            return None
        return TimeRange(start=start, end=end)

    @classmethod
    def normalize_axis_value(cls, value: Any, fmt: str | None) -> Optional[str]:
        resolved = cls._resolve_axis_format(fmt)
        if resolved:
            return DateUtils.normalize(value, fmt=resolved)
        return DateUtils.normalize(value, fmt=DateUtils.FMT_YYYYMMDD)

    @classmethod
    def normalize_as_of(cls, contract: DataContract, as_of: str) -> str:
        as_of_norm = DateUtils.normalize(as_of, fmt=DateUtils.FMT_YYYYMMDD)
        if as_of_norm is None:
            fmt = cls.time_axis_format(contract)
            resolved = cls._resolve_axis_format(fmt)
            as_of_norm = DateUtils.normalize(as_of, fmt=resolved) if resolved else None
        if as_of_norm is None:
            raise ValueError(f"as_of 格式非法：{as_of!r}")
        return as_of_norm

    @classmethod
    def data_edge_start(cls, contract: DataContract) -> Optional[str]:
        values = cls._iter_row_axis_values(contract)
        return min(values) if values else None

    @classmethod
    def data_edge_end(cls, contract: DataContract) -> Optional[str]:
        values = cls._iter_row_axis_values(contract)
        return max(values) if values else None

    @classmethod
    def data_window_edge(cls, contract: DataContract) -> Optional[TimeRange]:
        start = cls.data_edge_start(contract)
        end = cls.data_edge_end(contract)
        if start is None or end is None:
            return None
        return TimeRange(start=start, end=end)

    @classmethod
    def _resolve_axis_format(cls, fmt: str | None) -> str | None:
        if not fmt:
            return None
        s = fmt.strip()
        if not s:
            return None
        if s in cls._AXIS_FORMAT_LABELS:
            return cls._AXIS_FORMAT_LABELS[s]
        if "%" in s:
            return s
        return DateUtils.FMT_YYYYMMDD

    @classmethod
    def _iter_row_axis_values(cls, contract: DataContract) -> list[str]:
        cls.require_loaded(contract)
        cls.require_time_series(contract)
        field = cls.time_axis_field(contract)
        if not field:
            return []
        fmt = cls.time_axis_format(contract)
        rows = contract.data
        if not isinstance(rows, list):
            return []
        out: list[str] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            norm = cls.normalize_axis_value(row.get(field), fmt)
            if norm is not None:
                out.append(norm)
        return out


__all__ = ["ContractTimeHelper"]
