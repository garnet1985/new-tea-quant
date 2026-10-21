"""从 data_contract 拉取单条 time series 的 (date, value) 点。"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


def extract_field_points(
    rows: Any,
    field: str,
    *,
    start_date: str = "",
    end_date: str = "",
) -> List[Tuple[str, float]]:
    """从行列表抽取 date + field；非法点跳过。"""
    if not isinstance(rows, list):
        return []
    start = str(start_date or "").strip()
    end = str(end_date or "").strip()
    out: List[Tuple[str, float]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        day = str(row.get("date") or "").strip()
        if not day:
            continue
        if start and day < start:
            continue
        if end and day > end:
            continue
        value = _as_float(row.get(field))
        if value is None:
            continue
        out.append((day, value))
    out.sort(key=lambda item: item[0])
    return out


def load_contract_rows(
    data_key: str,
    *,
    entity_id: str = "",
    issuer: Any = None,
) -> Any:
    """``ContractIssuer.issue(..., fill_in_data=True)`` 后取 ``.data``。"""
    if issuer is None:
        from core.modules.data_contract import ContractIssuer

        issuer_cls = ContractIssuer
    else:
        issuer_cls = issuer

    eid = str(entity_id or "").strip()
    entity_ids = [eid] if eid else None
    contract = issuer_cls.issue(
        data_key,
        entity_ids=entity_ids,
        fill_in_data=True,
    )
    if hasattr(contract, "get_data") and callable(contract.get_data):
        data = contract.get_data()
    else:
        data = getattr(contract, "data", None)
    if eid and isinstance(data, Mapping) and eid in data:
        return data[eid]
    return data


def _as_float(value: Any) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


__all__ = ["extract_field_points", "load_contract_rows"]
