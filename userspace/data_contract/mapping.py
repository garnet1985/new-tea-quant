from __future__ import annotations

from core.modules.data_contract.contract_const import ContractScope, ContractType

# userspace 扩展映射（示例）
# key: data_id 字符串（建议稳定且全局唯一）
# value: DataSpec 字段（至少包含 scope/type/loader）
custom_map = {
    # "user.example.daily_series": {
    #     "scope": ContractScope.PER_ENTITY,
    #     "type": ContractType.TIME_SERIES,
    #     "unique_keys": ["date", "entity_id"],
    #     "time_axis_field": "date",
    #     "time_axis_format": "YYYYMMDD",
    #     "loader": "user.example.daily_series",
    #     "display_name": "示例日频序列",
    #     "defaults": {},
    # }
}
