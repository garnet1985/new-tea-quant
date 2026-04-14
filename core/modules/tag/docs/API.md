# Tag 模块 API 文档

**版本：** `0.2.0`

本文档描述包 **`core.modules.tag`** 的公开导出及 **`BaseTagWorker`** 约定实现面。配置字段与 **`TagModel`** 细节以代码与场景 **`settings.py`** 为准。

---

## get_scenarios_root

### 函数名
`get_scenarios_root() -> Path`

- 状态：`stable`
- 描述：返回 Tag 场景根目录（**`PathManager.tags()`**），用于发现子场景文件夹。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`pathlib.Path`

---

## TagUpdateMode

**枚举**（`core.modules.tag.enums.TagUpdateMode`），包内可从 **`core.modules.tag`** 导入。

| 成员 | 值 | 说明 |
|------|-----|------|
| `INCREMENTAL` | `incremental` | 增量更新 |
| `REFRESH` | `refresh` | 全量刷新 |

---

## TagManager

### 函数名
`__init__(self, is_verbose=False)`

- 状态：`stable`
- 描述：构造 **`DataManager`**、契约缓存与 **`DataContractManager`**，并扫描场景根目录填充 **`scenario_cache`**。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `is_verbose` (可选) | `bool` | 是否详细日志，默认 `False` |

- 返回值：无

---

### 函数名
`refresh_scenario(self) -> None`

- 状态：`stable`
- 描述：清空缓存并重新从磁盘发现场景。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`None`

---

### 函数名
`execute(self, scenario_name: Optional[str] = None, settings: Optional[Dict[str, Any]] = None) -> None`

- 状态：`stable`
- 描述：执行标签流水线。**`settings`** 非空时：用临时 settings 构建 **`ScenarioModel`** 跑一次，不依赖缓存名。**`scenario_name`** 非空时：从 **`scenario_cache`** 取配置执行单个场景。二者皆空时：对缓存中每个场景依次执行。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `scenario_name` (可选) | `Optional[str]` | 场景名 |
| `settings` (可选) | `Optional[Dict[str, Any]]` | 完整 settings 字典；若提供则优先于 `scenario_name` |

- 返回值：`None`

---

## BaseTagWorker

子类须放在场景目录的 **`tag_worker.py`** 中并由 **`TagManager`** 动态加载。**子进程入口**为 **`process_entity()`**，一般无需直接调用。

### 函数名
`process_entity(self) -> Dict[str, Any]`

- 状态：`stable`
- 描述：预处理 → 打标循环 → 后处理与批量保存；异常时返回带 **`success: False`** 与 **`errors`** 的字典。
- 诞生版本：`0.2.0`
- params：无
- 返回值：`Dict[str, Any]`（含 **`entity_id`**、**`scenario_name`**、**`total_dates`**、**`processed_dates`**、**`total_tags_created`**、**`errors`**、**`success`** 等）

---

### 函数名
`calculate_tag(self, as_of_date: str, historical_data: Dict[str, Any], tag_definition: TagModel) -> Optional[Dict[str, Any]]`

- 状态：`stable`（抽象方法，子类必须实现）
- 描述：在给定 **`as_of_date`** 与 **`historical_data`**（按 **`data_id`** 索引的历史行列表）下计算单个标签；返回 **`None`** 表示本日不产生记录。
- 诞生版本：`0.2.0`
- params：

| 名字 | 类型 | 说明 |
|------|------|------|
| `as_of_date` | `str` | 业务日 `YYYYMMDD` |
| `historical_data` | `Dict[str, Any]` | DataCursor 前缀视图 |
| `tag_definition` | `TagModel` | 当前 tag 定义 |

- 返回值：若创建标签，为 **`{"value": ..., "start_date": optional, "end_date": optional}`**；否则 **`None`**。**`value`** 可为 `str` 或可 JSON 序列化的 **`dict`/`list`**。

---

### 钩子（可选重写）

| 函数名 | 说明 |
|--------|------|
| `on_init(self)` | `__init__` 末尾 |
| `on_before_execute_tagging(self)` | 预处理末尾、遍历日期前 |
| `on_tag_created(self, as_of_date, tag_definition, tag_value)` | 每条待保存 tag 生成后 |
| `on_as_of_date_calculate_complete(self, as_of_date)` | 单日所有 tag 尝试完毕后 |
| `on_calculate_error(self, as_of_date, error, tag_definition) -> bool` | 默认返回 **`True`**（继续）；**`False`** 停止该日该 tag 循环 |
| `on_after_execute_tagging(self, result)` | 批量保存之后 |

---

## 相关文档

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DESIGN.md](DESIGN.md)
- [DECISIONS.md](DECISIONS.md)
