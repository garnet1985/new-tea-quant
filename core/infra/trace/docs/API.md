# API — infra.trace

## Trace.ask_permission(source="cli") → bool

统一询问入口：

- decision 已存在 → 什么都不做，返回是否已授权
- 尚无 decision 且是交互式终端 → 询问（仅 `y` 同意，其他不同意），写入 `trace_consent.json`
- 非 TTY（CI / 管道 / BFF）→ 不询问、不写文件，返回 `False`，留给 UI

返回值：调用结束后是否允许 track。

```python
from core.infra.trace import Trace

Trace.ask_permission(source="cli_install")  # install
Trace.ask_permission(source="cli")          # 日常命令
```

已接入：`setup/cli_runtime.py`（安装前）、`core/infra/cli/user/main.py`（业务命令前；version/help 等 early 命令不打断）。

## Trace.track(event, body=None)

写入本地队列。

- **event**：稳定事件名，如 `install.complete`
- **body**：事件业务 JSON（`success` / `msg` / `error_code` / …），格式灵活但有体积与敏感键限制
- **meta**（自动）：`os`、`python_version`、`arch`、`ntq_version`；不要在 body 里传这些。请求 IP 只用于服务端 Flood，不入库。

## Trace.flush(budget=None)

发送队列。`budget`：`standard` | `extreme` | `None`(auto)。返回成功条数。

## Trace.start_background_drain()

长进程后台 drain（幂等）。

## Trace.config.is_enabled() / Trace.config.load()

读取是否启用与完整配置（只读）。

## Trace.consent.*

| API | 作用 |
|-----|------|
| `needs_ask()` | 尚无 decision → `True`（**UI 用这个判断是否弹窗**） |
| `is_decided()` | 是否已有 decision |
| `is_granted()` | 是否同意 |
| `grant` / `revoke` / `set` | 写入决定；`revoke` 会清空本地队列 |
| `read()` | `{decided, enabled, decided_at, source}` |

Decision 语义：

- 文件存在且 `enabled: true` → track
- 文件存在且 `enabled: false` → 不 track
- 文件不存在 → 需要问询（CLI 调 `ask_permission`；UI 调 `needs_ask` + checkbox + `set`）

UI 接入（Python 无法弹 React 对话框）：

```python
# BFF 暴露 consent 状态后，FED：
if Trace.consent.needs_ask():
    show_welcome_checkbox()
    Trace.consent.set(checkbox_value, source="ui")
```

## 环境变量

| 变量 | 作用 |
|------|------|
| `NTQ_TRACE_SKIP` | `1` 强制关闭（优先级最高，CI 用） |
| `NTQ_TRACE_ENABLED` | `0/1` 覆盖同意状态（开发 / 测试用） |
| `NTQ_TRACE_ENDPOINT` | 覆盖 target_url |
| `NTQ_TRACE_TIMEOUT` | 单次 POST 超时秒数 |

## 配置存放

- 可调参数：模块内部 `config_service._DEFAULTS`，不进 `core/default_config/`
- 用户同意：`userspace/system/config/trace_consent.json`

```json
{ "enabled": true, "decided_at": "2026-07-30T06:00:00Z", "source": "ui" }
```
