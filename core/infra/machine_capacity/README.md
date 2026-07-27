# Machine Capacity（`infra.machine_capacity`）

机器 CPU / 内存容量探测，供 BacktestEngine 等调度器解析 worker 数与内存预算。

```python
from core.infra.machine_capacity import MachineInfo, MachineCapacity

capacity = MachineInfo.get_capacity(performance)
workers = MachineInfo.get_available_workers(capacity)
budget_mb = MachineInfo.worker_pool_budget_mb(capacity)
```

**边界**
- 负责：读本机 CPU / 内存，结合 `performance` 字段算预算与可用 worker
- 不负责：读 `worker.json`、dispatch plan、进程池执行（属 BE / 业务模块）
