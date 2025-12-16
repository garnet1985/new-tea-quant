# 复权因子事件表 Schema 设计文档

## 📋 设计概述

根据《复权因子优化方案 - 最终版》文档，重新设计了复权因子的数据库存储方案。

### 核心改进

1. **从每日存储改为事件存储**：只存储复权因子变化的日期（除权除息日）
2. **减少 98.8% 存储空间**：从 ~250 条/年/股 减少到 ~3 条/年/股
3. **支持精确计算**：存储与 AKShare 的差异，支持精确的前复权价格计算

---

## 📊 Schema 定义

### 表名

`adj_factor_events`

### 字段定义

| 字段名 | 类型 | 长度/精度 | 必填 | 默认值 | 说明 |
|-------|------|----------|------|--------|------|
| `id` | VARCHAR | 16 | ✅ | - | 股票代码（含市场后缀，如 000001.SZ） |
| `event_date` | DATE | - | ✅ | - | 除权除息日期（YYYY-MM-DD） |
| `adj_factor` | DECIMAL | 12,6 | ✅ | - | 复权因子 F(t)，用于计算前复权价格 |
| `constant_diff` | DECIMAL | 12,4 | ❌ | 0.0 | 与 AKShare 前复权价格的固定差异 |
| `created_at` | DATETIME | - | ✅ | CURRENT_TIMESTAMP | 记录创建时间 |
| `updated_at` | DATETIME | - | ✅ | CURRENT_TIMESTAMP ON UPDATE | 记录更新时间 |

### 主键

```sql
PRIMARY KEY (id, event_date)
```

确保每个股票的每个除权日只有一条记录。

### 索引

1. **唯一索引**：`idx_id_event_date (id, event_date)`
   - 用途：确保唯一性，快速查找特定事件

2. **普通索引**：`idx_id (id)`
   - 用途：按股票查询所有事件

3. **普通索引**：`idx_event_date (event_date)`
   - 用途：按日期查询所有股票的事件

4. **普通索引**：`idx_id_date_desc (id, event_date)`
   - 用途：用于查询最近的有效因子（`ORDER BY event_date DESC`）

---

## 🔧 使用场景

### 场景 1：查询指定日期的复权因子

```sql
SELECT adj_factor, constant_diff
FROM adj_factor_events
WHERE id = '000001.SZ' AND event_date <= '2024-12-12'
ORDER BY event_date DESC
LIMIT 1;
```

**说明**：查询 2024-12-12 及之前最近的一个复权因子事件。

### 场景 2：查询最新复权因子

```sql
SELECT adj_factor, constant_diff
FROM adj_factor_events
WHERE id = '000001.SZ'
ORDER BY event_date DESC
LIMIT 1;
```

### 场景 3：查询所有复权事件

```sql
SELECT *
FROM adj_factor_events
WHERE id = '000001.SZ'
ORDER BY event_date ASC;
```

### 场景 4：插入/更新复权事件

```sql
INSERT INTO adj_factor_events (id, event_date, adj_factor, constant_diff)
VALUES ('000001.SZ', '2024-06-14', 125.049600, 0.0000)
ON DUPLICATE KEY UPDATE
    adj_factor = VALUES(adj_factor),
    constant_diff = VALUES(constant_diff),
    updated_at = CURRENT_TIMESTAMP;
```

---

## 📈 数据示例

### 平安银行（000001.SZ）的复权事件

```sql
INSERT INTO adj_factor_events VALUES
('000001.SZ', '2023-12-12', 116.713000, 0.0000, 'initial', NOW(), NOW()),
('000001.SZ', '2024-06-14', 125.049600, 0.0000, 'dividend', NOW(), NOW()),
('000001.SZ', '2024-10-10', 127.784100, 0.0000, 'dividend', NOW(), NOW()),
('000001.SZ', '2025-06-12', 131.787800, 0.0000, 'dividend', NOW(), NOW()),
('000001.SZ', '2025-10-15', 134.579400, 0.0000, 'dividend', NOW(), NOW());
```

---

## 🔄 与旧表对比

### 旧表：`adj_factor`

```sql
CREATE TABLE adj_factor (
    id VARCHAR(16) NOT NULL,
    date VARCHAR(8) NOT NULL,      -- YYYYMMDD
    qfq FLOAT NOT NULL,             -- 前复权因子
    hfq FLOAT NOT NULL,             -- 后复权因子
    last_update TIMESTAMP,
    PRIMARY KEY (id, date)
);
```

**特点**：
- 每日存储（~250 条/年/股）
- 存储 qfq 和 hfq 两个因子
- 98.8% 的数据是重复的

### 新表：`adj_factor_events`

```sql
CREATE TABLE adj_factor_events (
    id VARCHAR(16) NOT NULL,
    event_date DATE NOT NULL,       -- YYYY-MM-DD
    adj_factor DECIMAL(12,6) NOT NULL,
    constant_diff DECIMAL(12,4) DEFAULT 0.0,
    created_at DATETIME,
    updated_at DATETIME,
    PRIMARY KEY (id, event_date)
);
```

**特点**：
- 只存储事件（~3 条/年/股）
- 只存储前复权因子（qfq）
- 存储与 AKShare 的差异
- 减少 98.8% 存储空间

---

## ✅ 设计验证

### 1. 数据完整性

- ✅ 主键确保唯一性
- ✅ 索引支持高效查询
- ✅ 字段类型和精度合理

### 2. 查询性能

- ✅ 单股票查询：`idx_id` 索引
- ✅ 日期范围查询：`idx_event_date` 索引
- ✅ 最近因子查询：`idx_id_date_desc` 索引

### 3. 扩展性

- ✅ `constant_diff` 字段支持 AKShare 差异修正
- ✅ `updated_at` 字段支持数据更新追踪

---

## 📝 实施检查清单

- [x] Schema 定义（`schema.json`）
- [x] Model 类实现（`model.py`）
- [x] 注册到 DataManager
- [x] 导出到 `__init__.py`
- [x] 更新枚举（`enums.py`）
- [x] 创建文档（README.md, MIGRATION.md）
- [ ] 数据库迁移脚本
- [ ] 数据验证脚本
- [ ] 单元测试
- [ ] 集成测试

---

## 📚 相关文档

- [复权因子优化方案](../../../../tmp/ADJ_FACTOR_OPTIMIZATION_FINAL.md)
- [数据库迁移指南](./MIGRATION.md)
- [使用说明](./README.md)
- [Model API](./model.py)

---

**设计日期：** 2025-12-15  
**状态：** ✅ Schema 设计完成，待实施

