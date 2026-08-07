# Architecture — infra.trace

**版本：** `0.2.0`

## 分层

```text
Trace (Facade, static API)
  ├── ask_permission / track / flush / start_background_drain
  ├── config / consent / types
        │
        ▼
  contracts.py      TraceEvent / TraceConfig / TraceConsent / FlushBudget
  core/defaults.py  TraceDefaults（内置 URL / 超时等唯一源）
  core/services/    Config · Consent · … · Client · Flush · Drain
```

## 开关来源（enabled）

```text
NTQ_TRACE_SKIP=1  >  NTQ_TRACE_ENABLED=0/1  >  userspace/system/config/trace_consent.json  >  false
```

## Tunables（target_url 等）

```text
NTQ_TRACE_ENDPOINT / NTQ_TRACE_TIMEOUT
  >  userspace/system/config/trace.json
  >  TraceDefaults（core/defaults.py）
```

不进 `core/default_config/`：tracing 为 opt-in，默认值与同意分离。

## 用法

```python
from core.infra.trace import Trace

Trace.track("install.complete", {"success": True})
Trace.flush(budget="standard")
# 内置默认 URL：
# Trace.types.TraceDefaults.TARGET_URL
```

## 数据流

0. 未取得同意 → `track` / `flush` 直接返回
1. `track`：sanitize → 本地 queue
2. `flush`：claim → POST `target_url` → 成功删 / 失败回队
3. CLI 预算 flush；BFF 后台 drain

## 边界

- 不采集主机名、真实用户 ID、策略/行情内容
- 失败静默；不阻塞业务
- 与 UI `traceId`（请求排障）无关
