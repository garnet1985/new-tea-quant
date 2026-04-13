from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from core.modules.data_contract.contracts.base import DataContract
from core.modules.data_contract.contracts.validate_helper import (
    validate_mapping_or_rows,
    validate_required_keys,
    validate_time_axis_field,
    validate_time_series_query_params,
)


@dataclass
class TimeSeriesContract(DataContract):
    """Time-series contract template."""

    time_axis_field: str = "date"
    time_axis_format: str = "YYYYMMDD"
    unique_keys: Sequence[str] = field(default_factory=tuple)

    def validate_raw(self, raw: Any) -> Any:
        """
        轻量校验（不做重型规则）：
        - 校验查询参数组合是否合法（来自 issue 注入的 loader_params）
        - 支持单条 Mapping 或 Sequence[Mapping]
        - 校验时间字段存在 + unique_keys 存在
        """
        validate_time_series_query_params(self.loader_params)
        rows = validate_mapping_or_rows(raw, contract_name="时序数据")
        validate_time_axis_field(
            rows,
            time_axis_field=self.time_axis_field,
            contract_name="时序数据",
        )
        validate_required_keys(
            rows,
            required_keys=self.unique_keys,
            contract_name="时序数据",
        )
        return raw
