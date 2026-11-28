# Tables — 用户指南

**模块：** `tables` · **版本：** `0.4.3`

**最低支持核心版本：** `>=0.5.0`

面向需要改内置表或读懂表名的维护者（非终端交易策略作者）。

---

## 功能总览

- 维护 NTQ 内置市场、宏观、标签、系统等 `sys_*` 表结构
- 为 renew 流水线提供 `update_key` 与列定义真源
- 少数表附带领域 Model 方法（如复权因子 CSV 导入、ST 时段规则）

## 配置说明

- 无独立 settings；`storage_domain` 写在各表 `schema.py`，对齐 `infra.db` 存储域注册表
- 用户业务表在 `userspace/extensions/tables`，表名须 `cust_{kind}_*`，勿写入 `core/tables`

## 常见使用方式

1. **查物理表名：** 打开对应目录 `schema.py`，读 `schema['name']`（一律 `sys_` 前缀）。
2. **加列 / 改类型：** 只改 `schema.py`，走正式 DB 迁移；同步 `model.py` 若读写字段变化。
3. **新增内置表：** 在合适领域子目录新建文件夹，成对添加 `schema.py` + `model.py`（首个类继承 `DbBaseModel`），补 `update_key`。
4. **运行时访问：** 通过 `DataManager.get_table('sys_…')`，不要跨模块 import 深层 `core/tables/.../model.py`（包内单测除外）。
5. **自定义表：** 使用 `DataManager` 用户表 API，目录在 userspace，禁止 `sys_` 前缀。

## 常见坑与注意事项

- 领域文件夹名不等于 `storage_domain`；以 schema 字段为准。
- 改 `schema['name']` 或主键属于破坏性迁移，须 bump 模块版本并写 changelog。
- Agent / 用户工具会拒绝直接改 `core/tables` 结构；应走开发流程。

## 相关文档

- [README](../README.md)
- [API](../API.md)
- [ARCHITECTURE](./ARCHITECTURE.md)
- [glossary.yaml](../glossary.yaml)