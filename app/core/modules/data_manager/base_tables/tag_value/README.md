# Tag Value 标签值表

## ⚠️ 重要更新

**字段已重命名为 `json_value` 并改为 JSON 类型**（支持键值对等结构化数据）

如果表已存在且字段名是 `value` 且类型是 TEXT/LONGTEXT，需要执行迁移：
```sql
ALTER TABLE tag_value CHANGE COLUMN value json_value JSON NOT NULL;
```

**注意**：虽然 `DESCRIBE tag_value` 可能显示 `longtext`，但实际类型是 JSON（可用 `JSON_TYPE(json_value)` 验证）。

详见 `migrate_to_json.sql` 文件。

## 表结构

- **表名**: `tag_value`
- **主键**: `(entity_id, tag_definition_id, as_of_date)`

## 字段说明

- `entity_type` (VARCHAR 32): 实体类型（如 "stock", "index" 等，默认 "stock"，方便未来扩展）
- `entity_id` (VARCHAR 64): 实体ID（默认是股票代码，如 000001.SZ，但支持其他实体类型以保持通用性）
- `tag_definition_id` (BIGINT): 标签定义ID（引用 tag_definition.id）
- `as_of_date` (DATE): 业务日期（tag 创建时间点）
- `start_date` (DATE, 可选): tag 起始日期（时间切片 tag 用，连续 tag 的上一个结束时间）
- `end_date` (DATE, 可选): tag 结束日期（时间切片 tag 用，连续 tag 的下一个开始时间的前一个时间点）
- `json_value` (JSON): 标签值（JSON 格式，支持键值对等结构化数据，strategy 自己解释和解析）
- `calculated_at` (DATETIME): 计算时间

**注意**：
- 使用联合主键 `(entity_id, tag_definition_id, as_of_date)`，不使用自增主键
- `entity_type` 字段用于区分不同类型的实体，方便未来扩展（如指数、板块等）
- `tag_definition_id` 引用 `tag_definition.id`，而不是旧的 `tag.id`

## 索引

- `idx_entity_date`: `(entity_id, as_of_date)` - 核心查询：给定实体+日期，快速获取所有标签
- `idx_tag_date`: `(tag_definition_id, as_of_date)` - 辅助查询：某个标签在某个日期的所有实体
- `idx_entity_tag_date`: `(entity_id, tag_definition_id, as_of_date)` - 增量计算查询：优化查询每个 (entity_id, tag_definition_id) 的最大 as_of_date

## 使用场景

### 策略回测核心查询

```python
# 获取某个实体在某个时刻的所有标签
tags = tag_value_model.get_entity_tags('600000.SH', '20250115')
# 返回: [
#   {"tag_definition_id": 1, "json_value": {"momentum": 0.23, "year_month": "202501"}, "start_date": None, "end_date": None},
#   {"tag_definition_id": 2, "json_value": {"category": "LARGE_CAP", "score": 85}, "start_date": "2025-01-01", "end_date": "2025-01-31"},
#   ...
# ]
# 注意：json_value 字段是 JSON 格式，自动解析为 Python dict/list，如果不是 JSON 则保持字符串格式（向后兼容）
```

**查询逻辑**：
- 查询 `as_of_date = 指定日期` 的 tag
- 或者查询 `start_date <= 指定日期 <= end_date` 的 tag（时间段 tag）

### 值存储格式

`json_value` 字段使用 **JSON 类型**，支持以下格式：

- **简单值**: `"0.23"` 或 `0.23` - 数值型标签（向后兼容字符串格式）
- **键值对**: `{"momentum": 0.1234, "year_month": "202501"}` - 多维度指标
- **数组**: `[1, 2, 3]` - 列表型数据
- **嵌套结构**: `{"metrics": {"roe": 0.15, "roa": 0.08}, "category": "LARGE_CAP"}` - 复杂结构

**使用示例**：
```python
# 保存 JSON 格式的 json_value
tag_value = {
    "entity_id": "000001.SZ",
    "tag_definition_id": 1,
    "as_of_date": "20250101",
    "json_value": {"momentum": 0.1234, "year_month": "202501"}  # 直接传入 dict
}

# 读取时自动解析为 Python dict/list
result = tag_value_model.get_tag_value("000001.SZ", 1, "20250101")
value = result['json_value']  # 自动是 dict 类型，无需手动 json.loads()
momentum = value['momentum']  # 直接访问
```

**向后兼容**：
- 如果 value 是字符串且不是有效 JSON，会保持原样（向后兼容旧数据）
- 如果 value 是字符串且是有效 JSON，会自动解析为 Python 对象

**注意**: `json_value` 字段的 JSON 格式由 strategy 自己定义，tag 系统只负责存储和查询，不关心具体结构。

### 时间段支持

Tag 支持三种时间段模式：

1. **时间点 tag**：`start_date` 和 `end_date` 都为 NULL，只有 `as_of_date`
2. **时间切片 tag**：`start_date` 和 `end_date` 都有值（如每月市值分类）
3. **连续 tag**：`start_date` 和 `end_date` 由系统自动处理（如牛市/熊市）

## 设计原则

- **存储层极简**: 只负责存和查，不关心怎么算
- **查询性能优先**: 索引针对"给定 entity_id + 时间点，查所有 tag"优化
- **计算解耦**: 计算复杂度由 calculator/strategy 处理，存储层不关心
- **通用性**: 支持多种实体类型（股票、指数等），不局限于股票
