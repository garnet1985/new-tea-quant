# Assistant — 架构

**版本：** `0.1.0`

`modules.assistant` 是 AI 助理的产品模块：发现 userspace 供应商配置，并发送一轮 OpenAI 兼容聊天。NTQ 百科与页面上下文后续再加。

---

## 职责与边界（结论）

**负责**

- 经 `ProjectContext.path` 定位 `userspace/extensions/assistant/providers/`
- 扫描各供应商 `config.py`，组装 `ProviderInfo`
- 在 Manager 内读取 `api_key.txt` 并发送非流式 chat/completions
- 判断是否已配置密钥（不回传明文）

**不负责**

- 流式输出、多轮会话持久化
- 组装 NTQ 百科 / 当前页上下文
- 浏览器 / Flask；由 BFF 日后调用本门面

---

## 模块结构图

```text
core/modules/assistant/
├── assistant.py                    # Facade Assistant（唯一对外入口）
├── contracts.py                    # ProviderInfo / AssistantError
├── core/
│   ├── assistant_manager.py        # 编排层（不导出）
│   ├── provider_catalog.py         # 实施层：扫描/解析目录
│   └── openai_compatible_client.py # 实施层：HTTP 协议
├── API.md / QUICKSTART.md / glossary.yaml
├── __test__/
└── docs/
```

---

## 架构图

```text
Caller
  → Assistant.list_providers / get_provider / chat
       → AssistantManager（编排，不导出）
            → ProviderCatalog（扫描 / 解析 / 读密钥）
            → OpenAICompatibleClient（chat/completions）
       → ProviderInfo 或 str（无 api_key 明文）
```

---

## 数据流（若有）

```text
userspace/extensions/assistant/providers/<id>/config.py
  + api_key.txt
  → Discovery 扫描
  → AssistantManager 选供应商、读 Key
  → POST {base_url}/chat/completions
  → 助手文本
```

---

## 依赖（结论）

- `infra.project_context`：助理目录路径
- `infra.discovery`：文件扫描与 Python 配置加载

---

## 相关文档

- [README](../README.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
- [设计](./DESIGN.md)
- [快速开始](../QUICKSTART.md)
