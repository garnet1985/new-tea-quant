# Updater — 快速开始

**模块：** `infra.updater` · **版本：** `0.1.0`

最短路径：把编排同步到 userspace，或跑 post-upgrade。

---

## 最小示例

```python
from pathlib import Path
from core.infra.updater import Updater

dest = Path("userspace/system/updater")
Updater.runtime.sync_orchestrator(dest)

result = Updater.post_upgrade.run(Path("."))
print(result.skipped, result.executed_count, result.action_ids)
```

**预期结果：** 生产会执行内置 `sync_userspace_updater`。

应用升级从运行时拷贝启动：`cli.py u` 或 `python userspace/system/updater/run_apply.py`。

---

## 下一步

- [API.md](./API.md)

```bash
python3 -m pytest core/infra/updater/__test__/test_api.py -q
```
