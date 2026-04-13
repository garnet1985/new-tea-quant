from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Union

from core.modules.data_contract.contracts.base import PerEntityContract


RawEntityNonTimeseries = Union[Mapping[str, Any], Sequence[Mapping[str, Any]]]


@dataclass(frozen=True)
class EntityNonTimeseriesContract(PerEntityContract):
    """
    **单实体 · 非时序**（MVP）

    每个实体一份**无统一时间轴**的映射/分类类数据（如 tag_kind=category 的输出）。

    校验：容器形态；`entity_id` 由 context 提供；返回 raw as-is。
    """

    display_name: str = ""
    context: Optional[Mapping[str, Any]] = None

    def validate_raw(self, raw: Any, *, context: Optional[Mapping[str, Any]] = None) -> RawEntityNonTimeseries:
        entity_id, _merged_ctx = self._require_entity_id(context)

        if isinstance(raw, Mapping):
            return raw

        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
            for i, row in enumerate(raw):
                if not isinstance(row, Mapping):
                    raise TypeError(
                        f"EntityNonTimeseriesContract.validate_raw: row[{i}] must be a mapping, got {type(row)!r} "
                        f"(entity_id={entity_id})"
                    )
            return raw  # type: ignore[return-value]

        raise TypeError(
            "EntityNonTimeseriesContract.validate_raw: raw must be a mapping or a sequence of mappings, "
            f"got {type(raw)!r} (entity_id={entity_id})"
        )
