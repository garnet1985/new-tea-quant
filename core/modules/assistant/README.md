# Assistant（`modules.assistant`）

发现 userspace 中的 AI 供应商配置，并发送一轮 OpenAI 兼容聊天。对外入口为 `Assistant`（内部由 `AssistantManager` 编排，不导出）；快照与异常见 `contracts`。

## 适用场景

- 列出本机已配置的供应商（是否启用、是否已填 Key）
- 把 API Key 写入已发现供应商的 `api_key.txt`（不回传明文）
- 发送一句用户消息并拿到助手回复
- 在 `userspace/extensions/assistant/providers/<id>/` 增加新的 OpenAI 兼容供应商

## 模块依赖

- `infra.project_context`：助理与供应商目录路径
- `infra.discovery`：扫描 `config.py` 并加载 `PROVIDER`

## 设计初衷

- **要解决的问题：** 聊天需要先发现本机供应商，再用其配置发请求，且路径与密钥不能散落在调用方。
- **明确不做：** 本版本不做流式输出、不做 NTQ 百科注入、不把 api_key 明文返回给调用方。

## 常见问题

**Q：该 import 什么？**  
A：`from core.modules.assistant import Assistant`；类型 `from core.modules.assistant.contracts import ProviderInfo, AssistantError`。

**Q：供应商目录在哪？**  
A：`ProjectContext.path.get_assistant_providers_directory()`，即 `userspace/extensions/assistant/providers/`。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
