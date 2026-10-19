# Agent 设计说明

**版本：** `0.1.0`

**相关文档：** [架构](./ARCHITECTURE.md)

模块切分：业务（门禁、角色、知识、工具）在本模块；模型出站在 `infra.ai`。

---

## 和 infra.ai 的分界

`AiChannel.complete` 只做连接、密钥路由与裸补全，**不**挑说明书。

`Agent` 做门禁与角色循环，并拥有 `context/` 知识语料与拼装。`Agent.run` 默认会员 `ntq`；也可传本机 `provider_id`（BYOK 轻问答，不跑 worker）。

---

## 三块内部结构

### 工具清单（`tool_catalog`）

已登记的工具里，新建、写文件、校验、后台启动、读进度和读报告都已实现。会员 `ntq` 路径下 `Agent.run` 会把这些说明写进系统提示。

### 写入准则（`policy`）

相对路径解析后，必须落在 `userspace/strategies/`、`userspace/extensions/tags/`、`userspace/extensions/adapters/` 之一。

### 运行循环（`run_loop` + `gate` + `roles`）

`Agent.run` → `RunLoop`：外层 `gate.router` 分流，再交给 `roles.guide` 或 `roles.worker`。共用模型 IO 在 `loop_runtime`（经 `AiChannel.complete`）。说明书拼装在 `core/knowledge`。

会话落在 `userspace/.ntq/agent/`。

---

## 本版明确不做

- 不在 `infra.ai` 内写业务门禁或百科挑选
- 不做全库 RAG；白名单 + 现有 picker
