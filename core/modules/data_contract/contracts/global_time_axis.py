from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, List, Mapping, Optional, Sequence

from core.modules.data_contract.contracts.base import ContractScope, GlobalContract


@dataclass(frozen=True, slots=True)
class GlobalTimeAxisContract(GlobalContract):
    """
    GlobalTimeAxisContract (MVP)

    用于“全局一份时序数据”：
    - 固化 scope=global
    - 必须存在 time_axis_field（例如 date/quarter）
    - 可选 required_fields（如果给了就强校验）

    注意：
    - time_axis_field / required_fields 属于 contract 的结构性规则，建议由具体 DataKey 对应的
      contract 实例固定，不建议在 issue(...) 时由外部传入修改。
    """

    time_axis_field: str
    required_fields: Sequence[str] = field(default_factory=tuple)

    def issue(self, raw: Any, *, context: Optional[Mapping[str, Any]] = None) -> List[Mapping[str, Any]]:
        """
        Sign raw rows as contracted global time-axis data.

        MVP: validate shape + required fields, return rows as-is.
        """
        if context:
            _ = self.with_context(**dict(context))

        if raw is None:
            raise TypeError("GlobalTimeAxisContract.issue: raw rows is None")

        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
            raise TypeError(
                "GlobalTimeAxisContract.issue: raw must be a sequence of mappings, "
                f"got {type(raw)!r}"
            )

        rows: List[Mapping[str, Any]] = []
        for i, row in enumerate(raw):
            if not isinstance(row, Mapping):
                raise TypeError(
                    f"GlobalTimeAxisContract.issue: row[{i}] must be a mapping, got {type(row)!r}"
                )

            if self.time_axis_field not in row:
                raise KeyError(
                    f"GlobalTimeAxisContract.issue: missing time_axis_field='{self.time_axis_field}' "
                    f"at row[{i}]"
                )

            for f in self.required_fields:
                if f not in row:
                    raise KeyError(
                        f"GlobalTimeAxisContract.issue: missing required field='{f}' at row[{i}]"
                    )

            rows.append(row)

        return rows

