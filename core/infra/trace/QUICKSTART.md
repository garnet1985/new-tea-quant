# Trace — 快速开始

**模块：** `infra.trace` · **版本：** `0.1.0`

最短路径：询问同意后立刻上报一条事件。

---

## 最小示例

```python
from core.infra.trace import Trace

Trace.ask_permission(source="cli")
Trace.track("install.complete", {"success": True})
```

**预期结果：** 同意后事件立刻 POST；失败则入本地 queue，可由 `Trace.send` 或后台 drain 重试。

入队后再发送：

```python
Trace.queue("app.session_start", {})
print(Trace.send(budget="standard"))
```

---

## 改上报地址

- **改内置默认：** 编辑 [`core/defaults.py`](./core/defaults.py) 的 `TraceDefaults.TARGET_URL`
- **不改代码覆盖：** 环境变量 `NTQ_TRACE_ENDPOINT`，或 `userspace/system/config/trace.json` 的 `target_url`

---

## 下一步

- [API.md](./API.md)

```bash
python3 -m pytest core/infra/trace/__test__/test_api.py -q
```
