from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from core.modules.data_contract.contracts.base import DataContract
from core.modules.data_contract.contracts.validate_helper import validate_mapping_or_rows, validate_required_keys


@dataclass
class NonTimeSeriesContract(DataContract):
    """Non-time-series contract template."""

    unique_keys: Sequence[str] = field(default_factory=tuple)

    def validate_raw(self, raw: Any) -> Any:
        """
        轻量校验（不做重型规则）：
        - 支持单条 Mapping 或 Sequence[Mapping]
        - 若配置了 unique_keys，则校验键存在（不在此阶段做唯一性去重）
        """
        rows = validate_mapping_or_rows(raw, contract_name="非时序数据")
        validate_required_keys(
            rows,
            required_keys=self.unique_keys,
            contract_name="非时序数据",
        )
        return raw
