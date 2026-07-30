# infra.trace

匿名 usage 上报。**默认关闭**，需用户明确同意（opt-in）。**静态 Facade**：

```python
from core.infra.trace import Trace

Trace.ask_permission(source="cli")   # 已有决定则跳过；TTY 下询问

Trace.track("install.complete", {
    "success": True,
    "error_code": "step_failed:resolve_deps",
    "msg": "pip install failed",
})
# meta（os / python_version / ntq_version / …）由模块自动附加
Trace.flush(budget="standard")
```

结构：

```text
contracts.py              TraceEvent / TraceConfig / TraceConsent / FlushBudget
trace.py                  Facade Trace
core/services/*Service    内部实现（类静态方法，不导出）
```

同意状态存 `userspace/system/config/trace_consent.json`；可调参数在模块内部，不进 `core/default_config/`。
强制关闭：`NTQ_TRACE_SKIP=1`（CI 用）。

详见 [docs/API.md](docs/API.md)。
