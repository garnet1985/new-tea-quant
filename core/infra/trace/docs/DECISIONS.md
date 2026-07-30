# Decisions — infra.trace

## D0：仅 Facade 静态 API，不导出自由函数

对外只用 `Trace.track` / `Trace.flush` / `Trace.config.*`；实现落在 `*Service` 类上。不需要 `new Trace()`。

## D0.5：opt-in，默认关闭；同意状态存 system/config 而非 .ntq

`enabled` 默认 `false`，且不放进 `core/default_config/`——它不是运维旋钮，而是用户意愿，由 UI checkbox / CLI 首次运行写入
`userspace/system/config/trace_consent.json`。

选 `system/config` 而不是 `.ntq/`，因为 `devcli` 的 cache cleanup 会整体删除 `userspace/.ntq/`，同意记录会跟着丢，导致反复询问。

`is_decided()` / `needs_ask()` 与 `is_granted()` 分开：前者用于判断"要不要弹询问"，后者用于判断"能不能采集"。
CLI 统一走 `Trace.ask_permission()`（已有决定则 no-op）；UI 不能在 Python 里弹窗，用 `needs_ask()` + `set()`。
撤回同意时顺手清空本地队列，避免已入队数据在拒绝后仍被发出。

## D1：本地 outbox，不在 track 里发网络

保证 `track` 不阻塞业务；网站不可达时事件可在后续 CLI/BFF 补发。

## D2：不做客户端注册 / HMAC

公开分发客户端无法保存不可提取密钥；首版靠服务端 IP Flood + schema 校验。重复可接受。

## D3：匿名 installation_id，不用 IP/电脑名

IP 不稳定且不宜当用户身份；电脑名可能含 PII。`ntq_i_<uuid>` 存在 `userspace/.ntq/trace/`；清 `.ntq` 会重置身份。
请求 IP 只进 Drupal Flood（临时限流桶），**永不写入** `ntq_trace.meta`。

## D4：properties 白名单

未知键丢弃；禁止路径/token/原始 error_msg；允许稳定 `error_code`。

## D5：积压删最旧，不用长连接

用户量小；超限丢最旧 + 积压时 extreme 预算即可。
