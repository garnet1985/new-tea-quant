# 测试用例 — `modules.assistant.core`

**模块：** `modules.assistant`  
**版本：** `0.1.0`  
**本文件位置：** `core/__test__/`

---

## Scope

供应商扫描已有单测。调用编排与协议客户端先记 case，后续统一补 UT。

## 边界

**负责**

- 合法 config 被发现
- 缺字段 / 无目录 / 禁用项 / 密钥探测
- 不硬编码 userspace 绝对路径

**不负责**

- 门面导出（见模块根 `__test__/test_api.py`）

**允许的测试类型（本目录）：** `unit`

---

## Scenario：catalog

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_empty_when_root_missing` | `test_provider_catalog.py` | 目录不存在返回空列表 |
| `test_discovers_valid_provider` | `test_provider_catalog.py` | 读 base_url / model / has_api_key |
| `test_skips_incomplete_config` | `test_provider_catalog.py` | 缺 model 的目录被跳过 |
| `test_keeps_disabled_provider` | `test_provider_catalog.py` | `enabled=False` 仍列出 |
| `test_paths_come_from_project_context` | `test_provider_catalog.py` | 真实 Path API 落在 extensions/assistant |

## Scenario：manager（待补 UT）

| Case | 文件 | 说明 |
|------|------|------|
| `test_chat_uses_ready_provider` | 待补 | 把 model / messages / key 交给客户端 |
| `test_chat_rejects_missing_key` | 待补 | 无密钥时失败 |
| `test_chat_rejects_unknown_provider` | 待补 | 未知 id 失败 |
| `test_chat_sends_history_and_system` | 待补 | messages 含系统提示 + 合法 history + 本轮 user |

## Scenario：protocol（待补 UT）

| Case | 文件 | 说明 |
|------|------|------|
| `test_complete_returns_assistant_text` | 待补 | 解析 choices 文本 |
| `test_http_error_uses_vendor_message` | 待补 | HTTP 错误用不含密钥的中文消息 |
| `test_network_error_is_wrapped` | 待补 | 网络错误包装为 AssistantError |
