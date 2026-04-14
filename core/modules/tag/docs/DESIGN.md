# Tag 设计说明

**版本：** `0.2.0`

---

## Scenario 与目录约定

- 根路径：**`get_scenarios_root()`** → **`PathManager.tags()`**（通常为 **`userspace/tags`**）。
- 每个场景一个子目录；跳过以下划线 `_` 开头的目录名。
- 目录内至少包含 **`settings.py`**（场景名、`tags` 定义、`core`/`performance` 等）与 **`tag_worker.py`**（导出继承 **`BaseTagWorker`** 的类）。

---

## 数据与 as_of 语义

- **`TagDataManager`** 根据 settings 中的数据声明装载行槽、重建 **`DataCursor`**。
- 每个交易日 **`as_of`**：**`get_data_until(as_of)`** 返回「截至该日（含）」的累计切片；键为 **`data_id`**（如 **`stock.kline`**），值为历史行列表。
- **`calculate_tag(as_of_date, historical_data, tag_definition)`** 只应基于该切片做决策，避免偷看未来。

---

## 更新模式（`TagUpdateMode`）

- **`INCREMENTAL`**：在已有标签基础上按日期范围增量延伸（具体起止由 Job 与元数据解析决定）。
- **`REFRESH`**：按场景配置对目标区间做全量重算语义（与元数据/库内已有行协同，由 `JobHelper` 等实现细节约束）。

---

## 目标类型（`TagTargetType`）

- **`ENTITY_BASED`**：按股票（或其它实体）维度拆分 Job，一实体一 Worker流程。
- **`GENERAL`**：非「逐实体」类场景的全局型目标（与场景模型字段一致，用于扩展非股票主键的打标）。

---

## Worker 生命周期（摘要）

1. **`__init__`**：解析 `job_payload`，构造 **`TagDataManager`**，调用 **`on_init`**。
2. **`process_entity`**：**`_preprocess`**（hydrate、游标、交易日、**`on_before_execute_tagging`**）→ **`_execute_tagging`** → **`_postprocess`**（批量保存、**`on_after_execute_tagging`**）。
3.逐日、逐 tag 调用 **`calculate_tag`**；非空结果进入待保存列表，并触发 **`on_tag_created`**；单 tag 异常走 **`on_calculate_error`**（返回 `False` 可中断该日该 tag 链）。

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [API.md](API.md)
- [DECISIONS.md](DECISIONS.md)
