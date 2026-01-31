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

## sys_stock_list 表结构迁移（schema 变更）

新 schema 下 `sys_stock_list` 仅保留 `id`、`name`、`is_active`、`last_update`；行业/板块/市场由定义表 + 映射表维护。若库中表仍含 `industry_id`、`market_id`、`board_id`，需按顺序执行：

1. **先填充新维度表与映射表**（保留旧维度关系）  
   若需从现有 `sys_stock_list` + 旧维度表生成新表数据：
   ```bash
   python scripts/seed_dimension_tables_from_stock_list.py
   ```
   若库中已无上述三列，可从 API 拉取：
   ```bash
   python scripts/seed_dimension_tables_from_stock_list.py --from-api
   ```

2. **再执行迁移脚本（必做）**  
   ```bash
   python scripts/migrate_stock_list_schema.py
   ```
   会：为 sys_industries、sys_boards、sys_markets 补 id 自增（序列 + DEFAULT），再删除 sys_stock_list 的 industry_id、market_id、board_id。  
   **未执行此脚本前，维度表 id 无自增，stock_list 写入或种子脚本会报 id NOT NULL。**

## seed_dimension_tables_from_stock_list.py

从现有 stock list 产生新维度表与映射表的初始值。

- **从 DB**：若 `sys_stock_list` 仍含 `industry_id`、`market_id`、`board_id`，则联合旧表 `sys_stock_industries`、`sys_stock_boards`、`sys_stock_markets` 解析出 (stock_id, 行业/板块/市场)，写入新表 `sys_industries`、`sys_boards`、`sys_markets` 及三张映射表。
- **从 API**：使用 `--from-api` 时从 Tushare 拉取 stock_basic，按 industry / market / exchange 聚合后写入上述新表（不写 sys_stock_list 主表）。

新表：`sys_industries`、`sys_boards`、`sys_markets`、`sys_stock_industry_map`、`sys_stock_board_map`、`sys_stock_market_map`。`sys_markets` 含 `value`（市场名如沪市）与 `code`（交易所代码如 SSE/SZSE/BSE）。

```bash
python scripts/seed_dimension_tables_from_stock_list.py
python scripts/seed_dimension_tables_from_stock_list.py --from-api   # 无 DB 维度列时从 Tushare 拉取
```

## migrate_stock_list_schema.py

将 `sys_stock_list` 表结构迁移为新 schema：删除 `industry_id`、`market_id`、`board_id` 三列。应在执行完 `seed_dimension_tables_from_stock_list.py`（从 DB 生成新维度/映射表）之后再执行。

```bash
python scripts/migrate_stock_list_schema.py
```

## 数据迁移脚本（待实现）

建表完成后，可编写数据迁移脚本：

- 从旧表（如 base_tables 对应旧库表）读取数据
- 按新表结构（core/tables 下 schema.py 定义）转换
- 通过 `data_manager.get_table("sys_xxx")` 获取 Model，写入新表

迁移脚本可放在本目录，例如 `migrate_to_sys_tables.py`。
