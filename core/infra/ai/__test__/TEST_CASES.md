# 测试用例 — `infra.ai` 公开 API

**模块：** `infra.ai` · **版本：** `0.2.0`

**最低支持核心版本：** `>=0.6.0`
**本文件位置：** `__test__/`

---

## Scope

验证 `AiChannel` 公开契约与消息校验辅助逻辑。

## 边界

**负责**

- Facade 导出与 `API.md` 入口可调用性
- 空消息拒绝、`ProviderInfo` 字段形状
- 可选 live userspace 发现 / 补全
- `_completion_messages` 超限裁剪

**不负责**

- 官网会员通道（`modules.ntq_external`）
- 真实供应商 HTTP 正确性（除 `NTQ_AI_LIVE=1` 可选冒烟）

**允许的测试类型（本目录）：** `api` · 包内 unit（消息裁剪）

---

## Scenario：Facade 与契约

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_facade_export` | `test_api.py` | 包根仅导出 AiChannel |
| `test_list_and_get_callable` | `test_api.py` | 公开方法可调用；非法 id 返回 None |
| `test_complete_rejects_blank_messages` | `test_api.py` | 空消息抛 AiError |
| `test_provider_info_fields` | `test_api.py` | ProviderInfo 字段且无明文 key |
| `test_live_userspace_discovers_provider` | `test_api.py` | 有 zhipu 时能发现 |
| `test_live_complete_pong` | `test_api.py` | `NTQ_AI_LIVE=1` 时真实补全 |

---

## Scenario：消息裁剪

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_empty_still_rejected` | `test_completion_messages.py` | 空列表仍拒绝 |
| `test_trim_keeps_system_and_tail` | `test_completion_messages.py` | 超限保留 system + 尾部 |
| `test_under_limit_unchanged` | `test_completion_messages.py` | 未超限原样返回 |
