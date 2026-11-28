# AI 通道 API 文档

**模块：** `infra.ai` · **版本：** `0.2.0`

**最低支持核心版本：** `>=0.6.0`

> 公开入口状态最高 **`beta`**。

术语见 [glossary.yaml](./glossary.yaml)。官网会员补全见 `modules.ntq_external.ai.member_channel.complete`。

**公开约定：** 包根仅导出 `AiChannel`；类型走 `contracts.py`。实现位于 `core/`，禁止 deep-import。

---

## AiChannel

本机 AI 通道门面：供应商发现、API Key 存取、裸补全。**不走官网会员。**

### list_providers

```python
AiChannel.list_providers() -> List[ProviderInfo]
```

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 发现 `userspace/extensions/llm_providers/` 下已配置的本机供应商
- **参数：** 无
- **返回值：** `List[ProviderInfo]` — 只读快照（不含密钥明文）

### get_provider

```python
AiChannel.get_provider(provider_id: str) -> Optional[ProviderInfo]
```

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 按 ID 取单个本机供应商配置

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `provider_id` | `str` | ✓ | 供应商标识（目录名） |

- **返回值：** `Optional[ProviderInfo]` — 未找到或不安全 id 时 `None`

### set_api_key

```python
AiChannel.set_api_key(provider_id: str, api_key: str) -> ProviderInfo
```

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 写入本机供应商 API Key，返回更新后的快照

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `provider_id` | `str` | ✓ | 供应商标识 |
| `api_key` | `str` | ✓ | API Key 明文 |

- **返回值：** `ProviderInfo` — `has_api_key=True`
- **错误与异常：** 空密钥 / 未找到供应商 / 写入失败 → `AiError`

### load_api_key

```python
AiChannel.load_api_key(provider_id: str) -> Optional[str]
```

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 读取本机供应商 API Key；未配置或不存在则 `None`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `provider_id` | `str` | ✓ | 供应商标识 |

- **返回值：** `Optional[str]`

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

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 按本机供应商做一次裸补全。`provider_id=None` 时选第一个已启用且有 Key 的本机供应商。

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `messages` | `List[Dict[str, str]]` | ✓ | | OpenAI 兼容消息列表 |
| `provider_id` | `str?` | | `None` | 本机供应商标识 |
| `max_tokens` | `int` | | `2048` | 最大生成长度 |
| `temperature` | `float` | | `0.2` | 采样温度 |
| `timeout_seconds` | `float?` | | `None` | HTTP 超时 |
| `extra_body` | `Dict[str, Any]?` | | `None` | 透传到请求体的额外字段 |

- **返回值：** `CompleteResult`
- **错误与异常：** 消息非法 / 无可用供应商 / HTTP 失败 → `AiError`

### complete_http

```python
AiChannel.complete_http(
    messages: Sequence[Mapping[str, str]],
    *,
    base_url: str,
    api_key: str,
    model: str,
    provider_id: str,
    max_tokens: int = 2048,
    temperature: float = 0.2,
    timeout_seconds: Optional[float] = None,
    extra_body: Optional[Dict[str, Any]] = None,
) -> CompleteResult
```

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 对任意 OpenAI 兼容端点补全；由业务层注入已解析的地址与密钥（如会员通道）

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `messages` | 消息序列 | ✓ | | OpenAI 兼容消息 |
| `base_url` | `str` | ✓ | | 端点根（自动拼 `/chat/completions`） |
| `api_key` | `str` | ✓ | | Bearer 密钥 |
| `model` | `str` | ✓ | | 模型名 |
| `provider_id` | `str` | ✓ | | 写入 `CompleteResult.provider_id` 的标签 |
| `max_tokens` | `int` | | `2048` | 最大生成长度 |
| `temperature` | `float` | | `0.2` | 采样温度 |
| `timeout_seconds` | `float?` | | `None` | HTTP 超时 |
| `extra_body` | `Dict[str, Any]?` | | `None` | 透传字段 |

- **返回值：** `CompleteResult`

---

## contracts

从 `core.infra.ai.contracts` 导入：

| 符号 | 说明 |
|------|------|
| `ProviderInfo` | `provider_id` / `directory` / `base_url` / `model` / `enabled` / `has_api_key` |
| `CompleteResult` | `reply` / `provider_id` / `model` / 可选 `ntq` / `usage` |
| `AiError` | 配置或调用失败 |
