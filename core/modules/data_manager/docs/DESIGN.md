# Data Manager 设计说明

**模块：** `modules.data_manager` · **版本：** `0.4.0`

API 以根目录 [API.md](../API.md) 为准。实现以 `data_manager.py` 为准。

---

## 1. 表发现与注册

1. 初始化 `DatabaseManager` 后，`create_all_base_tables` 创建基线结构（可写库时）。
2. **`_discover_tables`**：对 `core/tables` 与 `userspace/extensions/tables`（`ProjectContext.path.get_extensions_tables_directory()`）递归查找 **`schema.py`**。
3. **`register_table(path, from_core=...)`**：
   - 读 `schema.py` 逻辑表名 `name`
   - **Core**：须以 `sys_` 开头，否则跳过
   - **Userspace**：表名任意
   - 加载 `model.py` 中第一个 `DbBaseModel` 子类 → `_table_cache`
4. **`get_table(table_name)`** 返回已绑定默认 db 的 Model 实例（供 DataService 内部使用）

---

## 2. 物理表名

**`get_physical_table_name(logical_name)`**：PostgreSQL 下可为 `schema.table`；MySQL 等当前返回逻辑名。

---

## 3. 服务访问形态

- **显式嵌套**：`data_mgr.stock.list.load(...)`、`data_mgr.macro.load_gdp(...)`
- **`DataService`（`data_mgr.service`）**：子服务容器，不承担跨域聚合 API

---

## 4. 与 data_contract

Loader 经 **`DataManager`** 取 raw 行；契约 / `DataKey` / `until` 在 data_contract，本模块不感知 `issue` 语义。

---

## 5. 设计决策

### 决策 1：Facade 与单例

**决策：** 默认进程内单例（锁 + 双重检查）；`force_new` 用于测试/隔离。  
**影响：** 多进程每进程各自 `DataManager`。

### 决策 2：表定义在 `core/tables` 与 `userspace/extensions/tables`

**决策：** 递归发现 `schema.py`；core 强制 `sys_` 前缀。

### 决策 3：领域服务属性链

**决策：** 经 `stock` / `macro` / `calendar` / … 属性访问，不包根导出各 Service 类。

---

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [API.md](../API.md)
