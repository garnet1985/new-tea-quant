# Tag · Userspace 使用指南

在 `userspace/tags/` 下按场景（Scenario）定义并实现标签计算逻辑。框架自动发现场景、按配置调度多进程计算，结果写入标签表，供策略与 DataManager 读取。无需改 core。

---

## 目录结构

```
userspace/tags/
└── <scenario_name>/         # 如 momentum_mid_term、my_scenario
    ├── settings.py          # 必选：场景与标签定义（Settings 字典）
    └── tag_worker.py         # 必选：继承 BaseTagWorker，实现 calculate_tag
```

**约定**：目录名即场景名（`name` 在 settings 里需与目录名一致）。框架通过 `PathManager.tags()` 扫描该目录发现场景。

---

## 新增一个标签场景

1. **建目录**：`userspace/tags/<scenario_name>/`。

2. **settings.py**：定义 `Settings` 字典，至少包含：
   - `name`：场景机器名，建议与目录名一致。
   - `is_enabled`：是否参与执行，`True` / `False`。
   - `target_entity`：如 `{"type": "stock_kline_daily"}`（见 `EntityType`）。
   - `update_mode`：`"incremental"` 或 `"refresh"`。
   - `tags`：标签列表，每项含 `name`、`display_name`、`description` 等。
   - 可选：`display_name`、`description`、`start_date`、`end_date`、`incremental_required_records_before_as_of_date`、`performance`（如 `max_workers`、`use_chunk`、`data_chunk_size`）等。

3. **tag_worker.py**：写一个类继承 `BaseTagWorker`，实现：
   - `calculate_tag(self, as_of_date, historical_data, tag_definition) -> Optional[Dict]`
   - 返回 `None` 表示该日不产出标签；返回 `{"value": ...}`（可含 `start_date` / `end_date`）表示产出一条标签。
   - 可访问 `self.entity`、`self.config`、`self.tag_data_service` 等；可选实现 `on_before_execute_tagging`、`on_after_execute_tagging` 等钩子。

4. **执行**：
   - 执行所有启用场景：`TagManager(is_verbose=True).execute()`
   - 仅执行本场景：`TagManager(is_verbose=True).execute(scenario_name="<scenario_name>")`

---

## 在策略或脚本里读标签

通过 DataManager 的标签服务按「实体 + 场景 + 日期区间」读取，无需关心 tag_definition 细节：

```python
from core.modules.data_manager import DataManager

data_mgr = DataManager()
values = data_mgr.stock.tags.load_values_for_entity(
    entity_id="000001.SZ",
    scenario_name="momentum_mid_term",
    start_date="20240101",
    end_date="20241231",
)
```

详见 [api.md](./api.md) 中 TagDataService 部分。

---

## 相关文档

- [API 文档](./api.md)
- [概览](./overview.md)
- [架构](./architecture.md)
