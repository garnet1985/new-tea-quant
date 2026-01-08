# Core Configuration

## worker_config.py

⚠️ **核心配置文件，不建议用户修改**

### 用途

定义各个模块的任务类型和预留核心数，供 `ProcessWorker` 自动计算 worker 数量时使用。

### 任务类型

| 类型 | 说明 | 适用场景 | Worker 计算策略 |
|------|------|---------|----------------|
| `CPU_INTENSIVE` | CPU 密集型 | 大量计算、数值处理 | 物理核心数 - 预留 |
| `IO_INTENSIVE` | I/O 密集型 | 数据库查询、文件读写、网络请求 | 逻辑核心数（可超配） |
| `MIXED` | 混合型 | 既有计算也有 I/O | 逻辑核心数 - 预留 |

### 配置示例

```python
MODULE_TASK_CONFIG = {
    'OpportunityEnumerator': {
        'task_type': TaskType.MIXED,        # 混合型
        'reserve_cores': 2                  # 预留 2 个核心
    },
    
    'TagManager': {
        'task_type': TaskType.IO_INTENSIVE,  # I/O 密集型
        'reserve_cores': 1                   # 预留 1 个核心
    }
}
```

### 如何添加新模块

1. 在 `MODULE_TASK_CONFIG` 中添加配置项
2. 确定任务类型（CPU_INTENSIVE / IO_INTENSIVE / MIXED）
3. 设置合理的预留核心数（1-2 个）

```python
'YourModule': {
    'task_type': TaskType.MIXED,
    'reserve_cores': 2
}
```

### Worker 数量计算公式

#### CPU_INTENSIVE（CPU 密集型）
```
workers = max(1, 物理核心数 - reserve_cores)
物理核心数 ≈ cpu_count / 2（假设超线程）
```

#### IO_INTENSIVE（I/O 密集型）
```
workers = max(2, cpu_count - reserve_cores + 1)
```

#### MIXED（混合型）
```
workers = max(1, cpu_count - reserve_cores)
```

### 示例

**8 核 16 线程的 CPU**：

| 任务类型 | reserve_cores | 计算公式 | 结果 |
|----------|--------------|---------|------|
| CPU_INTENSIVE | 2 | (16/2) - 2 | 6 |
| IO_INTENSIVE | 1 | 16 - 1 + 1 | 16 |
| MIXED | 2 | 16 - 2 | 14 |

---

## 如何使用

### 方式 1：自动计算（推荐）⭐

```python
# 使用 'auto'，自动根据模块配置计算
OpportunityEnumerator.enumerate(
    ...,
    max_workers='auto'  # ✅ 推荐
)
```

### 方式 2：手动指定

```python
# 手动指定数字（会自动保护，最多 2 倍 CPU 核心数）
OpportunityEnumerator.enumerate(
    ...,
    max_workers=10
)
```

### 方式 3：调试模式

```python
# 单进程，方便调试
OpportunityEnumerator.enumerate(
    ...,
    max_workers=1
)
```

---

## 保护机制

### 上限保护

```python
# 用户写 99999
max_workers = ProcessWorker.resolve_max_workers(99999, 'OpportunityEnumerator')
# 实际使用：32（假设 CPU 核心数 16）
```

### 下限保护

```python
# 用户写 0 或负数
max_workers = ProcessWorker.resolve_max_workers(0, 'OpportunityEnumerator')
# 实际使用：1
```

---

## 日志示例

### 自动计算时

```
✅ Worker 数量（自动）: 14 (模块=OpportunityEnumerator, 类型=mixed, CPU核心=16, 预留=2)
```

### 手动指定时

```
✅ Worker 数量（手动）: 10
```

### 超过上限时

```
⚠️ Worker 数量超过上限，已调整: 99999 → 32 (最大允许: 32)
```

---

## 注意事项

1. **不要随意修改此文件**：影响所有模块的性能
2. **谨慎调整 `reserve_cores`**：太少会导致系统卡顿，太多会浪费资源
3. **新增模块时记得添加配置**：否则会使用默认配置（MIXED，预留 2 核心）

---

**版本**：1.0  
**更新时间**：2026-01-08
