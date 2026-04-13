from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Sequence, Union

from core.modules.data_contract.contracts.base import GlobalContract


RawGlobalNonTimeseries = Union[Mapping[str, Any], Sequence[Mapping[str, Any]]]


@dataclass(frozen=True)
class GlobalNonTimeseriesContract(GlobalContract):
    """
    **全局 · 非时序**（MVP）

    字典/映射/静态清单等 **无统一时间轴** 的数据（如股票列表、行业表、系统 meta）：
    - scope 固定为 `ContractScope.GLOBAL`
    - 输入可为单条 `Mapping` 或 `list[dict]`；仅校验容器形态
    """

    display_name: str = ""
    context: Optional[Mapping[str, Any]] = None

    def validate_raw(self, raw: Any, *, context: Optional[Mapping[str, Any]] = None) -> RawGlobalNonTimeseries:
        if context:
            _ = self.with_context(**dict(context))

        if isinstance(raw, Mapping):
            return raw

        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
            for i, row in enumerate(raw):
                if not isinstance(row, Mapping):
                    raise TypeError(
                        f"GlobalNonTimeseriesContract.validate_raw: row[{i}] must be a mapping, got {type(row)!r}"
                    )
            return raw  # type: ignore[return-value]

        raise TypeError(
            "GlobalNonTimeseriesContract.validate_raw: raw must be a mapping or a sequence of mappings, "
            f"got {type(raw)!r}"
        )
