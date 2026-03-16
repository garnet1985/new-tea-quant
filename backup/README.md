## backup 工具约定说明

本目录用于存放 **数据备份与恢复工具** 以及生成的备份文件。当前只用于内部开发和运维场景，不对框架使用者开放。

---

### 1. 目录结构约定

- `backup/export_table.py`  
  单表导出/备份脚本，把数据库里指定表的数据导出到 `backup/data/`。

- `backup/import_table.py`  
  单表导入/恢复脚本，从 `backup/data/` 下的备份文件导入回数据库。

- `backup/data/`  
  备份数据根目录（已在 `.gitignore` 中忽略），其下结构为：

  - `backup/data/{backup_date}/`：备份日期目录，`backup_date` 为当天 `YYYYMMDD`。  
    例如：`backup/data/20260315/`
  - 目录内是按表划分的单表归档文件：
    - 全量备份：`{table}.tar.gz` 或 `{table}.zip`
    - 范围备份：`{table}_{start}_{end}.tar.gz` 或 `.zip`  
      其中 `start`、`end` 也为 `YYYYMMDD`，表示数据区间。

---

### 2. 导出脚本：`export_table.py`

**作用**：从当前数据库导出一张表的数据，写入 `backup/data/{backup_date}/` 下的单个归档文件。

#### 2.1 基本用法

在项目根目录执行：

```bash
python backup/export_table.py -t sys_corporate_finance -s 20230101 -e 20251231
python backup/export_table.py -t sys_corporate_finance -s 20230101 -d 3y
python backup/export_table.py -t sys_corporate_finance -e 20251231 -d 1095d
python backup/export_table.py -t sys_stock_list
python backup/export_table.py -t sys_corporate_finance -s 20230101 -e 20251231 --format zip
```

#### 2.2 参数说明

- `-t, --table`（必选）  
  源表名，如 `sys_corporate_finance`。

- `-s, --start`（可选）  
  起始日期，格式 `YYYYMMDD`。

- `-e, --end`（可选）  
  结束日期，格式 `YYYYMMDD`。

- `-d, --duration`（可选）  
  时长，支持：
  - `Nd`：天数，如 `30d`
  - `Nm`：月数，如 `3m`
  - `Ny`：年数，如 `2y`

  **区间解析优先级**：
  1. 同时提供 `-s` 和 `-e`：直接使用 `[start, end]` 区间；
  2. 否则若有 `-s` 和 `-d`：从 `start` 正向推 duration 得到 `end`；
  3. 否则若有 `-e` 和 `-d`：从 `end` 反向推 duration 得到 `start`；
  4. 否则：认为是「无日期区间」（仅对无日期列的表有效）。

- `--format`（可选，默认 `tar.gz`）  
  归档格式：
  - `tar.gz`：压缩率更高（默认推荐）；
  - `zip`：兼容性更好（Windows 原生支持）。

- `--keep`（可选，默认 `3`）  
  在 `backup/data/` 下最多保留的**备份日期目录**数量：
  - 每次导出后会扫描 `backup/data/` 中所有 `YYYYMMDD` 目录；
  - 按日期倒序保留最新 `keep` 个，其余整目录删除；
  - 删除前会打印一行日志列出被删除的目录名。

#### 2.3 文件命名与目录结构

- 每次导出都会在：

  ```text
  backup/data/{backup_date}/
  ```

  目录下生成一个文件，其中：
  - `backup_date` 为当天日期，格式 `YYYYMMDD`。

- 文件名规则：
  - 有日期区间时：
    ```text
    {table}_{start}_{end}.tar.gz  或 .zip
    ```
    例如：`sys_corporate_finance_20230101_20251231.tar.gz`
  - 无日期区间（全表导出）时：
    ```text
    {table}.tar.gz  或 .zip
    ```
    例如：`sys_stock_list.tar.gz`

- 若同一天对同一表、同一区间多次导出，会在同一目录下**覆盖**同名文件。

---

### 3. 导入脚本：`import_table.py`

**作用**：从指定备份日期目录中读取单表归档文件，并导入到数据库指定表中。

#### 3.1 基本用法

```bash
# 恢复最近一次备份中的 sys_corporate_finance（覆盖导入到同名表）
python backup/import_table.py -t sys_corporate_finance

# 恢复指定备份日期
python backup/import_table.py -d 20260315 -t sys_corporate_finance

# 导入到不同目标表（用于对比测试）
python backup/import_table.py -d 20260315 -t sys_corporate_finance --target-table sys_corporate_finance_copy

# 补齐模式（不清空）
python backup/import_table.py -t sys_corporate_finance -i
```

#### 3.2 参数说明

- `-d, --date`（可选）  
  备份日期目录名，`YYYYMMDD`。  
  省略时：自动选择 `backup/data/` 下最新的日期目录。

- `-t, --table`（必选）  
  源表名：备份时的表名，如 `sys_corporate_finance`。

- `--target-table`（可选）  
  目标表名：
  - 默认等于 `--table`；
  - 可设置为不同名称，以便导入到测试表做对比。

- 导入模式（三选一，默认 `-r`）：

  - `-r` / `--replace`：**覆盖模式**（默认）
    - 导入前执行：`DELETE FROM target_table`；
    - 然后对 CSV 中的每一行执行 `INSERT`。

  - `-i` / `--incremental`：**补齐模式**
    - 不清空表，直接对每一行执行 `INSERT`。
    - 是否报错或忽略重复，由数据库主键/唯一约束决定。

  - `-u` / `--upsert`：**upsert 模式（预留）**
    - 目前实现与 `-i` 相同（简单 `INSERT`），后续可在此分支上按不同数据库实现 `ON CONFLICT`/`ON DUPLICATE KEY`。

  - 同时传入多个模式（如同时带 `-r` 和 `-i`）会被视为错误并直接退出。

#### 3.3 备份文件选择规则

在 `backup/data/{backup_date}/` 下，按以下顺序查找备份文件：

1. **全量备份优先**：
   - `{table}.tar.gz` 或 `{table}.zip`
   - 如存在多个同名全量文件，会报错提示手动处理。

2. **若无全量，再找范围备份**：
   - `{table}_*.tar.gz` 或 `{table}_*.zip`  
     例如：`sys_corporate_finance_20230101_20251231.tar.gz`
   - 如存在多个范围备份文件，同样报错提示手动处理（当前不自动选择）。

3. **两类都不存在**：  
   - 报错：`在 backup/data/{date} 下未找到 {table} 的备份文件`。

归档内部期望只包含该表的一个 CSV 文件，名称通常为 `{table}.csv`，解压并通过 `csv.DictReader` 读取逐行 `INSERT`。

---

### 4. 后续 TODO（已约定但未实现）

- **多表导出/导入**：
  - 导出：支持一次命令导出多张表（例如 `--tables` 或预定义“全量一套 demo 表”）。
  - 导入：在未指定 `-t` 时，按某个日期目录下的所有归档文件依次导入。

- **真正的 upsert 支持**：
  - 在 `-u` 模式下，根据每个表的主键/唯一约束，分别为 PostgreSQL / MySQL 实现 `INSERT ... ON CONFLICT` 或 `ON DUPLICATE KEY UPDATE`。

本 README 仅面向维护者，用于记载 `backup/` 目录下工具的约定与行为，方便后续扩展和重构。

