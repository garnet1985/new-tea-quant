# Data Manager — 设计与决策

**模块：** `modules.data_manager` · **版本：** `0.2.4`

**最低支持核心版本：** `>=0.5.0`

本文记录本模块的设计目标、方案思路与拍板决策。API 以根目录 [API.md](../API.md) 为准。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

提供统一的数据访问门面，支持对不同数据源的访问和查询。表定义分布在 `core/tables` 与 `userspace/extensions/tables` 两处，需要自动发现与注册，并以 `sys_` 前缀区分 core 系统表。

## 方案与思路

- **表发现与注册**：初始化 `DatabaseManager` 后 `create_all_base_tables` 创建基线结构（可写库时）；`_discover_tables` 对 `core/tables` 与 `userspace/extensions/tables` 递归查找 `schema.py`，`register_table` 加载 `model.py` 中第一个 `DbBaseModel` 子类入 `_table_cache`；`get_table(table_name)` 返回已绑定默认 db 的 Model 实例（见 DEC-02）。
- **物理表名**：`get_physical_table_name(logical_name)` 在 PostgreSQL 下可为 `schema.table`；MySQL 等当前返回逻辑名。
- **服务访问形态**：显式嵌套——`data_mgr.stock.list.load(...)`、`data_mgr.macro.load_gdp(...)`；`DataService`（`data_mgr.service`）是子服务容器，不承担跨域聚合 API（见 DEC-01、DEC-03）。
- **与 data_contract 的边界**：Loader 经 `DataManager` 取 raw 行；契约 / `DataKey` / `until` 在 data_contract，本模块不感知 `issue` 语义。
- **样本股票宇宙**归属本模块，data_source 只消费（见 DEC-04）。

---

## DEC-01：决策 1：Facade 与单例

**决策：** 默认进程内单例（锁 + 双重检查）；`force_new` 用于测试/隔离。  
**影响：** 多进程每进程各自 `DataManager`。

---

## DEC-02：决策 2：表定义在 `core/tables` 与 `userspace/extensions/tables`

**决策：** 递归发现 `schema.py`；core 强制 `sys_` 前缀。

---

## DEC-03：决策 3：领域服务属性链

**决策：** 经 `stock` / `macro` / `calendar` / … 属性访问，不包根导出各 Service 类。

---

## DEC-04：决策 4：样本股票宇宙属于 DataManager

**决策：** `use_sample_stock_list` 决定系统内保留哪些股票，经 `DataManager.sample_universe` 访问。data_source 只消费该宇宙（抓取切片 / 写库过滤），不持有名单文件或 API。

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
