# Worker 数量自动计算

## 概述

提供智能的 worker 数量计算，根据任务类型和 CPU 核心数自动选择最佳并行数。

---

## 使用方法

### 方式 1：自动计算（推荐）⭐

```python
from app.core.infra.worker.multi_process.process_worker import ProcessWorker

# 在模块中使用
max_workers = ProcessWorker.resolve_max_workers(
    max_workers='auto',  # ✅ 自动计算
    module_name='OpportunityEnumerator'
)

# 输出：✅ Worker 数量（自动）: 6 (模块=OpportunityEnumerator, 类型=mixed, CPU核心=8, 预留=2)
```

### 方式 2：手动指定

```python
max_workers = ProcessWorker.resolve_max_workers(
    max_workers=10,  # ✅ 手动指定
    module_name='OpportunityEnumerator'
)

# 输出：✅ Worker 数量（手动）: 10
```

### 方式 3：超过上限自动保护

```python
max_workers = ProcessWorker.resolve_max_workers(
    max_workers=99999,  # ⚠️ 太大了
    module_name='OpportunityEnumerator'
)

# 输出：⚠️ Worker 数量超过上限，已调整: 99999 → 16 (最大允许: 16)
```

---

## 配置管理

### 核心配置文件

**位置**：`core/config/worker.json`（⚠️ 核心区，不建议修改）

```python
MODULE_TASK_CONFIG = {
    'OpportunityEnumerator': {
        'task_type': TaskType.MIXED,      # 混合型
        'reserve_cores': 2                # 预留 2 个核心
    },
    'TagManager': {
        'task_type': TaskType.IO_INTENSIVE,  # I/O 密集型
        'reserve_cores': 1
    },
    'Simulator': {
        'task_type': TaskType.MIXED,
        'reserve_cores': 2
    }
}
```

### 任务类型说明

| 任务类型 | 说明 | Worker 数量计算 | 适用场景 |
|----------|------|----------------|---------|
| `CPU_INTENSIVE` | CPU 密集型 | `物理核心数 - 预留` | 大量计算、数学运算 |
| `IO_INTENSIVE` | I/O 密集型 | `逻辑核心数 - 预留 + 1` | 数据库查询、文件读写 |
| `MIXED` | 混合型 | `逻辑核心数 - 预留` | 既有计算也有 I/O |

---

## 计算规则

### CPU 密集型
```python
# 假设：8 核 16 线程，预留 2 核
物理核心数 = 16 / 2 = 8
Worker 数量 = 8 - 2 = 6
```

### I/O 密集型
```python
# 假设：8 核 16 线程，预留 1 核
Worker 数量 = 16 - 1 + 1 = 16
```

### 混合型（默认）
```python
# 假设：8 核 16 线程，预留 2 核
Worker 数量 = 16 - 2 = 14
```

### 保护规则
- **最小值**：1（至少 1 个 worker）
- **最大值**：`CPU 核心数 * 2`（防止过度并行）

---

## 在模块中集成

### 示例：OpportunityEnumerator

```python
class OpportunityEnumerator:
    
    @staticmethod
    def enumerate(
        strategy_name: str,
        start_date: str,
        end_date: str,
        stock_list: List[str],
        max_workers: Union[str, int] = 'auto'  # ⭐ 支持 'auto' 或数字
    ):
        # 解析 max_workers
        from app.core.infra.worker.multi_process.process_worker import ProcessWorker
        
        max_workers = ProcessWorker.resolve_max_workers(
            max_workers=max_workers,
            module_name='OpportunityEnumerator'  # ⭐ 模块名称
        )
        
        # 使用解析后的 max_workers
        ProcessWorker.execute(
            worker_class=...,
            job_payloads=...,
            max_workers=max_workers
        )
```

---

## 添加新模块配置

### Step 1: 在 worker_config.py 中添加

```python
MODULE_TASK_CONFIG = {
    # ... 现有配置 ...
    
    # 新增模块
    'MyNewModule': {
        'task_type': TaskType.MIXED,
        'reserve_cores': 2
    }
}
```

### Step 2: 在模块中使用

```python
max_workers = ProcessWorker.resolve_max_workers(
    max_workers='auto',
    module_name='MyNewModule'  # ⭐ 使用新模块名称
)
```

---

## 常见问题

**Q: 为什么我的 CPU 是 8 核，但自动选择了 6 个 worker？**  
A: 因为预留了 2 个核心给系统和其他进程，避免 CPU 100% 导致系统卡顿。

**Q: 我想手动指定 worker 数量怎么办？**  
A: 直接传数字即可：`max_workers=10`

**Q: 我传了 99999 个 worker，为什么只用了 16 个？**  
A: 系统自动保护，最多允许 `CPU 核心数 * 2`。

**Q: 如何修改模块的任务类型？**  
A: 修改 `core/config/worker.json`（⚠️ 核心配置，请谨慎）

**Q: 新增模块时忘记配置怎么办？**  
A: 会使用默认配置（MIXED 类型，预留 2 核）

---

## 设计原则

1. **自动优于手动**：默认 'auto'，让系统智能选择
2. **保护优于自由**：防止用户设置过大的值
3. **集中优于分散**：所有配置在一个地方
4. **隐藏优于暴露**：配置在核心区，不鼓励修改

---

**版本**：1.0  
**完成时间**：2026-01-08
