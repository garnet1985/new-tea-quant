# Agent BFF：`platform/agent` 编排

**版本：** 0.1.0

浏览器经本域访问 `modules.agent`（Provider：`ntq` 或某一个自备）。补全经 `infra.ai.AiChannel.complete`。

## 与 infra.ai 的分界

| 入口 | 用途 |
|------|------|
| `POST /v1/agent/run` | Provider → Navigator → guide/worker；可传 `providerId`（默认 `ntq`） |
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

`providerId` 省略或 `ntq`：打 Website（猫粮与模型调度在远端）。其他 id：用户自备供应商，一个 Provider 干到底。
