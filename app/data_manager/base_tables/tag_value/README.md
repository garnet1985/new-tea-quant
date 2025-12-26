# Tag Value 标签值表

## 表结构

- **表名**: `tag_value`
- **主键**: `(entity_id, tag_id, as_of_date)`

## 字段说明

- `id` (BIGINT): 自增主键
- `entity_id` (VARCHAR 64): 实体ID（可以是股票代码、指数代码等）
- `tag_id` (BIGINT): 标签ID（引用 tag.id）
- `as_of_date` (DATE): 业务日期（tag 创建时间点）
- `start_date` (DATE, 可选): tag 起始日期（时间切片 tag 用，连续 tag 的上一个结束时间）
- `end_date` (DATE, 可选): tag 结束日期（时间切片 tag 用，连续 tag 的下一个开始时间的前一个时间点）
- `value` (TEXT): 标签值（string，strategy 自己解释和解析）
- `calculated_at` (DATETIME): 计算时间

## 索引

- `idx_entity_date`: `(entity_id, as_of_date)` - 核心查询：给定实体+日期，快速获取所有标签
- `idx_tag_date`: `(tag_id, as_of_date)` - 辅助查询：某个标签在某个日期的所有实体

## 使用场景

### 策略回测核心查询

```python
# 获取某个实体在某个时刻的所有标签
tags = tag_value_model.get_entity_tags('600000.SH', '20250115')
# 返回: [
#   {"tag_id": 1, "value": "0.23", "start_date": None, "end_date": None},
#   {"tag_id": 2, "value": "LARGE_CAP", "start_date": "2025-01-01", "end_date": "2025-01-31"},
#   ...
# ]
```

**查询逻辑**：
- 查询 `as_of_date = 指定日期` 的 tag
- 或者查询 `start_date <= 指定日期 <= end_date` 的 tag（时间段 tag）

### 值存储格式

- **数值型**: `"0.23"` - 波动率、动量等（strategy 自己解析为 float）
- **文本型**: `"LARGE_CAP"` - 分类、等级等
- **复杂结构**: `"{\"roe\":0.15,\"roa\":0.08}"` - 多维度指标（JSON string）

**注意**: `value` 是 string 类型，解释权完全在 strategy，tag 系统只负责存储和查询。

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
