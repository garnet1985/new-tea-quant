# System Actions — 快速开始

**模块：** `infra.system_actions` · **版本：** `0.2.0`

最短路径：读 pipeline 状态。

---

## 最小示例

```python
from core.infra.system_actions import SystemActions

status = SystemActions.pipeline.read_status()
print(status["busy"])
```

**预期结果：** 无长任务时 `busy` 为 `False`。

临时文件清理见 `devcli.py cgc/csc/cdc/cmc` 或 `core.infra.cli.dev.scripts.temp_cleanup`。

---

## 下一步

- [API.md](./API.md)

```bash
python3 -m pytest core/infra/system_actions/__test__/test_api.py -q
```
