# Tables（`tables`）

**模块：** `tables` · **版本：** `0.4.3`

**最低支持核心版本：** `>=0.5.0`

内置系统表的 schema 与 Model 定义仓库。运行时发现与注册由 `modules.data_manager` 完成；业务代码通过 `DataManager.get_table` 按物理表名访问，不经过本目录的 Facade。

## 适用场景

- 查阅或修改 NTQ 内置 `sys_*` 表结构（列、索引、`storage_domain`、renew 用 `update_key`）
- 为数据源 renew / 回测新增领域表（须在对应领域子目录成对维护 `schema.py` + `model.py`）
- 理解表名、`storage_domain` 与用户自定义表（`userspace/extensions/tables` 的 `cust_*`）的边界

## 模块依赖

- 无（表 Model 运行时依赖 `infra.db.contracts.DbBaseModel`，由 `data_manager` 注入）

## 设计初衷

- **要解决的问题：** 把内置表定义从业务模块中剥离，统一发现路径与 `sys_` 命名，便于迁移 diff 与 renew 对齐。
- **明确不做：** 不提供模块级 Facade；不在此目录放用户自定义表；不替代 `DataManager` 的注册与建表编排。

## 相关文档

- [公开约定](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [用户指南](./docs/USER_GUIDE.md)
- [测试用例](./__test__/TEST_CASES.md)