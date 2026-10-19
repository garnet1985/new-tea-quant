# Agent 设计说明

**版本：** `0.1.0`

**相关文档：** [架构](./ARCHITECTURE.md) · [Provider 与 Navigator](./PROVIDER_AND_NAVIGATOR.md)（名词与本地/远端边界以此为准）

---

## 职责切分

| | 本地 App | 远端 Website（ntq） |
|--|----------|-------------------|
| 重心 | 组织 context、流程、本机工具 | 调度模型、计算与消耗 |
| Provider | 只选 `ntq` 或某一个用户供应商 | 接收 ntq 请求并选背后模型 |

`infra.ai.AiChannel.complete`：按 `provider_id` 出站（连接与密钥），**不**做业务分流、**不**为 ntq 挑本机 DS/GLM。

---

## 名词（摘要）

- **Provider**：一路出入口（`ntq` | 用户自备×1），一个 Provider 干到底  
- **Navigator**：意图 → 处理清单（原门禁/分流器）  
- **流向**：清单上的处理方式（guide / worker / advice…）

详见 [PROVIDER_AND_NAVIGATOR.md](./PROVIDER_AND_NAVIGATOR.md)。

---

## 内部结构

### 工具清单（`tool_catalog`）

新建、写文件、校验、后台启动、读进度和读报告等；说明可写入系统提示。

### 写入准则（`policy`）

相对路径须落在 `userspace/strategies/`、`userspace/extensions/tags/`、`userspace/extensions/adapters/` 之一。

### 运行循环（`run_loop` + Navigator + `roles`）

`Agent.run` → `resolve_provider` → Navigator → guide / worker → `complete(provider_id=同一 Provider)`。说明书在 `core/knowledge`。会话在 `userspace/.ntq/agent/`。

---

## 本版明确不做

- 不在 App 内为 ntq 配置多模型挑选表（那是 Website 的事）
- 不在 `infra.ai` 内写业务分流或百科挑选
- 不做全库 RAG；白名单 + 现有 picker
