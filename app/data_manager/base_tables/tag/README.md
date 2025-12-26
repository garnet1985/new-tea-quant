# Tag 标签元信息表

## 表结构

- **表名**: `tag`
- **主键**: `id` (自增)

## 字段说明

- `id` (BIGINT): 自增主键
- `name` (VARCHAR 64): 标签唯一代码（machine readable），如 `VOL_20D`, `MC_LARGE`
- `display_name` (VARCHAR 128): 标签显示名称（用户可见）
- `is_enabled` (TINYINT 1): 是否启用
- `created_at` (DATETIME): 创建时间
- `updated_at` (DATETIME): 更新时间

## 使用场景

- 存储标签的元信息
- `name` 字段是 machine readable，用于代码中引用
- `display_name` 字段是用户可见的显示名称
- 标签的计算逻辑、参数等由 calculator 层自己管理，不存储在数据库中

## 示例

```json
{
  "id": 1,
  "name": "VOL_20D",
  "display_name": "20日波动率",
  "is_enabled": 1
}
```
