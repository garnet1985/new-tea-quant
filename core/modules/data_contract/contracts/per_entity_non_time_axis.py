from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Union

from core.modules.data_contract.contracts.base import PerEntityContract


RawPerEntityStaticCategory = Union[Mapping[str, Any], Sequence[Mapping[str, Any]]]


@dataclass(frozen=True, slots=True)
class PerEntityNoTimeAxisContract(PerEntityContract):
    """
    PerEntityNoTimeAxisContract (MVP)

    用于“每个实体一份静态分类/属性/映射”类数据（无 time axis）。

    典型场景：
    - tag_kind=category 的 tag 输出（例如某股票属于某组/某分类）
    - per-entity 的静态权重/属性等

    MVP 行为：
    - 只做 container shape 的 fail-closed 校验
    - entity_id 由调用方在 context 中提供（key 默认 "entity_id"）
    - 返回 raw as-is
    """

    def issue(self, raw: Any, *, context: Optional[Mapping[str, Any]] = None) -> RawPerEntityStaticCategory:
        entity_id, _merged_ctx = self._require_entity_id(context)

        if isinstance(raw, Mapping):
            return raw

        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
            for i, row in enumerate(raw):
                if not isinstance(row, Mapping):
                    raise TypeError(
                        f"PerEntityNoTimeAxisContract.issue: row[{i}] must be a mapping, got {type(row)!r} "
                        f"(entity_id={entity_id})"
                    )
            return raw  # type: ignore[return-value]

        raise TypeError(
            "PerEntityNoTimeAxisContract.issue: raw must be a mapping or a sequence of mappings, "
            f"got {type(raw)!r} (entity_id={entity_id})"
        )


# Backward-compatible alias (MVP): old name kept for existing imports.
PerEntityStaticCategoryContract = PerEntityNoTimeAxisContract

