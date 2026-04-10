"""
Userspace：自定义 DataKey（字符串 id）与 Contract 工厂注册。

- **不要**修改 `core/.../data_keys.py`（随 core 升级会覆盖）。
- 在 `contract_routes.py`（或本包下其它子模块）中实现 `register_data_contract_routes`，
  由框架扫描并合并到默认 `DataContractManager` 使用的路由表。
"""
