# 跨进程 Tracker 分析

## 当前设计

### 单进程 Tracker（已实现）
- **作用域**：单个 worker 实例（处理一个 entity 的所有日期）
- **生命周期**：从 worker 实例化到 process_entity() 完成
- **使用场景**：
  - 缓存上次处理的日期（避免重复查询数据库）
  - 缓存中间计算结果（跨日期共享）
  - 存储临时状态（如累计值、计数器等）

### 跨进程 Tracker（未实现）
- **作用域**：所有子进程之间共享
- **生命周期**：从 TagManager 开始执行到所有 jobs 完成
- **潜在使用场景**：
  - 共享市场级别的数据（如指数、行业数据）
  - 共享计算结果（避免重复计算）
  - 共享配置或元数据

## 价值分析

### ✅ 有价值的场景

#### 1. 市场级别数据共享
**场景**：多个进程都需要加载相同的市场数据（如指数、行业数据）

```python
# 示例：多个进程都需要计算市场平均PE
# 当前：每个进程都独立计算（重复计算）
# 优化：第一个进程计算后存入跨进程 tracker，其他进程直接使用
```

**价值**：
- 避免重复计算
- 减少数据库查询
- 提高性能

#### 2. 共享计算结果
**场景**：多个 entity 的计算都依赖某个全局指标

```python
# 示例：计算相对强度（需要知道市场平均收益率）
# 当前：每个进程都计算市场平均收益率
# 优化：第一个进程计算后共享，其他进程直接使用
```

**价值**：
- 避免重复计算
- 保证计算结果一致性

#### 3. 共享配置或元数据
**场景**：多个进程都需要相同的配置或元数据

```python
# 示例：交易日历、行业分类等
# 当前：每个进程都从数据库加载
# 优化：加载一次，所有进程共享
```

**价值**：
- 减少数据库查询
- 提高性能

### ❌ 没有价值的场景

#### 1. Entity 级别的数据
**原因**：当前设计是每个 entity 在一个进程中处理，不需要跨进程共享

#### 2. 已经优化的场景
**原因**：如果数据已经在数据库中，可以直接查询，不需要跨进程缓存

#### 3. 数据量小的场景
**原因**：如果数据量很小，重复加载的开销可以忽略

## 实现方式

### 方案 1: multiprocessing.Manager（推荐用于小数据）

```python
import multiprocessing as mp

class TagManager:
    def __init__(self):
        # 创建共享字典
        self.manager = mp.Manager()
        self.shared_tracker = self.manager.dict()
    
    def _execute_scenario(self, worker: BaseTagWorker):
        # 将 shared_tracker 传递给子进程
        # 在 payload 中添加 shared_tracker
        ...
```

**优点**：
- 实现简单
- 自动处理进程间同步

**缺点**：
- 性能较低（通过代理访问）
- 不适合大数据量

### 方案 2: multiprocessing.shared_memory（推荐用于大数据）

```python
import multiprocessing as mp
import multiprocessing.shared_memory as shm

class TagManager:
    def __init__(self):
        # 创建共享内存
        self.shared_memory = shm.SharedMemory(create=True, size=1024*1024)
    
    def _execute_scenario(self, worker: BaseTagWorker):
        # 将 shared_memory 名称传递给子进程
        ...
```

**优点**：
- 性能高
- 适合大数据量

**缺点**：
- 实现复杂
- 需要手动管理内存

### 方案 3: Redis/数据库（推荐用于持久化）

```python
class TagManager:
    def __init__(self):
        # 使用 Redis 作为跨进程缓存
        import redis
        self.redis_client = redis.Redis()
    
    def _execute_scenario(self, worker: BaseTagWorker):
        # 子进程通过 Redis 共享数据
        ...
```

**优点**：
- 持久化
- 可以跨机器共享
- 支持过期时间

**缺点**：
- 需要额外的依赖
- 网络开销

### 方案 4: 数据库缓存表（推荐用于当前架构）

```python
# 在数据库中创建缓存表
# 子进程通过数据库共享数据
# 优点：不需要额外依赖，利用现有数据库
# 缺点：有数据库查询开销
```

## 推荐方案

### 对于当前 Tag 系统

**建议：暂不实现跨进程 tracker**

**原因**：
1. **当前设计已经优化**：
   - 每个 entity 在一个进程中处理，数据已经共享
   - 市场级别数据可以通过数据库查询（已经有索引优化）

2. **复杂度 vs 收益**：
   - 实现跨进程 tracker 需要额外的同步机制
   - 可能引入死锁、数据竞争等问题
   - 收益有限（大部分数据已经是 entity 级别的）

3. **替代方案**：
   - 如果确实需要共享数据，可以在数据库层面优化（缓存表、索引等）
   - 或者使用 Redis（如果已经有 Redis 基础设施）

### 如果确实需要实现

**推荐使用方案 4（数据库缓存表）**：
- 利用现有数据库基础设施
- 不需要额外的依赖
- 可以持久化
- 实现简单

**实现示例**：
```python
# 在 TagManager 中
def _get_or_compute_market_data(self, key: str, compute_func):
    """获取或计算市场数据（跨进程共享）"""
    # 1. 尝试从数据库缓存表读取
    cached = self.tag_service.get_cached_data(key)
    if cached:
        return cached
    
    # 2. 如果不存在，计算并存入缓存
    result = compute_func()
    self.tag_service.save_cached_data(key, result)
    return result
```

## 总结

| 场景 | 是否有价值 | 推荐方案 |
|------|----------|---------|
| 市场级别数据共享 | ✅ 有 | 数据库缓存表或 Redis |
| 共享计算结果 | ✅ 有 | 数据库缓存表 |
| Entity 级别数据 | ❌ 无 | 不需要（已在单进程 tracker 中） |
| 配置或元数据 | ⚠️ 视情况 | 如果频繁使用，可以考虑 |

**结论**：对于当前 Tag 系统，跨进程 tracker 的价值有限，建议暂不实现。如果未来有明确需求，优先考虑数据库缓存表方案。
