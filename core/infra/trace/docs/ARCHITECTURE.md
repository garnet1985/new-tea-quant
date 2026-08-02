# Architecture — infra.trace

**版本：** `0.2.0`

## 分层

```text
Trace (Facade, static API)
  ├── ask_permission / track / flush / start_background_drain
  ├── config.is_enabled / load
  └── consent.needs_ask / is_decided / is_granted / grant / revoke / set / read
        │
        ▼
  contracts.py     TraceEvent / TraceConfig / TraceConsent / FlushBudget
  core/services/   Config · Consent · Permission · Identity · Sanitize · Queue · Client · Track · Flush · Drain
```

## 开关来源

`enabled` 不是配置项，而是用户同意的结果，优先级：

```text
NTQ_TRACE_SKIP=1  >  NTQ_TRACE_ENABLED=0/1  >  userspace/system/config/trace_consent.json  >  false
```

可调参数（target_url / 超时 / 队列上限）写死在 `config_service._DEFAULTS`，不进 `core/default_config/`。

## 用法

全部静态，**不要** `new Trace()`：

```python
from core.infra.trace import Trace

Trace.track("install.complete", {"success": True})
Trace.flush(budget="standard")
```

`__init__.py` 只导出 `Trace`；`contracts.py` 可供内部/跨模块引用，但不作为 Facade 默认导出。

## 数据流

0. 未取得同意 → `track` / `flush` 直接返回，不落盘、不发网络
1. `track`：白名单/体积校验 body → 自动 meta → `TraceEvent` → `userspace/.ntq/trace/queue/*.json`
2. `flush`：按深度选 budget → claim inflight → POST → 成功删 / 失败回队
3. CLI 入口预算 flush；BFF 后台 drain + atexit

## 边界

- 不采集主机名、真实用户 ID、策略/行情内容
- 失败静默；不阻塞业务
- 与 UI `traceId`（请求排障）无关
