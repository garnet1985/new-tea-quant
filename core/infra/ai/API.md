# AI 通道 API 文档

**模块：** `infra.ai` · **版本：** `0.1.0`  
**最低支持核心版本：** `>=0.6.0`

> 公开入口状态最高 **`beta`**。

快速上手见 [QUICKSTART.md](../QUICKSTART.md)（若有）。术语见 [glossary.yaml](../glossary.yaml)。

**公开约定：** 包根仅导出 `AiChannel`；类型走 `contracts.py`。实现位于 `core/`，禁止 deep-import。

---

## AiChannel

AI 通道门面：供应商发现、API Key 存取、裸补全调用。**只管 HTTP 通道，不管业务**——不做多轮对话、工具调度、系统提示词编排。

### list_providers

```python
AiChannel.list_providers() -> List[ProviderInfo]
```

- **状态：** `beta`
- **描述：** 发现 `userspace/extensions/ai/providers/` 下已配置的 AI 供应商，返回列表

### get_provider

```python
AiChannel.get_provider(provider_id: str) -> Optional[ProviderInfo]
```

- **状态：** `beta`
- **描述：** 按 ID 取单个供应商配置

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `provider_id` | `str` | ✓ | 供应商标识（目录名） |

### set_api_key

```python
AiChannel.set_api_key(provider_id: str, api_key: str) -> ProviderInfo
```

- **状态：** `beta`
- **描述：** 写入供应商 API Key 到本地 userspace，返回更新后的供应商配置

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `provider_id` | `str` | ✓ | 供应商标识 |
| `api_key` | `str` | ✓ | API Key 明文 |

### complete

```python
AiChannel.complete(
    messages: List[Dict[str, str]],
    *,
    provider_id: Optional[str] = None,
    max_tokens: int = 2048,
    temperature: float = 0.2,
    timeout_seconds: Optional[float] = None,
    extra_body: Optional[Dict[str, Any]] = None,
) -> CompleteResult
```

- **状态：** `beta`
- **描述：** 按给定消息做一次裸补全。不注入百科、不拼接系统提示词、不管多轮上下文。

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `messages` | `List[Dict[str, str]]` | ✓ | | OpenAI 兼容消息列表 |
| `provider_id` | `str?` | | `None` | 指定供应商；`None` 用默认 |
| `max_tokens` | `int` | | `2048` | 最大生成长度 |
| `temperature` | `float` | | `0.2` | 采样温度 |
| `timeout_seconds` | `float?` | | `None` | HTTP 超时 |
| `extra_body` | `Dict[str, Any]?` | | `None` | 透传到请求体的额外字段 |

---

## contracts

| 符号 | 说明 |
|------|------|
| `ProviderInfo` | 供应商配置（id / name / base_url / has_key） |
| `CompleteResult` | 补全结果（text / usage / raw） |
