# Trace API 文档

**版本：** `0.2.0`  
**最低支持核心版本：** `>=0.4.1`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。  
> 所列门面入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Trace`；类型从 [`contracts.py`](./contracts.py) 导入。

---

## Trace

**描述：** 匿名 usage 上报门面（opt-in；静态 API，勿实例化）

#### ask_permission

`Trace.ask_permission(*, source: str = "cli") -> bool`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 已有决定则 no-op；TTY 询问；非 TTY 不写文件。返回是否已授权

#### track

`Trace.track(event: str, body: Mapping | None = None) -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 写入本地队列（无网络 I/O）

#### flush

`Trace.flush(*, budget: str | FlushBudget | None = None) -> int`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 按预算发送队列；返回成功条数

#### start_background_drain

`Trace.start_background_drain() -> None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** BFF/长进程后台 drain（幂等）

### config

`Trace.config.is_enabled() -> bool`  
`Trace.config.load() -> dict`

- **状态：** `beta`
- **描述：** 只读配置

### consent

| API | 作用 |
|-----|------|
| `needs_ask()` | 尚无 decision → `True`（UI 弹窗判断） |
| `is_decided()` / `is_granted()` | 是否已有决定 / 是否同意 |
| `grant` / `revoke` / `set` | 写入决定；`revoke` 清空本地队列 |
| `read()` | `{decided, enabled, decided_at, source}` |

- **状态：** `beta`

### 环境变量

| 变量 | 作用 |
|------|------|
| `NTQ_TRACE_SKIP` | `1` 强制关闭（CI） |
| `NTQ_TRACE_ENABLED` | `0/1` 覆盖同意状态 |
| `NTQ_TRACE_ENDPOINT` | 覆盖 target_url |
| `NTQ_TRACE_TIMEOUT` | POST 超时秒数 |

同意文件：`userspace/system/config/trace_consent.json`

---

## contracts

| 符号 | 说明 |
|------|------|
| `FlushBudget` | `standard` / `extreme` / `auto` |
| `TraceConsent` / `TraceConfig` / `TraceEvent` | 同意、配置、事件 schema |
