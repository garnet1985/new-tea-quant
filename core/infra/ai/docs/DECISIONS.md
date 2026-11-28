# AI 通道 — 设计与决策

**模块：** `infra.ai` · **版本：** `0.2.0`

**最低支持核心版本：** `>=0.6.0`

记录本模块非平凡选型。现状结构见 [ARCHITECTURE.md](./ARCHITECTURE.md)。

---

## 设计目标

- 本机供应商发现与 HTTP 补全可独立使用，不绑定官网
- 删除 `modules.ntq_external` 后，本机 AI 仍可用；仅失去官网 service
- 业务层可注入任意 OpenAI 兼容端点，而不把官网知识渗进 infra

---

## 方案与思路

早期 `AiChannelManager` 懒加载 `ntq_external.member_channel`，在 `provider_id` 缺省或为 `ntq` 时走会员。这违反「infra 不引用 modules」与「官网业务只在 ntq_external」两条边界。

候选：

1. **路由上移 + `complete_http`**：infra 只做本机目录与通用 HTTP；会员补全在 `ntq_external`，经 `complete_http` 注入凭证
2. 会员能力下沉到 infra：违背「删 ntq_external 即去官网化」
3. 仅文档约束、代码保留 try/import：分层仍脏

选定 1。Agent 经 `complete_result` 按 Provider 分流。

---

## DEC-01: infra.ai 不依赖 ntq_external

**是什么**  
本模块禁止 import `modules.ntq_external`；`complete` 只解析本机 `llm_providers`。

**为什么选它**  
官网业务集中在 ntq_external；去掉该模块后核心本机能力应仍可用。

**放弃了什么**  
在 Facade 内「默认走会员」的便利；缺省 `provider_id` 改为选第一个本机已配置供应商。

---

## DEC-02: 用 complete_http 承接业务端点

**是什么**  
公开 `AiChannel.complete_http(base_url, api_key, model, …)`，供会员等业务层注入已解析凭证。

**为什么选它**  
复用消息校验与 OpenAI 客户端，避免 ntq_external 再写一份 HTTP；infra 仍不知道「会员」语义。

**放弃了什么**  
让 `complete(provider_id="ntq")` 继续作为会员入口。

---

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [API.md](../API.md)
