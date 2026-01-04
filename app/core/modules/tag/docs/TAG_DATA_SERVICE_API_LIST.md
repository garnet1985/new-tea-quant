# Tag Data Service API 清单

本文档列出了 Tag 系统中所有需要在 `TagDataService`（位于 `app/core_modules/data_manager`）中实现的数据库操作 API。

## 说明

- 所有数据库操作都应该封装在 `TagDataService` 中
- `TagDataService` 应该继承 `BaseDataService`
- 所有方法应该操作 `tag_scenario`、`tag_definition`、`tag_value` 三个表
- 日期格式统一使用 `YYYYMMDD`（字符串）

---

## 1. Scenario 相关 API

### 1.1 `load_scenario(scenario_name: str, scenario_version: str) -> Optional[Dict[str, Any]]`
**功能**：加载指定名称和版本的 scenario

**参数**：
- `scenario_name`: Scenario 名称
- `scenario_version`: Scenario 版本

**返回**：
- `Dict[str, Any]`: Scenario 记录（包含 id, name, version, is_legacy, display_name, description, created_at 等）
- `None`: 如果不存在

**使用位置**：
- `entity_meta_manager.py:89` - `_ensure_scenario`

---

### 1.2 `save_scenario(scenario_name: str, scenario_version: str, display_name: str = None, description: str = None) -> Dict[str, Any]`
**功能**：创建新的 scenario

**参数**：
- `scenario_name`: Scenario 名称
- `scenario_version`: Scenario 版本
- `display_name`: 显示名称（可选，默认使用 scenario_name）
- `description`: 描述（可选，默认空字符串）

**返回**：
- `Dict[str, Any]`: 新创建的 scenario 记录

**使用位置**：
- `entity_meta_manager.py:109` - `_ensure_scenario`

---

### 1.3 `update_scenario(scenario_id: int, scenario_name: str = None, scenario_version: str = None, is_legacy: int = None, display_name: str = None, description: str = None) -> Dict[str, Any]`
**功能**：更新 scenario 信息

**参数**：
- `scenario_id`: Scenario ID
- `scenario_name`: Scenario 名称（可选）
- `scenario_version`: Scenario 版本（可选）
- `is_legacy`: 是否 legacy（0=active, 1=legacy）（可选）
- `display_name`: 显示名称（可选）
- `description`: 描述（可选）

**返回**：
- `Dict[str, Any]`: 更新后的 scenario 记录

**使用位置**：
- `entity_meta_manager.py:98` - `_ensure_scenario`（版本回退）
- `base_tag_worker.py:702, 758` - `handle_version_change`（REFRESH_SCENARIO）

---

### 1.4 `list_scenarios(scenario_name: str = None, include_legacy: bool = False) -> List[Dict[str, Any]]`
**功能**：列出所有 scenarios（支持按名称过滤）

**参数**：
- `scenario_name`: Scenario 名称（可选，如果提供则只返回该名称的所有版本）
- `include_legacy`: 是否包含 legacy 版本（默认 False）

**返回**：
- `List[Dict[str, Any]]`: Scenario 列表

**使用位置**：
- `entity_meta_manager.py:349` - 注释代码 `ensure_scenario`
- `entity_meta_manager.py:490` - 注释代码 `handle_version_change`
- `base_tag_worker.py:650, 888` - `handle_version_change`, `cleanup_legacy_versions`

---

### 1.5 `get_scenario(scenario_name: str, scenario_version: str) -> Optional[Dict[str, Any]]`
**功能**：获取指定名称和版本的 scenario（与 `load_scenario` 功能相同，但命名不同）

**参数**：
- `scenario_name`: Scenario 名称
- `scenario_version`: Scenario 版本

**返回**：
- `Dict[str, Any]`: Scenario 记录
- `None`: 如果不存在

**使用位置**：
- `entity_meta_manager.py:373, 549` - 注释代码
- `base_tag_worker.py:709, 776` - `handle_version_change`

---

### 1.6 `create_scenario(name: str, version: str, display_name: str = None, description: str = None) -> int`
**功能**：创建新的 scenario（返回 scenario_id）

**参数**：
- `name`: Scenario 名称
- `version`: Scenario 版本
- `display_name`: 显示名称（可选）
- `description`: 描述（可选）

**返回**：
- `int`: 新创建的 scenario ID

**使用位置**：
- `entity_meta_manager.py:365` - 注释代码 `ensure_scenario`
- `base_tag_worker.py:735, 768` - `handle_version_change`（NEW_SCENARIO, REFRESH_SCENARIO）

---

### 1.7 `mark_scenario_as_legacy(scenario_id: int) -> None`
**功能**：将 scenario 标记为 legacy（设置 `is_legacy=1`）

**参数**：
- `scenario_id`: Scenario ID

**返回**：
- `None`

**使用位置**：
- `entity_meta_manager.py:539, 572` - 注释代码 `handle_version_change`
- `base_tag_worker.py:699, 732` - `handle_version_change`（ROLLBACK, NEW_SCENARIO）

---

### 1.8 `delete_scenario(scenario_id: int, cascade: bool = False) -> None`
**功能**：删除 scenario（可选级联删除 tag definitions 和 tag values）

**参数**：
- `scenario_id`: Scenario ID
- `cascade`: 是否级联删除（默认 False）

**返回**：
- `None`

**使用位置**：
- `entity_meta_manager.py:781` - 注释代码 `cleanup_legacy_versions`
- `base_tag_worker.py:900` - `cleanup_legacy_versions`

---

## 2. Tag Definition 相关 API

### 2.1 `load_tag(tag_name: str, scenario_id: int, scenario_version: str) -> Optional[Dict[str, Any]]`
**功能**：加载指定名称的 tag definition

**参数**：
- `tag_name`: Tag 名称
- `scenario_id`: Scenario ID
- `scenario_version`: Scenario 版本

**返回**：
- `Dict[str, Any]`: Tag definition 记录（包含 id, name, scenario_id, scenario_version, display_name, description, is_legacy 等）
- `None`: 如果不存在

**使用位置**：
- `entity_meta_manager.py:118` - `_ensure_tag`

---

### 2.2 `save_tag(tag_name: str, scenario_id: int, scenario_version: str, display_name: str, description: str = "") -> Dict[str, Any]`
**功能**：创建新的 tag definition

**参数**：
- `tag_name`: Tag 名称
- `scenario_id`: Scenario ID
- `scenario_version`: Scenario 版本
- `display_name`: 显示名称
- `description`: 描述（可选，默认空字符串）

**返回**：
- `Dict[str, Any]`: 新创建的 tag definition 记录

**使用位置**：
- `entity_meta_manager.py:122` - `_ensure_tag`

---

### 2.3 `get_tag_definitions(scenario_id: int = None, include_legacy: bool = False) -> List[Dict[str, Any]]`
**功能**：获取 tag definitions 列表

**参数**：
- `scenario_id`: Scenario ID（可选，如果提供则只返回该 scenario 下的 tags）
- `include_legacy`: 是否包含 legacy tags（默认 False）

**返回**：
- `List[Dict[str, Any]]`: Tag definition 列表

**使用位置**：
- `entity_meta_manager.py:414, 440` - 注释代码 `ensure_tags`
- `scenarios/momentum/tag_worker.py:177` - `list_tag_definitions`

---

### 2.4 `list_tag_definitions(scenario_id: int = None, include_legacy: bool = False) -> List[Dict[str, Any]]`
**功能**：列出 tag definitions（与 `get_tag_definitions` 功能相同，但命名不同）

**参数**：
- `scenario_id`: Scenario ID（可选）
- `include_legacy`: 是否包含 legacy tags（默认 False）

**返回**：
- `List[Dict[str, Any]]`: Tag definition 列表

**使用位置**：
- `scenarios/momentum/tag_worker.py:177`

---

### 2.5 `create_tag_definition(scenario_id: int, scenario_version: str, name: str, display_name: str, description: str = "") -> int`
**功能**：创建新的 tag definition（返回 tag_definition_id）

**参数**：
- `scenario_id`: Scenario ID
- `scenario_version`: Scenario 版本
- `name`: Tag 名称
- `display_name`: 显示名称
- `description`: 描述（可选，默认空字符串）

**返回**：
- `int`: 新创建的 tag definition ID

**使用位置**：
- `entity_meta_manager.py:431` - 注释代码 `ensure_tags`

---

### 2.6 `delete_tag_definitions_by_scenario(scenario_id: int) -> None`
**功能**：删除指定 scenario 下的所有 tag definitions

**参数**：
- `scenario_id`: Scenario ID

**返回**：
- `None`

**使用位置**：
- `entity_meta_manager.py:597` - 注释代码 `handle_version_change`（REFRESH_SCENARIO）
- `base_tag_worker.py:764` - `handle_version_change`（REFRESH_SCENARIO）

---

## 3. Tag Value 相关 API

### 3.1 `save_tag_value(tag_value_data: Dict[str, Any]) -> int`
**功能**：保存单个 tag value

**参数**：
- `tag_value_data`: Tag value 数据字典，包含：
  - `entity_id`: 实体ID
  - `tag_definition_id`: Tag definition ID
  - `as_of_date`: 业务日期（YYYYMMDD）
  - `value`: 标签值（字符串）
  - `start_date`: 起始日期（可选，YYYYMMDD）
  - `end_date`: 结束日期（可选，YYYYMMDD）
  - `entity_type`: 实体类型（可选，默认 "stock"）

**返回**：
- `int`: 保存的记录数（通常是 1）

**使用位置**：
- `base_tag_worker.py:582` - `save_tag_value`

---

### 3.2 `batch_save_tag_values(tag_values: List[Dict[str, Any]]) -> int`
**功能**：批量保存 tag values

**参数**：
- `tag_values`: Tag value 数据列表（每个元素格式同 `save_tag_value` 的 `tag_value_data`）

**返回**：
- `int`: 保存的记录数

**使用位置**：
- `base_tag_worker.py:405` - `batch_save_tag_values`

---

### 3.3 `delete_tag_values_by_scenario(scenario_id: int) -> None`
**功能**：删除指定 scenario 下的所有 tag values

**参数**：
- `scenario_id`: Scenario ID

**返回**：
- `None`

**使用位置**：
- `entity_meta_manager.py:598` - 注释代码 `handle_version_change`（REFRESH_SCENARIO）
- `base_tag_worker.py:765` - `handle_version_change`（REFRESH_SCENARIO）

---

### 3.4 `get_max_as_of_date(tag_definition_ids: List[int]) -> Optional[str]`
**功能**：获取指定 tag definitions 的最大 `as_of_date`（用于增量计算）

**参数**：
- `tag_definition_ids`: Tag definition ID 列表

**返回**：
- `Optional[str]`: 最大 `as_of_date`（YYYYMMDD 格式），如果没有数据则返回 `None`

**使用位置**：
- `entity_meta_manager.py:177, 194` - `_determine_date_range`（通过 `_get_max_as_of_date` 调用）
- **注意**：当前实现中，`_get_max_as_of_date` 直接查询数据库，应该改为调用此 API

**实现说明**：
- 查询 `tag_value` 表中，`tag_definition_id IN (tag_definition_ids)` 的最大 `as_of_date`
- 使用 SQL: `SELECT MAX(as_of_date) FROM tag_value WHERE tag_definition_id IN (...)`

---

## 4. 其他辅助 API

### 4.1 `get_next_trading_date(date: str) -> str`
**功能**：获取下一个交易日

**参数**：
- `date`: 当前日期（YYYYMMDD 格式）

**返回**：
- `str`: 下一个交易日（YYYYMMDD 格式）

**使用位置**：
- `entity_meta_manager.py:180, 197` - `_determine_date_range`（通过 `_get_next_trading_date` 调用）
- **注意**：当前实现中，`_get_next_trading_date` 是简单实现，应该改为调用 DataManager 的交易日历 API

**实现说明**：
- 应该调用 `DataManager.get_next_trading_date()` 或类似的交易日历 API
- 如果 DataManager 没有此方法，需要实现交易日历查询逻辑

---

## 总结

### 必须实现的 API（共 18 个）

#### Scenario 相关（8 个）
1. ✅ `load_scenario` / `get_scenario`（功能相同，可合并为一个）
2. ✅ `save_scenario` / `create_scenario`（功能相同，可合并为一个）
3. ✅ `update_scenario`
4. ✅ `list_scenarios`
5. ✅ `mark_scenario_as_legacy`
6. ✅ `delete_scenario`

#### Tag Definition 相关（6 个）
7. ✅ `load_tag`
8. ✅ `save_tag` / `create_tag_definition`（功能相同，可合并为一个）
9. ✅ `get_tag_definitions` / `list_tag_definitions`（功能相同，可合并为一个）
10. ✅ `delete_tag_definitions_by_scenario`

#### Tag Value 相关（4 个）
11. ✅ `save_tag_value`
12. ✅ `batch_save_tag_values`
13. ✅ `delete_tag_values_by_scenario`
14. ✅ `get_max_as_of_date` ⭐ **新增，用于增量计算**

#### 辅助 API（1 个）
15. ✅ `get_next_trading_date` ⭐ **新增，用于日期范围确定**

---

## 注意事项

1. **命名统一**：有些方法有多个命名（如 `load_scenario` vs `get_scenario`），建议统一为一个命名
2. **日期格式**：所有日期参数和返回值统一使用 `YYYYMMDD` 格式（字符串）
3. **返回值格式**：所有方法返回的 Dict 应该包含数据库表中的所有字段
4. **错误处理**：所有方法应该处理数据库错误，并抛出适当的异常
5. **事务处理**：批量操作（如 `batch_save_tag_values`）应该使用事务确保数据一致性

---

## 实现优先级

### 高优先级（核心功能）
1. `load_scenario` / `get_scenario`
2. `save_scenario` / `create_scenario`
3. `load_tag`
4. `save_tag` / `create_tag_definition`
5. `save_tag_value`
6. `batch_save_tag_values`
7. `get_max_as_of_date` ⭐ **新增**

### 中优先级（版本管理）
8. `update_scenario`
9. `list_scenarios`
10. `mark_scenario_as_legacy`
11. `get_tag_definitions` / `list_tag_definitions`

### 低优先级（清理和删除）
12. `delete_scenario`
13. `delete_tag_definitions_by_scenario`
14. `delete_tag_values_by_scenario`
15. `get_next_trading_date` ⭐ **新增**（可以暂时使用简单实现）
