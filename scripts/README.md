# 脚本说明

## create_sys_tables.py

创建系统表并完成表发现/注册。

1. 初始化 DatabaseManager（连接数据库）
2. 根据 `core/tables` 下所有 `schema.py` 执行 `CREATE TABLE`（SchemaManager.create_all_tables）
3. 递归发现 `core/tables`、`userspace/tables` 下的 `schema.py`，对每个目录调用 `register_table`，注册 Model 到 DataManager

运行后所有 sys_* 表已建好，且 `get_table("sys_xxx")` 可用。

```bash
# 从项目根目录执行
python scripts/create_sys_tables.py
# 或
python -m scripts.create_sys_tables
```

## 数据迁移脚本（待实现）

建表完成后，可编写数据迁移脚本：

- 从旧表（如 base_tables 对应旧库表）读取数据
- 按新表结构（core/tables 下 schema.py 定义）转换
- 通过 `data_manager.get_table("sys_xxx")` 获取 Model，写入新表

迁移脚本可放在本目录，例如 `migrate_to_sys_tables.py`。
