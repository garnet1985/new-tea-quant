# Machine Capacity — 快速开始

**模块：** `infra.machine_capacity` · **版本：** `0.2.0`

```python
from core.infra.machine_capacity import MachineInfo
from core.infra.machine_capacity.contracts import MachineCapacity

performance = {"reserve_cores": 1, "memory_budget_mb": 4096, "memory_floor_mb": 1024}
capacity: MachineCapacity = MachineInfo.get_capacity(performance)
print(MachineInfo.get_available_workers(capacity), MachineInfo.worker_pool_budget_mb(capacity))
```

```bash
python3 -m pytest core/infra/machine_capacity/__test__/test_api.py -q
```
