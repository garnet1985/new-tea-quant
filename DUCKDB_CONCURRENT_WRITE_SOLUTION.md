# DuckDB 并发写入问题解决方案

## 🔍 问题分析

### 问题描述

**核心问题**：DuckDB 是单连接写入数据库，多线程同时写入会导致写锁冲突。

**当前场景**：
- `renew` 操作使用多线程（`FuturesWorker`）
- 每个线程完成数据获取后立即保存（`after_single_task_execute`）
- 多个线程同时调用 `model.replace()` → `db.queue_write()` → `conn.execute()`
- **结果**：DuckDB 写锁冲突错误

### 受影响的模块

1. **KlineHandler** - `after_single_task_execute` 中保存 K 线数据
2. **CorporateFinanceHandler** - `after_single_task_execute` 中保存财务数据
3. **AdjFactorEventHandler** - `after_single_task_execute` 中保存复权事件
4. **RollingHandler** - `after_normalize` 中保存宏观数据
5. **其他 Handler** - 可能也有类似问题

### 问题根源

```python
# ❌ 当前实现（多线程并发写入）
async def after_single_task_execute(self, task_id, task_result, context):
    # 线程 1, 2, 3... 同时执行
    model.replace(data_list, unique_keys)  # 直接写入，导致锁冲突
```

---

## 🎯 解决方案设计

### 核心思路

**批量写入队列 + 写入线程分离**

1. **写入请求队列**：所有写入请求先进入队列
2. **批量收集**：达到阈值（如 1000 条）后触发写入
3. **单线程写入**：专门的写入线程执行实际写入
4. **请求/写入分离**：写入请求和实际写入完全分离

### 架构设计

```
多线程 Handler
    ↓
写入请求 → BatchWriteQueue (线程安全队列)
    ↓
批量收集 (达到阈值或超时)
    ↓
单线程写入器 → DuckDB (单连接写入)
```

---

## 📋 实施计划

### 阶段 1：创建批量写入队列系统（核心）

#### TODO-1: 创建 BatchWriteQueue 类
**文件**：`app/core/infra/db/batch_write_queue.py`

**功能要求**：
- [ ] 线程安全的写入队列
- [ ] 按表名分组收集数据
- [ ] 达到阈值（可配置）后触发批量写入
- [ ] 超时机制（避免数据长时间不写入）
- [ ] 支持刷新（强制立即写入）
- [ ] 支持等待写入完成

**接口设计**：
```python
class BatchWriteQueue:
    def __init__(self, db_manager, batch_size=1000, flush_interval=5.0):
        """
        Args:
            db_manager: DatabaseManager 实例
            batch_size: 批量写入阈值（默认 1000 条）
            flush_interval: 刷新间隔（秒，默认 5 秒）
        """
    
    def enqueue(self, table_name: str, data_list: List[Dict], unique_keys: List[str]):
        """将数据加入队列（非阻塞）"""
    
    def flush(self, table_name: str = None):
        """立即刷新指定表或所有表的数据"""
    
    def wait_for_writes(self, timeout: float = 30.0):
        """等待所有写入完成"""
    
    def shutdown(self):
        """关闭队列，刷新所有数据"""
```

**预计时间**：1-2 天

---

#### TODO-2: 集成到 DatabaseManager
**文件**：`app/core/infra/db/db_manager.py`

**修改点**：
- [ ] 添加 `BatchWriteQueue` 实例
- [ ] 修改 `queue_write` 方法，使用队列而不是直接写入
- [ ] 添加配置项（批量大小、刷新间隔）
- [ ] 添加 `flush()` 和 `wait_for_writes()` 方法

**预计时间**：0.5 天

---

### 阶段 2：修改 Handler 使用队列（逐个修改）

#### TODO-3: 修改 KlineHandler
**文件**：`app/core/modules/data_source/handlers/kline/handler.py`

**修改点**：
- [ ] `after_single_task_execute`：使用队列而不是直接保存
- [ ] `after_all_tasks_execute`：等待所有写入完成

**预计时间**：0.5 天

---

#### TODO-4: 修改 CorporateFinanceHandler
**文件**：`app/core/modules/data_source/handlers/corporate_finance/handler.py`

**修改点**：
- [ ] `after_single_task_execute`：使用队列而不是直接保存

**预计时间**：0.5 天

---

#### TODO-5: 修改 AdjFactorEventHandler
**文件**：`app/core/modules/data_source/handlers/adj_factor_event/handler.py`

**修改点**：
- [ ] `after_single_task_execute`：使用队列而不是直接保存

**预计时间**：0.5 天

---

#### TODO-6: 修改其他 Handler
**文件**：
- `app/core/modules/data_source/handlers/rolling/handler.py`
- `app/core/modules/data_source/handlers/price_indexes/handler.py`
- `app/core/modules/data_source/handlers/stock_index_indicator/handler.py`
- `app/core/modules/data_source/handlers/stock_index_indicator_weight/handler.py`

**修改点**：
- [ ] 所有直接调用 `model.replace()` 的地方改为使用队列

**预计时间**：1 天

---

### 阶段 3：配置和测试

#### TODO-7: 添加配置项
**文件**：`config/database/db_config.example.json`

**配置项**：
```json
{
  "duckdb": {
    "db_path": "data/stocks.duckdb",
    "threads": 4,
    "memory_limit": "8GB"
  },
  "batch_write": {
    "batch_size": 1000,
    "flush_interval": 5.0,
    "enable": true,
    "_comment": "批量写入配置：batch_size=批量写入阈值，flush_interval=刷新间隔（秒）"
  }
}
```

**预计时间**：0.5 天

---

#### TODO-8: 测试和验证
**测试内容**：
- [ ] 多线程 renew 操作测试
- [ ] 批量写入功能测试
- [ ] 写入性能测试
- [ ] 数据完整性验证

**预计时间**：1 天

---

## 🔧 技术实现细节

### BatchWriteQueue 实现要点

1. **线程安全**
   - 使用 `threading.Lock` 保护队列操作
   - 使用 `collections.defaultdict(list)` 按表分组

2. **批量触发机制**
   - 计数触发：达到 `batch_size` 后立即写入
   - 时间触发：`flush_interval` 秒后自动刷新

3. **写入线程**
   - 使用单独的线程执行写入
   - 使用 `threading.Event` 控制写入时机

4. **错误处理**
   - 写入失败时记录错误但不阻塞队列
   - 支持重试机制

---

## 📊 预期效果

### 性能影响

- **写入延迟**：增加 0-5 秒（等待批量收集）
- **写入性能**：提升（批量写入比单条写入快）
- **并发安全**：完全解决写锁冲突问题

### 配置建议

- **小数据量**（< 1000 条/次）：`batch_size=500, flush_interval=3.0`
- **中等数据量**（1000-10000 条/次）：`batch_size=1000, flush_interval=5.0`
- **大数据量**（> 10000 条/次）：`batch_size=5000, flush_interval=10.0`

---

## ⚠️ 注意事项

1. **数据丢失风险**
   - 队列中的数据在程序崩溃时可能丢失
   - 建议在关键操作后调用 `flush()` 确保数据写入

2. **内存占用**
   - 队列会缓存待写入数据
   - 需要根据数据量调整 `batch_size`

3. **写入顺序**
   - 批量写入不保证写入顺序
   - 如果顺序重要，需要特殊处理

---

## 🔗 相关文档

- [DuckDB 官方文档 - 并发](https://duckdb.org/docs/guides/python/concurrency)
- [数据库优化与迁移计划](./DATABASE_OPTIMIZATION_AND_MIGRATION_PLAN.md)
