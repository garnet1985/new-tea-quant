from __future__ import annotations

from typing import Any, Mapping, Sequence


def validate_mapping_or_rows(raw: Any, *, contract_name: str) -> Sequence[Mapping[str, Any]]:
    """
    标准化输入为 rows，供 contract 校验逻辑复用。

    支持：
    - 单条 Mapping -> 包装为 1 行
    - Sequence[Mapping]
    """
    if isinstance(raw, Mapping):
        return [raw]

    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
        for i, row in enumerate(raw):
            if not isinstance(row, Mapping):
                raise TypeError(
                    f"{contract_name} 校验失败：row[{i}] 必须是 Mapping，当前为 {type(row)!r}"
                )
        return raw

    raise TypeError(
        f"{contract_name} 校验失败：raw 必须是 Mapping 或 Sequence[Mapping]，当前为 {type(raw)!r}"
    )


def validate_required_keys(
    rows: Sequence[Mapping[str, Any]],
    *,
    required_keys: Sequence[str],
    contract_name: str,
) -> None:
    """校验每一行都包含 required_keys 指定的字段。"""
    if not required_keys:
        return
    for i, row in enumerate(rows):
        for key in required_keys:
            if key not in row:
                raise KeyError(f"{contract_name} 校验失败：row[{i}] 缺少字段 {key!r}")


def validate_time_series_query_params(params: Mapping[str, Any]) -> None:
    """
    时序查询参数轻量校验（按当前约定）：
    - load() -> all
    - load(start=...) -> 点查（amount=1, direction=-1）
    - load(start=..., amount=..., direction=...) -> 窗口
    - load(start=..., end=...) -> 区间
    """
    start = params.get("start")
    end = params.get("end")
    amount = params.get("amount")
    direction = params.get("direction")
    include_boundary = params.get("include_boundary")

    if include_boundary is not None and not isinstance(include_boundary, bool):
        raise TypeError("时序参数校验失败：include_boundary 必须是 bool")

    if end is not None and (amount is not None or direction is not None):
        raise ValueError("时序参数校验失败：end 与 amount/direction 不能同时传入")

    if start is None:
        if end is not None:
            raise ValueError("时序参数校验失败：仅传 end 无效，需同时传 start")
        if amount is not None or direction is not None:
            raise ValueError("时序参数校验失败：仅传 amount/direction 无效，需同时传 start")
        return

    if amount is not None:
        if not isinstance(amount, int):
            raise TypeError("时序参数校验失败：amount 必须是 int")
        if amount < 1:
            raise ValueError("时序参数校验失败：amount 必须 >= 1")

    if direction is not None:
        if direction not in (-1, 1):
            raise ValueError("时序参数校验失败：direction 只能是 -1 或 1")


def validate_time_axis_field(
    rows: Sequence[Mapping[str, Any]],
    *,
    time_axis_field: str,
    contract_name: str,
) -> None:
    """校验每一行都包含 time_axis_field。"""
    for i, row in enumerate(rows):
        if time_axis_field not in row:
            raise KeyError(f"{contract_name} 校验失败：row[{i}] 缺少时间字段 {time_axis_field!r}")

