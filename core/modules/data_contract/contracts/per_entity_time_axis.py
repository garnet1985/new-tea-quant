from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional, Sequence

from core.modules.data_contract.contracts.base import PerEntityContract


@dataclass(frozen=True, slots=True)
class PerEntityTimeAxisContract(PerEntityContract):
    """
    PerEntityTimeAxisContract (MVP)

    用于“每个实体一份时序数据”（如 per-stock K 线、tag eventlog、财务快照等）：
    - 固化 scope=per_entity（外部不可修改）
    - raw 输入是 rows（Sequence[Mapping]）
    - entity_id 由调用方在 context 中提供（避免强依赖 rows 内必须包含 id 字段）

    MVP 行为：
    - 只做 container shape + time_axis_field + required_fields 的 fail-closed 校验
    - 不做 normalize/sort/dedupe（后续需要时再加）
    """

    time_axis_field: str
    required_fields: Sequence[str] = field(default_factory=tuple)

    def issue(self, raw: Any, *, context: Optional[Mapping[str, Any]] = None) -> List[Mapping[str, Any]]:
        """
        Sign raw rows as contracted per-entity time-axis data.

        Requirements:
        - context must contain `context_entity_id_key` (e.g. stock_id)
        - each row must contain `time_axis_field`
        - if required_fields provided, each row must contain them
        """
        entity_id, _merged_ctx = self._require_entity_id(context)

        if raw is None:
            raise TypeError("PerEntityTimeAxisContract.issue: raw rows is None")

        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
            raise TypeError(
                "PerEntityTimeAxisContract.issue: raw must be a sequence of mappings, "
                f"got {type(raw)!r}"
            )

        rows: List[Mapping[str, Any]] = []
        for i, row in enumerate(raw):
            if not isinstance(row, Mapping):
                raise TypeError(
                    f"PerEntityTimeAxisContract.issue: row[{i}] must be a mapping, got {type(row)!r}"
                )

            if self.time_axis_field not in row:
                raise KeyError(
                    f"PerEntityTimeAxisContract.issue: missing time_axis_field='{self.time_axis_field}' "
                    f"at row[{i}] (entity_id={entity_id})"
                )

            for f in self.required_fields:
                if f not in row:
                    raise KeyError(
                        f"PerEntityTimeAxisContract.issue: missing required field='{f}' "
                        f"at row[{i}] (entity_id={entity_id})"
                    )

            rows.append(row)

        return rows

