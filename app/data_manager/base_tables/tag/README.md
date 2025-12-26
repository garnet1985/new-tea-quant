# Tag 标签元信息表

## 表结构

- **表名**: `tag`
- **主键**: `id` (自增)

## 字段说明

- `id` (BIGINT): 自增主键
- `name` (VARCHAR 64): 标签唯一代码（machine readable），如 `VOL_20D`, `MC_LARGE`
- `display_name` (VARCHAR 128): 标签显示名称（用户可见）
- `version` (VARCHAR 32): 版本号（用户显式声明，用于版本管理，如 "1.0", "2.0"）
- `description` (TEXT, 可选): Tag 描述（用于文档和说明，存储到数据库便于查询）
- `created_at` (DATETIME): 创建时间
- `updated_at` (DATETIME): 更新时间

**注意**：
- `is_enabled` 等配置字段存储在 calculator 的 config 文件中，不存储在数据库
- 版本管理由用户通过 `version` 字段显式声明，系统不自动检测配置变化

## 索引

- `idx_name`: `(name)` - 标签名称索引（用于快速查找，name 字段有 UNIQUE 约束）

## 使用场景

- 存储标签的元信息
- `name` 字段是 machine readable，用于代码中引用
- `display_name` 字段是用户可见的显示名称
- `version` 字段用于版本管理，用户显式声明版本号
- `description` 字段存储 tag 描述，便于查询和文档生成
- 标签的计算逻辑、参数等由 calculator 层自己管理（存储在配置文件中），不存储在数据库中

## 示例

```json
{
  "id": 1,
  "name": "VOL_20D",
  "display_name": "20日波动率",
  "is_enabled": 1
}
```
