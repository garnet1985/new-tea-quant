# Data Manager 设计说明

**版本：** `0.2.0`

本文档描述 **表发现流程**、**表名约定**与 **服务入口形态**。实现以 `data_manager.py` 为准。

**相关文档**：[架构总览](./ARCHITECTURE.md)

---

## 表发现与注册

1. 初始化 `DatabaseManager` 后，`schema_manager.create_all_tables` 创建基线结构（若可写库）。
2. **`_discover_tables`**：对 `PathManager.core() / "tables"` 与 `PathManager.userspace() / "tables"` 递归查找 **`schema.py`**，以其父目录为「表目录」。
3. 对每个目录调用 **`register_table(path, from_core=...)`**：
   - 读取 **`schema.py`** 得逻辑表名 **`name`**。
   - **Core**：表名须以 **`sys_`** 开头，否则跳过。
   - **Userspace**：表名任意。
   - 加载 **`model.py`** 中第一个 **`DbBaseModel`** 子类，缓存到 **`_table_cache[table_name]`**。
4. **`get_table(table_name)`** 返回已绑定默认 db 的 **Model 实例**（供 DataService 内部使用）。

---

## 物理表名

**`get_physical_table_name(logical_name)`**：PostgreSQL 下可返回 **`schema.table`** 形式；MySQL 当前返回逻辑名（见源码注释）。

---

## 服务访问形态

- **显式嵌套**：`data_mgr.stock.list.load(...)`、`data_mgr.macro.load_gdp(...)`，不在 `StockService` 上为子域再提供一层「万能 `load_kline`」式隐式路由（避免职责混淆）。
- **`DataService`（`data_mgr.service`）**：子服务容器，**不**承担跨域聚合 API；Strategy/Tag 侧用各自 Worker 数据管理器组装多源数据。

---

## 与 data_contract 的关系

**`modules.data_contract`** 的 **Loader** 通过 **`DataManager`** 取 raw 行；契约、缓存与 **`DataKey`** 路由在 data_contract 层完成，本模块不感知 `issue/load` 语义。

---

## 相关文档

- [API.md](API.md)
- [DECISIONS.md](DECISIONS.md)
