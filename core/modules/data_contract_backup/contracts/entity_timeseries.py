from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional, Sequence

from core.modules.data_contract.contracts.base import PerEntityContract


@dataclass(frozen=True)
class EntityTimeseriesContract(PerEntityContract):
    """
    **单实体 · 时序**（MVP）

    每个实体一份时间轴上的 records（如 per-stock K 线、tag eventlog、财务快照等）：
    - scope 固定为 `ContractScope.PER_ENTITY`
    - raw 为 rows（`Sequence[Mapping]`）
    - `entity_id` 由调用方在 context 中提供（不强依赖行内必须含 id）

    校验：容器形态 + `time_axis_field` + `required_fields`（fail-closed）。
    """

    time_axis_field: str
    required_fields: Sequence[str] = field(default_factory=tuple)
    display_name: str = ""
    context: Optional[Mapping[str, Any]] = None

    def validate_raw(self, raw: Any, *, context: Optional[Mapping[str, Any]] = None) -> List[Mapping[str, Any]]:
        """
        - context 须含 `context_entity_id_key`（默认 `entity_id`）
        - 每行须含 `time_axis_field`；若配置了 `required_fields` 则每行须含这些列
        """
        entity_id, _merged_ctx = self._require_entity_id(context)

        if raw is None:
            raise TypeError("EntityTimeseriesContract.validate_raw: raw rows is None")

        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
            raise TypeError(
                "EntityTimeseriesContract.validate_raw: raw must be a sequence of mappings, "
                f"got {type(raw)!r}"
            )

        rows: List[Mapping[str, Any]] = []
        for i, row in enumerate(raw):
            if not isinstance(row, Mapping):
                raise TypeError(
                    f"EntityTimeseriesContract.validate_raw: row[{i}] must be a mapping, got {type(row)!r}"
                )

            if self.time_axis_field not in row:
                raise KeyError(
                    f"EntityTimeseriesContract.validate_raw: missing time_axis_field='{self.time_axis_field}' "
                    f"at row[{i}] (entity_id={entity_id})"
                )

            for f in self.required_fields:
                if f not in row:
                    raise KeyError(
                        f"EntityTimeseriesContract.validate_raw: missing required field='{f}' "
                        f"at row[{i}] (entity_id={entity_id})"
                    )

            rows.append(row)

        return rows
