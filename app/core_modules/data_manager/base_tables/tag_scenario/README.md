# Tag Scenario 业务场景表

## 表结构

- **表名**: `tag_scenario`
- **主键**: `id` (自增)

## 字段说明

- `id` (BIGINT): 自增主键
- `name` (VARCHAR 64): 业务场景唯一代码（如 `market_value_bucket`, `momentum_classifier`）
- `display_name` (VARCHAR 128, 可选): 业务场景显示名称
- `version` (VARCHAR 32): **版本号**（如 `1.0`, `2.0`），代表整个业务场景的算法版本
- `description` (TEXT, 可选): 业务场景描述
- `calculator_path` (VARCHAR 255, 可选): Calculator 文件路径
- `settings_path` (VARCHAR 255, 可选): Settings 文件路径
- `is_enabled` (TINYINT 1): 是否启用（控制整个业务场景是否启用，默认 1）
- `created_at` (DATETIME): 创建时间
- `updated_at` (DATETIME): 更新时间

## 索引

- `uk_name_version`: `(name, version)` UNIQUE - 同一场景的不同版本（允许一个场景有多个版本）
- `idx_name`: `(name)` - 业务场景名称索引

## 设计要点

1. **Version 在 Scenario 级别**：代表整个业务场景的算法版本
2. **一个 Scenario 可以有多个版本**：历史版本保留，便于比较和追溯
3. **is_enabled 控制整个 Scenario**：如果 Scenario 启用，所有 Tags 都会被计算
4. **name + version 唯一**：允许同一场景的不同版本共存

## 使用场景

### 创建业务场景

```python
# 创建新的业务场景
scenario = TagScenarioModel.create(
    name="market_value_bucket",
    display_name="市值分类",
    version="1.0",
    description="按市值阈值给股票打大小市值标签",
    calculator_path="app/core_modules/tag/scenarios/market_value_bucket/tag_worker.py",
    settings_path="app/core_modules/tag/scenarios/market_value_bucket/settings.py",
    is_enabled=True
)
```

### 版本管理

```python
# 查询某个场景的所有版本
scenarios = TagScenarioModel.get_by_name("market_value_bucket")
# 返回: [
#   {"id": 1, "name": "market_value_bucket", "version": "1.0", ...},
#   {"id": 2, "name": "market_value_bucket", "version": "2.0", ...},
# ]

# 查询最新版本
latest = TagScenarioModel.get_latest_version("market_value_bucket")
```

### 启用/禁用场景

```python
# 禁用场景（所有 Tags 都不会被计算）
TagScenarioModel.update(scenario_id, is_enabled=False)
```

## 与 Tag Definition 的关系

- 一个 Scenario 可以产生多个 Tag Definitions
- Tag Definition 通过 `scenario_id` 外键关联到 Scenario
- Tag Definition 共享 Scenario 的版本
