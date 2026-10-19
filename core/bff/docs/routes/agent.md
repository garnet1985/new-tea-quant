# Agent BFF：`platform/agent` 编排

**版本：** 0.1.0

浏览器经本域访问 `modules.agent`（产品 NTQ AI 与 BYOK 轻问答）。补全经 `infra.ai.AiChannel.complete`。

## 与 infra.ai 的分界

| 入口 | 用途 |
|------|------|
| `POST /v1/agent/run` | 门禁 + guide/worker；可传 `providerId`（默认 `ntq`） |
| `GET /v1/agent/quota` | 会员猫粮余额 |
| `GET /v1/ai/providers` | 仅供应商/密钥（见 [`ai.md`](./ai.md)） |

## 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v1/agent/quota` | 会员猫粮快照 |
| POST | `/v1/agent/run` | 一句用户消息 → Agent |
| POST | `/v1/agent/session/clear` | 清空本机会话 |
| GET\|POST | `/v1/agent/session/history` | 最近对话 |

### POST `/v1/agent/run`

```json
{
  "content": "帮我看看资金报告",
  "sessionId": "default",
  "providerId": "ntq"
}
```

`providerId` 省略或 `ntq`：会员产品循环（可工具）。其他本机供应商：门禁后百科轻问答，不写策略/回测。
