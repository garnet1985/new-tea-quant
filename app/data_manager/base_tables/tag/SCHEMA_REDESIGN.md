# Tag Schema 重新设计

## 📋 设计原则

1. **配置与数据分离**：配置字段（如 `is_enabled`）存储在 calculator 的 config 文件中，不存储在数据库
2. **用户显式声明**：版本管理由用户通过 `version` 字段显式声明，系统不自动检测配置变化
3. **最小改动**：只添加必要的字段和索引，避免过度设计

---

## 📊 最终 Schema 设计

### `tag` 表（改进版）

```json
{
  "name": "tag",
  "primaryKey": "id",
  "fields": [
    {
      "name": "id",
      "type": "bigint",
      "isRequired": true,
      "isAutoIncrement": true,
      "description": "自增主键"
    },
    {
      "name": "name",
      "type": "varchar",
      "length": 64,
      "isRequired": true,
      "description": "标签唯一代码（machine readable），如 VOL_20D, MC_LARGE"
    },
    {
      "name": "display_name",
      "type": "varchar",
      "length": 128,
      "isRequired": true,
      "description": "标签显示名称（用户可见）"
    },
    {
      "name": "version",
      "type": "varchar",
      "length": 32,
      "isRequired": true,
      "description": "版本号（用户显式声明，用于版本管理，如 \"1.0\", \"2.0\"）"
    },
    {
      "name": "description",
      "type": "text",
      "isRequired": false,
      "description": "Tag 描述（用于文档和说明，存储到数据库便于查询）"
    },
    {
      "name": "created_at",
      "type": "datetime",
      "isRequired": true,
      "default": "CURRENT_TIMESTAMP",
      "description": "创建时间"
    },
    {
      "name": "updated_at",
      "type": "datetime",
      "isRequired": true,
      "default": "CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
      "description": "更新时间"
    }
  ],
  "indexes": [
    {
      "name": "idx_name",
      "fields": ["name"],
      "description": "标签名称索引（用于快速查找，name 字段有 UNIQUE 约束）"
    }
  ]
}
```

**改进点**：
- ✅ 添加 `version` 字段（用户显式声明版本号）
- ✅ 添加 `description` 字段（存储 tag 描述，便于查询）
- ❌ 移除 `is_enabled` 字段（移到 config 文件中）
- ❌ 移除 `config_hash` 字段（版本管理由用户显式声明，不需要自动检测）

### `tag_value` 表（改进版）

```json
{
  "name": "tag_value",
  "primaryKey": ["entity_id", "tag_id", "as_of_date"],
  "fields": [
    {
      "name": "id",
      "type": "bigint",
      "isRequired": true,
      "isAutoIncrement": true,
      "description": "自增主键"
    },
    {
      "name": "entity_id",
      "type": "varchar",
      "length": 64,
      "isRequired": true,
      "description": "实体ID（默认是股票代码，如 000001.SZ，但支持其他实体类型以保持通用性）"
    },
    {
      "name": "tag_id",
      "type": "bigint",
      "isRequired": true,
      "description": "标签ID（引用 tag.id）"
    },
    {
      "name": "as_of_date",
      "type": "date",
      "isRequired": true,
      "description": "业务日期（tag 创建时间点）"
    },
    {
      "name": "start_date",
      "type": "date",
      "isRequired": false,
      "description": "tag 起始日期（时间切片 tag 用，连续 tag 的上一个结束时间）"
    },
    {
      "name": "end_date",
      "type": "date",
      "isRequired": false,
      "description": "tag 结束日期（时间切片 tag 用，连续 tag 的下一个开始时间的前一个时间点）"
    },
    {
      "name": "value",
      "type": "text",
      "isRequired": true,
      "description": "标签值（string，strategy 自己解释和解析）"
    },
    {
      "name": "calculated_at",
      "type": "datetime",
      "isRequired": true,
      "default": "CURRENT_TIMESTAMP",
      "description": "计算时间"
    }
  ],
  "indexes": [
    {
      "name": "idx_entity_date",
      "fields": ["entity_id", "as_of_date"],
      "description": "核心查询：给定实体+日期，快速获取所有标签"
    },
    {
      "name": "idx_tag_date",
      "fields": ["tag_id", "as_of_date"],
      "description": "辅助查询：某个标签在某个日期的所有实体"
    },
    {
      "name": "idx_entity_tag_date",
      "fields": ["entity_id", "tag_id", "as_of_date"],
      "description": "增量计算查询：优化查询每个 (entity_id, tag_id) 的最大 as_of_date，用于增量计算"
    }
  ]
}
```

**改进点**：
- ✅ 添加 `idx_entity_tag_date` 索引（优化增量计算查询）
- ✅ 优化 `entity_id` 的 description（明确默认是股票代码，但支持其他实体）

---

## 🔍 关键设计决策

### 1. **version 字段**

**用途**：
- 用户显式声明版本号（如 "1.0", "2.0"）
- 用于版本管理和追踪
- 当算法改变时，用户可以创建新版本（新的 name 或新的 version）

**使用场景**：
- 创建 tag 时：用户显式声明 version
- 更新 tag 时：如果算法改变，用户可以更新 version 或创建新 tag
- 版本管理：通过 version 字段追踪不同版本的 tag

**注意**：
- 版本管理由用户显式声明，系统不自动检测配置变化
- 如果用户想要保留旧版本，可以创建新 tag（新的 name）或更新 version

### 2. **description 字段**

**用途**：
- 存储 tag 的描述信息
- 便于查询和文档生成
- 可以从 config 文件的 `meta.description` 同步到数据库

**使用场景**：
- 创建 tag 时：从 config 文件读取 description 并存储
- 查询 tag 时：可以显示 description 帮助用户理解 tag 的用途

### 3. **is_enabled 移到 config**

**理由**：
- `is_enabled` 是配置字段，不是数据字段
- 配置应该存储在 config 文件中，便于版本控制和修改
- 数据库只存储元信息，不存储配置

**实现**：
- `is_enabled` 存储在 `config.py` 的 `meta` 或 `performance` 部分
- 系统读取 config 时获取 `is_enabled` 值
- 数据库不存储此字段

### 4. **config_hash 移除**

**理由**：
- 版本管理由用户通过 `version` 字段显式声明
- 不需要自动检测配置变化
- 简化设计，减少维护成本

**替代方案**：
- 用户通过更新 `version` 字段来声明版本变更
- 系统根据 `on_version_change` 配置处理版本变更（创建新 tag 或全量刷新）

### 5. **as_of_date 字段考虑（未添加）**

**考虑**：
- 是否需要在 `tag` 表添加 `last_calculated_date` 字段来记录整个 tag 的最后计算日期？

**分析**：
- 增量计算时，系统会查询每个 `(entity_id, tag_id)` 的最大 `as_of_date`
- 这个查询在 `tag_value` 表上进行，不需要在 `tag` 表存储
- 如果将来需要监控整个 tag 的计算进度，可以通过查询 `tag_value` 表获取

**结论**：
- 暂时不添加 `last_calculated_date` 字段
- 如果将来需要，可以通过查询 `tag_value` 表获取：`SELECT MAX(as_of_date) FROM tag_value WHERE tag_id = ?`
- 避免过度设计，保持 schema 简洁

### 6. **idx_entity_tag_date 索引**

**用途**：
- 优化增量计算查询：`SELECT MAX(as_of_date) FROM tag_value WHERE entity_id = ? AND tag_id = ?`
- 当前只有 `idx_entity_date`，查询时需要扫描多个 tag_id
- 新索引可以大幅提升查询性能

**性能影响**：
- 增量计算时，需要查询每个 (entity_id, tag_id) 的最大 as_of_date
- 新索引可以避免全表扫描，大幅提升查询性能

---

## ✅ 总结

### 必须的改进

1. **tag 表**：
   - ✅ 添加 `version` 字段（用户显式声明版本号）
   - ✅ 添加 `description` 字段（存储 tag 描述）
   - ❌ 移除 `is_enabled` 字段（移到 config）
   - ❌ 移除 `config_hash` 字段（版本管理由用户显式声明）

2. **tag_value 表**：
   - ✅ 添加 `idx_entity_tag_date` 索引（优化增量计算查询）
   - ✅ 优化 `entity_id` 的 description（明确默认是股票代码）

### 不需要的改进

1. ❌ 不需要添加 `last_calculated_date`（可以通过查询 tag_value 表获取）
2. ❌ 不需要添加 `calculation_status`（避免过度设计）
3. ❌ 不需要修改主键结构（当前主键设计合理）

---

## 📝 实施建议

1. **立即实施**：
   - 更新 `tag` 表 schema：添加 `version` 和 `description`，移除 `is_enabled` 和 `config_hash`
   - 更新 `tag_value` 表 schema：添加 `idx_entity_tag_date` 索引
   - 更新 config 文件：将 `is_enabled` 移到 config 中

2. **后续优化**（如果需要）：
   - 根据实际使用情况，考虑添加其他索引
   - 根据监控需求，考虑添加状态字段（但当前不需要）
