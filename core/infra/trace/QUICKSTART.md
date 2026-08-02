# Trace — 快速开始

**模块：** `infra.trace` · **版本：** `0.2.0`

最短路径：询问同意后上报一条事件。

---

## 最小示例

```python
from core.infra.trace import Trace

Trace.ask_permission(source="cli")
Trace.track("install.complete", {"success": True})
print(Trace.flush(budget="standard"))
```

**预期结果：** 同意后事件入队并尝试发送；返回成功条数（整数）。

---

## 下一步

- [API.md](./API.md)

```bash
python3 -m pytest core/infra/trace/__test__/test_api.py -q
```
