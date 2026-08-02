# System Actions — 快速开始

**模块：** `infra.system_actions` · **版本：** `0.2.0`

最短路径：读 pipeline 状态并清理勾选缓存。

---

## 最小示例

```python
from core.infra.system_actions import SystemActions

status = SystemActions.pipeline.read_status()
if not status["busy"]:
    print(SystemActions.cache.run(clear_userspace_ntq=True))
```

**预期结果：** idle 时清理 `userspace/.ntq/` 并返回 `{"ok": True, ...}`。

---

## 下一步

- [API.md](./API.md)

```bash
python3 -m pytest core/infra/system_actions/__test__/test_api.py -q
```
