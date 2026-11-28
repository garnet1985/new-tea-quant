# Tables — 公开约定

**模块：** `tables` · **版本：** `0.4.3`

**最低支持核心版本：** `>=0.5.0`

本模块**无 Facade**。对外契约是：每张表的 `schema.py` 声明 + 首个 `DbBaseModel` 子类（`model.py`），由 `DataManager` 发现并注册。调用方应使用 `core.modules.data_manager.DataManager.get_table(<schema['name']>)`，勿直接依赖未文档化的内部路径。

下列为**表定义契约**（全表适用）；单表特有方法见各 `model.py`，状态均为 `beta`。

## TableSchemaContract

单表 `schema.py` 顶层变量 `schema` 的必需键与命名规则。

### schema dict（模块级）

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.4.0`
- **描述：** 表结构 SSOT；发现器按文件名 `schema.py` 定位。
- **参数：** 无（各表目录内独立模块）
- **返回值：** `dict` — 须含 `name`、`fields`、`primaryKey`、`storage_domain`、`update_key`、`kind`；`name` 必须以 `sys_` 开头。

## DbTableModel

各表 `model.py` 中第一个 `DbBaseModel` 子类，供 `register_table` 载入。

### DbBaseModel subclass

- **类型：** `instance`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 绑定 `schema['name']` 的读写模型；构造 `super().__init__(schema['name'], db)`。
- **参数：** `db`（可选）— 默认库由 `DataManager` 注入
- **返回值：** Model 实例 — 继承 `core.infra.db.contracts.DbBaseModel` 的 CRUD / upsert API

## 领域子目录

按 stock / industry / macro / calendar / index / tag / system 组织；**仅为浏览**，存储路由以 `storage_domain` 为准（见 [glossary.yaml](./glossary.yaml)）。