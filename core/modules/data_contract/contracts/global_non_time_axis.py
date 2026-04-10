from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Union

from core.modules.data_contract.contracts.base import GlobalContract


RawStaticCategory = Union[Mapping[str, Any], Sequence[Mapping[str, Any]]]


@dataclass(frozen=True, slots=True)
class GlobalNoTimeAxisContract(GlobalContract):
    """
    GlobalNoTimeAxisContract (MVP)

    用于“静态分类/属性/映射”类数据：
    - 不依赖 time axis（无时间流逝）
    - 输入可以是 dict(mapping) 或 list[dict](rows)
    - fail-closed：输入结构不符合预期直接抛错
    """

    def issue(self, raw: Any, *, context: Optional[Mapping[str, Any]] = None) -> RawStaticCategory:
        """
        Sign raw input as contracted static category data.

        MVP: only validates container shape, returns raw as-is.
        """
        if context:
            # Context is for diagnostics; contract semantics must not change.
            _ = self.with_context(**dict(context))

        if isinstance(raw, Mapping):
            return raw

        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
            for i, row in enumerate(raw):
                if not isinstance(row, Mapping):
                    raise TypeError(
                        f"GlobalNoTimeAxisContract.issue: row[{i}] must be a mapping, got {type(row)!r}"
                    )
            return raw  # type: ignore[return-value]

        raise TypeError(
            "GlobalNoTimeAxisContract.issue: raw must be a mapping or a sequence of mappings, "
            f"got {type(raw)!r}"
        )


# Backward-compatible alias (MVP): old name kept for existing imports.
StaticCategoryContract = GlobalNoTimeAxisContract

