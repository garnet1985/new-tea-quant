"""
注册 userspace DataKey -> Contract 工厂。

约定：导出 `register_data_contract_routes(registry)`，由 `userspace_contract_discovery` 自动发现并调用。

自定义 key 建议使用稳定字符串常量（可集中放在本包 `keys.py` 等模块），例如::

    MY_SERIES = "user.my_plugin.daily_series"
"""

from __future__ import annotations

from core.modules.data_contract.contract_route_registry import ContractRouteRegistry


def register_data_contract_routes(registry: ContractRouteRegistry) -> None:
    """在此 `registry.register(\"your.key.str\", lambda key_str, ctx: ...)`。"""
    # registry.register("user.example.foo", lambda k, ctx: ...)
    pass
