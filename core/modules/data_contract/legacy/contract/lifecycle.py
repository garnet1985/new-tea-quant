"""Contract data lifecycle: merge (append-tail), drop (release prefix)."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.modules.data_contract.core.contract.contracts.base import DataContract
from core.modules.data_contract.core.contract.data_class.drop_result import DropResult
from core.modules.data_contract.core.contract.data_class.merge_result import MergeResult
from core.modules.data_contract.core.facade.time_helpers import ContractTimeHelper
from core.modules.data_contract.core.registry.contract_const import ContractType


def merge_append_tail(
    contract: DataContract,
    data: Sequence[Mapping[str, Any]],
) -> MergeResult:
    """Append rows with time strictly greater than current data edge (overlap trimmed from new)."""
    if not data:
        rows = _ensure_list(contract)
        return MergeResult(added_rows=0, total_rows=len(rows))

    ctype = ContractTimeHelper.contract_type(contract)
    if ctype == ContractType.NON_TIME_SERIES:
        rows = _ensure_list(contract)
        batch = [dict(row) for row in data]
        rows.extend(batch)
        return MergeResult(added_rows=len(batch), total_rows=len(rows))

    ContractTimeHelper.require_time_series(contract)
    field = ContractTimeHelper.time_axis_field(contract)
    if not field:
        raise ValueError(f"contract={contract.meta.data_id.value} 缺少 time_axis_field")

    rows = _ensure_list(contract)
    fmt = ContractTimeHelper.time_axis_format(contract)
    edge = ContractTimeHelper.data_edge_end(contract)

    tail: list[dict[str, Any]] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        norm = ContractTimeHelper.normalize_axis_value(row.get(field), fmt)
        if norm is None:
            continue
        if edge is None or norm > edge:
            tail.append(dict(row))

    if tail:
        rows.extend(tail)
    return MergeResult(added_rows=len(tail), total_rows=len(rows))


def drop_before(contract: DataContract, before_time: str) -> DropResult:
    """Release rows with time axis strictly less than before_time."""
    ContractTimeHelper.require_loaded(contract)
    before_norm = _normalize_drop_time(contract, before_time)

    ctype = ContractTimeHelper.contract_type(contract)
    if ctype == ContractType.NON_TIME_SERIES:
        raise ValueError(f"非时序 data_key={contract.meta.data_id.value} 不支持 drop")

    ContractTimeHelper.require_time_series(contract)
    field = ContractTimeHelper.time_axis_field(contract)
    if not field:
        raise ValueError(f"contract={contract.meta.data_id.value} 缺少 time_axis_field")

    rows = contract.data
    if not isinstance(rows, list):
        raise ValueError(f"contract={contract.meta.data_id.value} 的 data 不是 list")

    fmt = ContractTimeHelper.time_axis_format(contract)
    kept: list[dict[str, Any]] = []
    dropped = 0
    for row in rows:
        if not isinstance(row, dict):
            dropped += 1
            continue
        norm = ContractTimeHelper.normalize_axis_value(row.get(field), fmt)
        if norm is None:
            kept.append(row)
            continue
        if norm < before_norm:
            dropped += 1
            continue
        kept.append(row)

    contract.data = kept
    return DropResult(dropped_rows=dropped, total_rows=len(kept))


def _ensure_list(contract: DataContract) -> list[Any]:
    if contract.data is None:
        contract.data = []
    if not isinstance(contract.data, list):
        raise ValueError(f"contract={contract.meta.data_id.value} 的 data 不是 list")
    return contract.data


def _normalize_drop_time(contract: DataContract, before_time: str) -> str:
    fmt = ContractTimeHelper.time_axis_format(contract)
    norm = ContractTimeHelper.normalize_axis_value(before_time, fmt)
    if norm is None:
        raise ValueError(f"before_time 格式非法：{before_time!r}")
    return norm


__all__ = ["drop_before", "merge_append_tail"]
