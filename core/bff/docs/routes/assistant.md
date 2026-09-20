# Assistant BFF：`platform/assistant` 编排

**版本：** 0.2.1

浏览器经本域访问 `modules.assistant`。领域执行在 Facade；本层只做 HTTP 信封与 camelCase DTO。

## HTTP 前缀

- 蓝图注册：`url_prefix='/api'`（`core/bff/app.py`）
- 完整 URL = **`/api`** + 下表路径

## 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v1/assistant/providers` | 列出本机供应商；`hasApiKey` 仅为布尔，不含密钥 |
| POST | `/v1/assistant/chat` | 一轮非流式对话 |
| PUT | `/v1/assistant/providers/<provider_id>/api-key` | 写入密钥；响应仍不含明文 |

### GET `/v1/assistant/providers`

成功 `message`：

```json
{
  "items": [
    {
      "providerId": "zhipu",
      "baseUrl": "https://open.bigmodel.cn/api/paas/v4",
      "model": "glm-4-flash",
      "enabled": true,
      "hasApiKey": true
    }
  ]
}
```

### POST `/v1/assistant/chat`

请求：

```json
{
  "content": "只回复 pong",
  "providerId": "zhipu",
  "history": [
    { "role": "user", "content": "NTQ 是什么" },
    { "role": "assistant", "content": "New Tea Quant。" }
  ]
}
```

`providerId` 可省略，则使用第一个已启用且已配置密钥的供应商。`history` 可省略；只接受此前 `user` / `assistant` 轮次。

成功 `message`：

```json
{ "reply": "pong", "providerId": "zhipu", "model": "glm-4-flash" }
```

失败：`400` 配置/入参问题（`ASSISTANT_BAD_REQUEST`）；`502` 供应商调用失败（`ASSISTANT_UNAVAILABLE`）。异常文本不含 api_key。

### PUT `/v1/assistant/providers/<provider_id>/api-key`

请求：

```json
{ "apiKey": "your-key" }
```

成功 `message` 与列表条目相同（`hasApiKey: true`），不含密钥字段。空白密钥或未知供应商返回 `400`。

## 待补测试

| Case | 说明 |
|------|------|
| `test_providers_omits_api_key` | 列表无密钥字段 |
| `test_chat_empty_content_400` | 空白 content 返回 400 |
| `test_chat_unknown_provider_400` | 未知 providerId 返回 400 |
| `test_chat_pong_200` | 有密钥时返回 reply（可 mock Facade） |
| `test_chat_history_passed` | history 传入 Facade（可 mock） |
| `test_put_api_key_omits_secret` | 写入后返回 hasApiKey，无密钥字段 |
| `test_put_api_key_empty_400` | 空白 apiKey 返回 400 |
