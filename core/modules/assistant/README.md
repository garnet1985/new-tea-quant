# Assistant（`modules.assistant`）

发现并读取 userspace 中的 AI 供应商配置，作为后续聊天调用的门面。对外入口为 `Assistant`（内部由 `AssistantManager` 编排，不导出）；快照类型见 `contracts.ProviderInfo`。

## 适用场景

- 设置页列出本机已配置的供应商（是否启用、是否已填 Key）
- 按目录名取出某一个供应商的 `base_url` / `model`，供后续调用使用
- 在 `userspace/extensions/assistant/providers/<id>/` 增加新的 OpenAI 兼容供应商

## 模块依赖

- `infra.project_context`：助理与供应商目录路径
- `infra.discovery`：扫描 `config.py` 并加载 `PROVIDER`

## 设计初衷

- **要解决的问题：** 聊天调用需要先知道本机有哪些供应商、配置是否完整，且路径不能写死。
- **明确不做：** 本版本不发 HTTP、不组 NTQ 提示词、不把 api_key 明文返回给调用方。

## 常见问题

**Q：该 import 什么？**  
A：`from core.modules.assistant import Assistant`；快照 `from core.modules.assistant.contracts import ProviderInfo`。

**Q：供应商目录在哪？**  
A：`ProjectContext.path.get_assistant_providers_directory()`，即 `userspace/extensions/assistant/providers/`。

## 相关文档

- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [设计](./docs/DESIGN.md)
- [测试用例](./__test__/TEST_CASES.md)
