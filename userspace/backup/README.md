## userspace/backup 约定说明

`userspace/backup/` 是**备份数据目录**。它的核心职责是承接由内部备份脚本触发、并通过核心模块执行的表备份结果。

本目录面向维护者，不建议普通用户手工修改其中内容。

---

### 1. 核心定位

- 核心跨表备份/恢复入口：`DataManager.backup_restore`
- 其底层能力来自各表 model 的 `export_data(...)` / `import_data(...)`。
- 备份产物统一落在 `userspace/backup/data/`。
- `devtools/automation/table_exporting/export_table.py` 是 **Demo 数据导出工具脚本**，不是通用 backup 主入口。

---

### 2. 目录结构

```text
userspace/backup/
  README.md
  data/
    {backup_date}/
      all_tables/               # 全表备份时
      {table}.tar.gz|zip        # 单表备份时（无时间窗口）
      {table}_{start}_{end}.tar.gz|zip
```

说明：

- `{backup_date}` 为执行当天日期（`YYYYMMDD`）。
- `data/` 已在 `.gitignore` 中忽略，不应提交到仓库。

---

### 3. 使用方式（维护者）

#### 3.1 核心跨表备份/恢复（推荐）

```python
from core.modules.data_manager import DataManager

dm = DataManager(is_verbose=False)

# 备份指定表（支持 keep 自动清理）
dm.backup_restore.backup(
    tables=["sys_stock_list", "sys_stock_klines"],
    keep=3,
)

# 恢复指定日期目录中的表
dm.backup_restore.restore(
    backup_date="20260422",
    tables=["sys_stock_list"],
)
```

#### 3.2 Demo 数据导出工具（辅助）

在项目根目录执行：

```bash
# 备份单表（默认窗口）
python devtools/automation/table_exporting/export_table.py -t sys_stock_list

# 备份单表（指定窗口）
python devtools/automation/table_exporting/export_table.py -t sys_corporate_finance --start-date 20230101 --end-date 20251231

# 全表备份（默认窗口）
python devtools/automation/table_exporting/export_table.py

# 全量全表备份（忽略窗口）
python devtools/automation/table_exporting/export_table.py --full
```

---

### 4. 自动清理机制

核心备份服务和 Demo 导出脚本都支持按日期目录自动清理，避免数据无限增长：

- 参数：`--keep`（默认 `3`）
- 行为：在 `userspace/backup/data/` 下按日期目录名（`YYYYMMDD`）倒序排序，仅保留最近 `keep` 个日期目录，其余自动删除。

示例：

```bash
python devtools/automation/table_exporting/export_table.py --keep 5
```

---

### 5. 维护约束

- `userspace/backup/` 内文件主要由脚本生成，不建议手工改动或重命名。
- 如需调整备份逻辑（窗口、归档格式、模型筛选），优先修改 `devtools/automation/table_exporting/export_table.py`，并保持与核心 model 能力一致。

