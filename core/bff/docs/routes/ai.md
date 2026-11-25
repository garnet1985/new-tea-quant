# AI 通道 BFF：`platform/ai`

**版本：** 0.1.0

浏览器经本域访问 `infra.ai`：供应商发现与密钥写入。**无 chat**；产品对话见 [`agent.md`](./agent.md)。

## 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v1/ai/providers` | 本机大模型供应商列表（无密钥明文；目录为 `userspace/extensions/llm_providers/`） |
| PUT | `/v1/ai/providers/<provider_id>/api-key` | 写入密钥 |
