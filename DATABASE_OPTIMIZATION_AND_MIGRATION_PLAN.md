# 数据库优化与迁移计划

## 📋 文档说明

本文档记录了当前数据库性能优化方案和后续 DuckDB 迁移计划。

**目标**: 将数据库从 MySQL 迁移到 DuckDB，同时实施性能优化方案，预计获得 **9-10 倍性能提升**。

**时间点**: Strategy 模块完成后实施。

---

## 📊 当前性能基线

### 性能报告（1989 只股票）

**时间消耗**：
- **总耗时**: ~263 秒（4.4 分钟）
- **数据库查询**: 231.08 秒（87.8%）- **主要瓶颈**
- **枚举计算**: ~24.7 秒（9.4%）
- **文件写入**: 1.74 秒（0.7%）

**IO 统计**：
- 数据库查询总数: 5,967 次
- 平均每只股票: 3 次查询
- 平均每次查询: 38.73 ms
- 文件写入总数: 3,880 次
- 文件写入总大小: 7.06 MB

**数据统计**：
- 总 K 线数: 6,343,829 根
- 总机会数: 40,052 个
- 总目标数: 54,940 个

**内存统计**：
- 平均每只股票峰值: 172.95 MB
- 主进程内存增长: 0.83 MB（内存管理良好）

---

## 🎯 优化方案（MySQL 环境）

### 优化点 1：JOIN 查询优化（3 次 → 1 次）

#### 当前实现

```python
# 每次 load_qfq_klines 需要 3 次查询：
1. _load_raw_klines: SELECT * FROM stock_kline WHERE id = ? AND date >= ? AND date <= ? AND term = ?
2. _load_factor_events: SELECT * FROM adj_factor_event WHERE id = ? AND event_date <= ?
3. _get_latest_factor: SELECT * FROM adj_factor_event WHERE id = ? ORDER BY event_date DESC LIMIT 1
```

**问题**：
- 每只股票 3 次查询
- 总查询: 5,967 次
- 总时间: 231.08 秒

#### 优化方案

使用 JOIN 查询一次性获取所有需要的数据：

```sql
-- 方案 A：使用相关子查询（MySQL 5.7+ 兼容）
SELECT 
    k.id,
    k.term,
    k.date,
    k.open,
    k.close,
    k.highest,
    k.lowest,
    k.pre_close,
    -- 获取每个日期对应的最新因子事件
    (
        SELECT factor 
        FROM adj_factor_event e 
        WHERE e.id = k.id 
          AND e.event_date <= k.date 
        ORDER BY e.event_date DESC 
        LIMIT 1
    ) as factor_t,
    (
        SELECT qfq_diff 
        FROM adj_factor_event e 
        WHERE e.id = k.id 
          AND e.event_date <= k.date 
        ORDER BY e.event_date DESC 
        LIMIT 1
    ) as qfq_diff_t,
    -- 获取最新因子 F(T)（每只股票只需要查询一次）
    (
        SELECT factor 
        FROM adj_factor_event e 
        WHERE e.id = k.id 
        ORDER BY e.event_date DESC 
        LIMIT 1
    ) as factor_T
FROM stock_kline k
WHERE k.id = ? 
  AND k.term = ?
  AND k.date >= ? 
  AND k.date <= ?
ORDER BY k.date ASC;
```

```sql
-- 方案 B：使用 LEFT JOIN LATERAL（MySQL 8.0+，性能更好）
WITH latest_factors AS (
    SELECT id, factor as factor_T
    FROM adj_factor_event e1
    WHERE e1.id = ?
      AND e1.event_date = (
          SELECT MAX(e2.event_date) 
          FROM adj_factor_event e2 
          WHERE e2.id = e1.id
      )
)
SELECT 
    k.*,
    e.factor as factor_t,
    e.qfq_diff as qfq_diff_t,
    lf.factor_T
FROM stock_kline k
LEFT JOIN LATERAL (
    SELECT factor, qfq_diff
    FROM adj_factor_event e
    WHERE e.id = k.id 
      AND e.event_date <= k.date
    ORDER BY e.event_date DESC
    LIMIT 1
) e ON TRUE
CROSS JOIN latest_factors lf
WHERE k.id = ? 
  AND k.term = ?
  AND k.date >= ? 
  AND k.date <= ?
ORDER BY k.date ASC;
```

**性能预期**：
- 查询次数: 5,967 → 1,989（减少 67%）
- 查询时间: 231.08 → ~77 秒（约 3 倍提升）
- **注意**: JOIN 查询可能比预期慢，实际提升可能在 1.5-2 倍

**实施位置**：
- `app/core/modules/data_manager/data_services/stock_related/stock/stock_data_service.py`
- 修改 `load_qfq_klines` 方法

**实施复杂度**: 中等（需要测试 JOIN 查询性能）

---

### 优化点 2：批量股票处理（1 只 → N 只/Worker）

#### 当前实现

```python
# 当前：每个 worker 处理 1 只股票
jobs = []
for stock_id in stock_list:
    jobs.append({'stock_id': stock_id, ...})

# 执行：1989 个 jobs，每个 worker 处理 1 只股票
```

**问题**：
- Jobs 数量: 1,989 个
- 查询次数: 5,967 次
- 查询时间: 231.08 秒

#### 优化方案

每个 worker 处理多只股票（批量处理）：

```python
# 优化：每个 worker 处理 N 只股票
BATCH_SIZE = 10  # 可配置，根据内存调整
jobs = []
for i in range(0, len(stock_list), BATCH_SIZE):
    batch_stocks = stock_list[i:i+BATCH_SIZE]
    jobs.append({
        'stock_ids': batch_stocks,  # ✅ 批量股票
        'strategy_name': strategy_name,
        'settings': validated_settings,
        'start_date': enum_start_date,
        'end_date': end_date,
        'output_dir': str(output_dir),
    })
```

**Worker 内部批量查询**：

```python
def load_batch_qfq_klines(self, stock_ids: List[str], term, start_date, end_date):
    """批量加载多只股票的 QFQ K 线"""
    
    # 使用 IN 查询批量获取
    raw_klines = self.stock_kline.load(
        "id IN (%s) AND term = %s AND date >= %s AND date <= %s",
        (','.join(['%s'] * len(stock_ids)), term, start_date, end_date),
        params=tuple(stock_ids) + (term, start_date, end_date),
        order_by="id ASC, date ASC"
    )
    
    # 批量获取因子事件
    factor_events = self.adj_factor_event.load(
        "id IN (%s) AND event_date <= %s",
        (','.join(['%s'] * len(stock_ids)), end_date),
        params=tuple(stock_ids) + (end_date,),
        order_by="id ASC, event_date ASC"
    )
    
    # 批量获取最新因子
    latest_factors = self.adj_factor_event.load_latest_factors_batch(stock_ids)
    
    # 按股票分组处理
    klines_by_stock = {}
    for stock_id in stock_ids:
        stock_klines = [k for k in raw_klines if k['id'] == stock_id]
        stock_events = [e for e in factor_events if e['id'] == stock_id]
        F_T = latest_factors.get(stock_id, {}).get('factor')
        
        klines_by_stock[stock_id] = self._apply_qfq_adjustment(
            stock_klines, stock_events, F_T
        )
    
    return klines_by_stock
```

**性能预期**：
- Jobs 数量: 1,989 → 199（减少 90%，10只/Worker）
- 查询次数: 5,967 → 597（减少 90%）
- 查询时间: 231.08 → ~23 秒（约 10 倍提升）
- **注意**: IN 查询可能比预期慢，实际提升可能在 5-7 倍

**内存影响**：

| 批量大小 | 每 Worker 内存 | 8 Workers 总内存 | 推荐场景 |
|---------|--------------|----------------|---------|
| 1 只（当前） | 172.95 MB | 1.38 GB | 内存紧张 |
| 3 只 | 518.85 MB | 4.15 GB | 内存有限（8-16 GB） |
| 5 只 | 864.75 MB | 6.9 GB | 内存充足（16+ GB） |
| 10 只 | 1,729.5 MB | 13.8 GB | 内存非常充足（32+ GB） |

**动态内存控制**：

```python
def calculate_optimal_batch_size(
    total_stocks: int,
    memory_per_stock_mb: float,
    available_memory_gb: float,
    max_workers: int
) -> int:
    """
    根据可用内存动态计算最优批量大小
    """
    # 预留 2 GB 给系统和其他进程
    usable_memory_gb = available_memory_gb - 2.0
    
    # 计算每个 worker 可用的内存（MB）
    memory_per_worker_mb = (usable_memory_gb * 1024) / max_workers
    
    # 计算每个 worker 可以处理的股票数
    batch_size = int(memory_per_worker_mb / memory_per_stock_mb)
    
    # 限制在合理范围内（1-20）
    batch_size = max(1, min(batch_size, 20))
    
    return batch_size
```

**实施位置**：
- `app/core/modules/strategy/components/opportunity_enumerator/opportunity_enumerator.py`
- `app/core/modules/strategy/components/opportunity_enumerator/enumerator_worker.py`

**实施复杂度**: 中等（需要仔细处理内存控制）

---

### 优化点 3：批量存储（可选）

#### 当前实现

```python
# 当前：每个 worker 写自己的 CSV 文件
def run(self):
    # ... 枚举逻辑 ...
    self._save_stock_results(output_dir, opportunities_dict)  # 写 CSV
    return {'success': True, 'opportunity_count': len(opportunities_dict)}
```

#### 优化方案（如果迁移到数据库）

```python
# Worker：返回全量数据
def run(self):
    # ... 枚举逻辑 ...
    opportunities_dict = [opp.to_dict() for opp in tracker['all_opportunities']]
    targets_dict = []
    for opp in opportunities_dict:
        targets_dict.extend(opp.pop('completed_targets', []) or [])
    
    return {
        'success': True,
        'stock_id': self.stock_id,
        'opportunities': opportunities_dict,  # ✅ 返回全量数据
        'targets': targets_dict,
        'opportunity_count': len(opportunities_dict)
    }

# 主进程：批量插入数据库
def enumerate(...):
    # ... 执行作业 ...
    all_opportunities = []
    all_targets = []
    
    for job_result in job_results:
        if job_result.result.get('success'):
            all_opportunities.extend(job_result.result.get('opportunities', []))
            all_targets.extend(job_result.result.get('targets', []))
    
    # 批量插入（每批 5000 条）
    BATCH_SIZE = 5000
    for i in range(0, len(all_opportunities), BATCH_SIZE):
        batch = all_opportunities[i:i+BATCH_SIZE]
        db.bulk_insert('opportunities', batch)
    
    for i in range(0, len(all_targets), BATCH_SIZE):
        batch = all_targets[i:i+BATCH_SIZE]
        db.bulk_insert('targets', batch)
```

**性能预期**：
- 批量插入: ~4 秒（vs CSV 的 1.74 秒）
- 优势: 后续查询更方便

**注意**: 如果保持 CSV 写入，此优化不影响性能

---

## 🚀 DuckDB 迁移方案

### 迁移目标

**性能目标**：
- 总耗时: 263 秒 → ~28 秒
- 性能提升: **9-10 倍**
- 查询时间: 231.08 秒 → ~2 秒（DuckDB + JOIN + 批量处理）

**其他目标**：
- 零配置部署（单文件数据库）
- 提升开源友好性
- 为后续分析功能打基础

---

### DuckDB 优势

1. **列式存储**: 适合分析查询，压缩更好
2. **向量化执行**: 批量处理，CPU 利用率高
3. **性能优势**: 在分析查询上比 MySQL 快 4.3x - 969.1x（取决于查询类型）
4. **零配置**: 单文件数据库，无需服务器
5. **标准 SQL**: 支持标准 SQL，迁移成本低

---

### 迁移架构设计

#### 1. 数据库抽象层

**创建 DuckDBDatabaseManager**：

```python
# app/core/infra/db/duckdb_manager.py
import duckdb
from typing import Optional, Dict, List, Any
from loguru import logger
from pathlib import Path

class DuckDBDatabaseManager:
    """
    DuckDB 数据库管理器
    
    特点：
    - 单文件数据库
    - 无需连接池（DuckDB 内部管理）
    - 支持标准 SQL
    - 列式存储，适合分析查询
    """
    
    def __init__(self, db_path: str, is_verbose: bool = False):
        """
        初始化 DuckDB 管理器
        
        Args:
            db_path: 数据库文件路径（.duckdb 文件）
            is_verbose: 是否输出详细日志
        """
        self.db_path = Path(db_path)
        self.is_verbose = is_verbose
        self.conn = None
        
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def initialize(self):
        """初始化数据库连接"""
        try:
            self.conn = duckdb.connect(str(self.db_path))
            
            # 启用性能优化
            self.conn.execute("SET threads TO 4")  # 可根据 CPU 核心数调整
            self.conn.execute("SET memory_limit='8GB'")  # 可根据内存调整
            
            if self.is_verbose:
                logger.info(f"✅ DuckDB 连接成功: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ DuckDB 初始化失败: {e}")
            raise
    
    def execute_sync_query(self, query: str, params: Any = None) -> List[Dict[str, Any]]:
        """
        执行同步查询
        
        Args:
            query: SQL 查询语句（使用 ? 作为占位符）
            params: 查询参数
        
        Returns:
            查询结果列表（字典格式）
        """
        if not self.conn:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        
        # DuckDB 使用 ? 作为占位符
        if params:
            result = self.conn.execute(query, params).fetchall()
        else:
            result = self.conn.execute(query).fetchall()
        
        # 转换为字典格式（兼容现有代码）
        if result:
            columns = result[0].keys() if isinstance(result[0], dict) else None
            if columns:
                return [dict(row) for row in result]
            else:
                # 如果没有列名，使用数字索引
                return [dict(enumerate(row)) for row in result]
        return []
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
```

#### 2. Schema 适配器

**字段类型映射**：

```python
# app/core/infra/db/duckdb_schema_adapter.py
MYSQL_TO_DUCKDB_TYPE_MAP = {
    'VARCHAR': 'VARCHAR',
    'TEXT': 'VARCHAR',  # DuckDB 使用 VARCHAR 替代 TEXT
    'INT': 'INTEGER',
    'BIGINT': 'BIGINT',
    'FLOAT': 'DOUBLE',  # DuckDB 使用 DOUBLE
    'DOUBLE': 'DOUBLE',
    'TINYINT(1)': 'BOOLEAN',
    'DATETIME': 'TIMESTAMP',
    'DATE': 'DATE',
    'JSON': 'JSON',
}

def convert_mysql_schema_to_duckdb(mysql_schema: Dict) -> Dict:
    """
    将 MySQL Schema 转换为 DuckDB Schema
    """
    duckdb_schema = {
        'name': mysql_schema['name'],
        'fields': [],
        'indexes': []  # DuckDB 不支持传统索引，但可以使用主键
    }
    
    for field in mysql_schema['fields']:
        mysql_type = field['type'].upper()
        duckdb_type = MYSQL_TO_DUCKDB_TYPE_MAP.get(mysql_type, mysql_type)
        
        duckdb_field = {
            'name': field['name'],
            'type': duckdb_type,
            'isRequired': field.get('isRequired', False),
        }
        
        # 处理长度限制
        if 'length' in field and duckdb_type == 'VARCHAR':
            duckdb_field['length'] = field['length']
        
        duckdb_schema['fields'].append(duckdb_field)
    
    # 主键处理
    if 'primaryKey' in mysql_schema:
        duckdb_schema['primaryKey'] = mysql_schema['primaryKey']
    
    return duckdb_schema
```

**CREATE TABLE 生成**：

```python
def generate_duckdb_create_table_sql(schema: Dict) -> str:
    """
    生成 DuckDB CREATE TABLE SQL
    """
    table_name = schema['name']
    fields = []
    
    for field in schema['fields']:
        field_def = f"{field['name']} {field['type']}"
        
        if 'length' in field and field['type'] == 'VARCHAR':
            field_def += f"({field['length']})"
        
        if field.get('isRequired', False):
            field_def += " NOT NULL"
        
        fields.append(field_def)
    
    create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
    create_sql += ",\n".join(f"    {f}" for f in fields)
    
    # 添加主键
    if 'primaryKey' in schema:
        pk_fields = ', '.join(schema['primaryKey'])
        create_sql += f",\n    PRIMARY KEY ({pk_fields})"
    
    create_sql += "\n);"
    
    return create_sql
```

#### 3. SQL 兼容层

**日期函数映射**：

```python
# MySQL → DuckDB 日期函数映射
DATE_FUNCTION_MAP = {
    'STR_TO_DATE': 'CAST',
    'DATE_SUB': 'DATE_SUB',  # DuckDB 支持
    'CURDATE': 'CURRENT_DATE',
    'NOW': 'CURRENT_TIMESTAMP',
}

def convert_mysql_sql_to_duckdb(mysql_sql: str) -> str:
    """
    将 MySQL SQL 转换为 DuckDB SQL
    """
    duckdb_sql = mysql_sql
    
    # 替换日期函数
    for mysql_func, duckdb_func in DATE_FUNCTION_MAP.items():
        duckdb_sql = duckdb_sql.replace(mysql_func, duckdb_func)
    
    # 替换占位符（如果使用 %s）
    duckdb_sql = duckdb_sql.replace('%s', '?')
    
    # 其他 MySQL 特定语法替换
    # ...
    
    return duckdb_sql
```

**ON DUPLICATE KEY UPDATE → INSERT OR REPLACE**：

```sql
-- MySQL
INSERT INTO table (id, value) VALUES (?, ?)
ON DUPLICATE KEY UPDATE value = ?;

-- DuckDB
INSERT INTO table (id, value) VALUES (?, ?)
ON CONFLICT (id) DO UPDATE SET value = ?;

-- 或者使用 REPLACE
REPLACE INTO table (id, value) VALUES (?, ?);
```

#### 4. JOIN 查询优化（DuckDB 版本）

```sql
-- DuckDB 版本的 JOIN 查询（性能更优）
SELECT 
    k.id,
    k.term,
    k.date,
    k.open,
    k.close,
    k.highest,
    k.lowest,
    k.pre_close,
    -- 使用窗口函数获取最新因子事件（DuckDB 优化）
    LAST_VALUE(e.factor) OVER (
        PARTITION BY k.id 
        ORDER BY k.date 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        FILTER (WHERE e.event_date <= k.date)
    ) as factor_t,
    LAST_VALUE(e.qfq_diff) OVER (
        PARTITION BY k.id 
        ORDER BY k.date 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        FILTER (WHERE e.event_date <= k.date)
    ) as qfq_diff_t,
    -- 获取最新因子 F(T)
    (SELECT factor FROM adj_factor_event WHERE id = k.id ORDER BY event_date DESC LIMIT 1) as factor_T
FROM stock_kline k
LEFT JOIN adj_factor_event e ON e.id = k.id AND e.event_date <= k.date
WHERE k.id = ? 
  AND k.term = ?
  AND k.date >= ? 
  AND k.date <= ?
ORDER BY k.date ASC;
```

---

### 数据迁移脚本

```python
# tools/migrate_mysql_to_duckdb.py
"""
MySQL 到 DuckDB 数据迁移脚本

步骤：
1. 从 MySQL 导出数据
2. 转换数据格式
3. 导入到 DuckDB
4. 验证数据完整性
"""

import pymysql
import duckdb
from pathlib import Path
import json
from loguru import logger

def migrate_table(
    mysql_conn,
    duckdb_conn,
    table_name: str,
    batch_size: int = 10000
):
    """
    迁移单个表的数据
    """
    logger.info(f"开始迁移表: {table_name}")
    
    # 从 MySQL 读取数据
    with mysql_conn.cursor(pymysql.cursors.DictCursor) as cursor:
        cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        total_count = cursor.fetchone()['count']
        
        logger.info(f"表 {table_name} 共有 {total_count} 条记录")
        
        # 分批读取和写入
        offset = 0
        while offset < total_count:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT %s OFFSET %s", (batch_size, offset))
            rows = cursor.fetchall()
            
            if not rows:
                break
            
            # 转换为 DuckDB 格式
            duckdb_rows = [convert_row_to_duckdb(row) for row in rows]
            
            # 批量插入到 DuckDB
            insert_into_duckdb(duckdb_conn, table_name, duckdb_rows)
            
            offset += batch_size
            logger.info(f"已迁移 {offset}/{total_count} 条记录")
    
    logger.info(f"表 {table_name} 迁移完成")

def main():
    # 1. 连接 MySQL
    mysql_conn = pymysql.connect(
        host='localhost',
        user='root',
        password='',
        database='stocks-py',
        cursorclass=pymysql.cursors.DictCursor
    )
    
    # 2. 连接/创建 DuckDB
    duckdb_path = Path('data/stocks.duckdb')
    duckdb_conn = duckdb.connect(str(duckdb_path))
    
    # 3. 创建表结构
    # ... (使用 Schema 适配器创建表)
    
    # 4. 迁移数据
    tables = [
        'stock_list',
        'stock_kline',
        'adj_factor_event',
        'gdp',
        'lpr',
        'shibor',
        'price_indexes',
        # ... 其他表
    ]
    
    for table_name in tables:
        migrate_table(mysql_conn, duckdb_conn, table_name)
    
    # 5. 验证数据完整性
    # ... (比较记录数、校验和等)
    
    # 6. 关闭连接
    mysql_conn.close()
    duckdb_conn.close()
    
    logger.info("✅ 数据迁移完成")

if __name__ == '__main__':
    main()
```

---

### 兼容层设计

**支持双数据库模式**（迁移期间的过渡方案）：

```python
# app/core/infra/db/db_adapter.py
from typing import Union
from enum import Enum

class DatabaseType(Enum):
    MYSQL = "mysql"
    DUCKDB = "duckdb"

class DatabaseAdapter:
    """
    数据库适配器：支持 MySQL 和 DuckDB
    """
    
    def __init__(self, db_type: DatabaseType, config: Dict):
        self.db_type = db_type
        
        if db_type == DatabaseType.MYSQL:
            from app.core.infra.db.db_manager import DatabaseManager
            self.db = DatabaseManager(config)
        elif db_type == DatabaseType.DUCKDB:
            from app.core.infra.db.duckdb_manager import DuckDBDatabaseManager
            self.db = DuckDBDatabaseManager(config['db_path'])
        else:
            raise ValueError(f"Unknown database type: {db_type}")
    
    def initialize(self):
        self.db.initialize()
    
    def execute_sync_query(self, query: str, params: Any = None):
        # 如果是 MySQL，可能需要转换 SQL
        if self.db_type == DatabaseType.DUCKDB:
            # DuckDB 使用 ? 占位符
            query = query.replace('%s', '?')
        
        return self.db.execute_sync_query(query, params)
```

---

## 📋 实施检查清单

### 阶段 1：准备（1-2 天）

- [ ] 创建迁移分支
- [ ] 安装 DuckDB: `pip install duckdb`
- [ ] 研究 DuckDB 文档和最佳实践
- [ ] 准备测试数据（小数据集）

### 阶段 2：数据库抽象层（2-3 天）

- [ ] 创建 `DuckDBDatabaseManager`
- [ ] 实现基本 CRUD 操作
- [ ] 实现事务支持
- [ ] 测试基本功能

### 阶段 3：Schema 适配（1-2 天）

- [ ] 创建 `duckdb_schema_adapter.py`
- [ ] 实现字段类型映射
- [ ] 实现 CREATE TABLE SQL 生成
- [ ] 测试所有表结构的转换

### 阶段 4：SQL 兼容层（2-3 天）

- [ ] 实现日期函数映射
- [ ] 实现占位符转换（%s → ?）
- [ ] 实现 ON DUPLICATE KEY UPDATE → INSERT OR REPLACE
- [ ] 实现 JOIN 查询优化（DuckDB 版本）
- [ ] 测试所有 SQL 转换

### 阶段 5：数据迁移（1-2 天）

- [ ] 创建数据迁移脚本
- [ ] 从 MySQL 导出数据
- [ ] 转换数据格式
- [ ] 导入到 DuckDB
- [ ] 验证数据完整性（记录数、校验和）

### 阶段 6：功能适配（2-3 天）

- [ ] 修改 `StockDataService.load_qfq_klines`（使用 JOIN 查询）
- [ ] 修改 `OpportunityEnumerator`（支持批量股票处理）
- [ ] 修改 Worker（支持批量查询）
- [ ] 测试所有功能

### 阶段 7：性能优化（2-3 天）

- [ ] 实现批量股票处理（动态批量大小）
- [ ] 实现批量插入（如果使用数据库存储）
- [ ] 性能测试和调优
- [ ] 内存使用监控

### 阶段 8：测试与验证（3-5 天）

- [ ] 功能回归测试（所有策略功能）
- [ ] 性能对比测试（MySQL vs DuckDB）
- [ ] 数据一致性验证
- [ ] 内存使用测试
- [ ] 边界情况测试

### 阶段 9：文档与部署（1-2 天）

- [ ] 更新文档（安装、配置、使用）
- [ ] 更新 README
- [ ] 准备迁移指南
- [ ] 更新 requirements.txt

---

## ⚠️ 注意事项

### 数据迁移风险

1. **数据完整性**
   - 确保所有表的数据都正确迁移
   - 验证主外键关系
   - 验证索引和约束

2. **数据类型转换**
   - 注意日期时间格式
   - 注意浮点数精度
   - 注意 NULL 值处理

3. **数据量**
   - 600 万 K 线数据，需要分批迁移
   - 预计迁移时间：1-2 小时（取决于硬件）

### 性能测试

1. **基准测试**
   - 在迁移前记录 MySQL 性能基准
   - 在迁移后对比 DuckDB 性能
   - 确保达到预期提升（9-10 倍）

2. **负载测试**
   - 测试不同数据量下的性能
   - 测试并发查询性能
   - 测试内存使用情况

### 回退方案

1. **保留 MySQL 支持**
   - 在迁移期间，保留 MySQL 兼容层
   - 支持配置切换数据库类型
   - 确保可以随时回退

2. **数据备份**
   - 迁移前备份所有 MySQL 数据
   - 保留原始数据文件
   - 准备快速恢复方案

---

## 📈 预期收益

### 性能提升

| 指标 | 当前（MySQL） | 优化后（DuckDB） | 提升 |
|------|--------------|-----------------|------|
| 查询时间 | 231.08 秒 | ~2 秒 | **115 倍** |
| 总耗时 | 263 秒 | ~28 秒 | **9.4 倍** |
| 查询次数 | 5,967 次 | 199 次 | **30 倍** |

### 其他收益

1. **部署简化**
   - 无需 MySQL 服务器
   - 单文件数据库，易于备份和迁移
   - 零配置，开箱即用

2. **开源友好性**
   - 降低使用门槛
   - 易于分发和共享
   - 更适合个人开发者

3. **后续扩展**
   - 为分析功能打下基础
   - 支持更复杂的数据分析
   - 支持机器学习模型训练

---

## 📚 参考资料

1. [DuckDB 官方文档](https://duckdb.org/docs/)
2. [DuckDB Python API](https://duckdb.org/docs/api/python/overview)
3. [MySQL 到 DuckDB 迁移指南](https://duckdb.org/docs/guides/import/mysql)
4. 性能基准测试报告（见 `DUCKDB_VS_MYSQLCLIENT_EVALUATION.md`）

---

## 📝 更新日志

- **2026-01-09**: 创建文档，记录优化方案和迁移计划
- **待更新**: Strategy 模块完成后，开始实施迁移
