# Tag Definition 标签定义表

## 表结构

- **表名**: `tag_definition`
- **主键**: `id` (自增)

## 字段说明

- `id` (BIGINT): 自增主键
- `scenario_id` (BIGINT): 外键 → `tag_scenario.id`（所属的业务场景）
- `scenario_version` (VARCHAR 32): **业务场景版本号**（冗余字段，与 `tag_scenario.version` 保持一致，用于查询优化）
- `is_legacy` (TINYINT 1): **是否为遗留标签**（冗余字段，与 `tag_scenario.is_legacy` 保持一致，用于查询优化，默认 0）
- `name` (VARCHAR 64): 标签唯一代码（如 `large_market_value`, `small_market_value`）
- `display_name` (VARCHAR 128): 标签显示名称（用户可见）
- `description` (TEXT, 可选): 标签描述
- `created_at` (DATETIME): 创建时间
- `updated_at` (DATETIME): 更新时间

## 索引

- `uk_scenario_name`: `(scenario_id, name)` UNIQUE - 同一 Scenario 下标签名唯一
- `idx_scenario_id`: `(scenario_id)` - 业务场景ID索引（用于快速查询某个场景下的所有标签）
- `idx_scenario_version`: `(scenario_id, scenario_version)` - 业务场景版本索引（用于快速查询某个场景的某个版本下的所有标签）
- `idx_scenario_legacy`: `(scenario_id, is_legacy)` - 业务场景遗留状态索引（用于快速查询某个场景的非遗留标签）

## 设计要点

1. **属于某个 Scenario**：通过 `scenario_id` 外键关联
2. **冗余 Scenario 的版本**：`scenario_version` 字段冗余存储 `tag_scenario.version`，用于查询优化
   - 创建 Tag Definition 时，自动从 Scenario 中获取 version 并冗余存储
   - 由于 Scenario 的 version 相对稳定（通常不会更新，而是创建新版本），数据一致性风险低
3. **标签名在同一 Scenario 内唯一**：通过 `uk_scenario_name` 唯一索引保证
4. **一个 Scenario 可以产生多个 Tags**：如市值分类场景可以产生大市值、小市值两个 Tags

## 使用场景

### 创建标签定义

```python
# 为某个 Scenario 创建标签定义
tag_def = TagDefinitionModel.create(
    scenario_id=1,
    name="large_market_value",
    display_name="大市值股票",
    description="市值大于阈值的股票"
)
```

### 查询场景下的所有标签

```python
# 查询某个 Scenario 下的所有 Tags
tags = TagDefinitionModel.get_by_scenario_id(scenario_id)
# 返回: [
#   {"id": 10, "scenario_id": 1, "scenario_version": "1.0", "name": "large_market_value", ...},
#   {"id": 11, "scenario_id": 1, "scenario_version": "1.0", "name": "small_market_value", ...},
# ]

# 查询某个 Scenario 的某个版本下的所有 Tags（利用冗余字段，无需 JOIN）
tags = TagDefinitionModel.get_by_scenario_version(scenario_id, "1.0")
# 返回: [
#   {"id": 10, "scenario_id": 1, "scenario_version": "1.0", "name": "large_market_value", ...},
#   {"id": 11, "scenario_id": 1, "scenario_version": "1.0", "name": "small_market_value", ...},
# ]

# 查询某个 Scenario 的非遗留 Tags（利用冗余字段，无需 JOIN）
tags = TagDefinitionModel.get_by_scenario_non_legacy(scenario_id)
# SQL: SELECT * FROM tag_definition WHERE scenario_id = X AND is_legacy = 0
# 返回: [
#   {"id": 10, "scenario_id": 1, "scenario_version": "1.0", "is_legacy": 0, "name": "large_market_value", ...},
#   {"id": 11, "scenario_id": 1, "scenario_version": "1.0", "is_legacy": 0, "name": "small_market_value", ...},
# ]
```

### 查询标签（带场景信息）

```python
# 查询标签及其所属场景
tag = TagDefinitionModel.get_with_scenario(tag_definition_id)
# 返回: {
#   "id": 10,
#   "name": "large_market_value",
#   "scenario": {
#     "id": 1,
#     "name": "market_value_bucket",
#     "version": "1.0"
#   }
# }
```

## 与 Tag Scenario 的关系

- 通过 `scenario_id` 外键关联到 `tag_scenario` 表
- 一个 Scenario 可以产生多个 Tag Definitions
- Tag Definition 共享 Scenario 的版本和启用状态

## 与 Tag Value 的关系

- Tag Value 通过 `tag_definition_id` 外键关联到 Tag Definition
- 一个 Tag Definition 可以有多个 Tag Values（不同实体、不同日期）
