from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional, Sequence

from core.modules.data_contract.contracts.base import GlobalContract


@dataclass(frozen=True)
class GlobalTimeseriesContract(GlobalContract):
    """
    **全局 · 时序**（MVP）

    全市场/宏观等 **一份** 时间轴上的 records（如 GDP、LPR）：
    - scope 固定为 `ContractScope.GLOBAL`
    - 须配置 `time_axis_field`；可选 `required_fields` 强校验列存在
    """

    time_axis_field: str
    required_fields: Sequence[str] = field(default_factory=tuple)
    display_name: str = ""
    context: Optional[Mapping[str, Any]] = None

    def validate_raw(self, raw: Any, *, context: Optional[Mapping[str, Any]] = None) -> List[Mapping[str, Any]]:
        if context:
            _ = self.with_context(**dict(context))

        if raw is None:
            raise TypeError("GlobalTimeseriesContract.validate_raw: raw rows is None")

        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
            raise TypeError(
                "GlobalTimeseriesContract.validate_raw: raw must be a sequence of mappings, "
                f"got {type(raw)!r}"
            )

        rows: List[Mapping[str, Any]] = []
        for i, row in enumerate(raw):
            if not isinstance(row, Mapping):
                raise TypeError(
                    f"GlobalTimeseriesContract.validate_raw: row[{i}] must be a mapping, got {type(row)!r}"
                )

            if self.time_axis_field not in row:
                raise KeyError(
                    f"GlobalTimeseriesContract.validate_raw: missing time_axis_field='{self.time_axis_field}' "
                    f"at row[{i}]"
                )

            for f in self.required_fields:
                if f not in row:
                    raise KeyError(
                        f"GlobalTimeseriesContract.validate_raw: missing required field='{f}' at row[{i}]"
                    )

            rows.append(row)

        return rows
