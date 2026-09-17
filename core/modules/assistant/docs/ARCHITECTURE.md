# Assistant — 架构

**版本：** `0.1.0`

`modules.assistant` 是 AI 助理的产品模块。本版本只负责从 userspace 发现 OpenAI 兼容供应商配置；HTTP 调用与 NTQ 提示词后续再加。

---

## 职责与边界（结论）

**负责**

- 经 `ProjectContext.path` 定位 `userspace/extensions/assistant/providers/`
- 扫描各供应商 `config.py`，组装 `ProviderInfo`
- 判断是否已配置 `api_key.txt`（不回传明文）

**不负责**

- 调用大模型 HTTP
- 组装 NTQ 百科 / 当前页上下文
- 浏览器 / Flask；由 BFF 日后调用本门面

---

## 模块结构图

```text
core/modules/assistant/
├── assistant.py              # Facade Assistant（唯一对外入口）
├── contracts.py              # ProviderInfo
├── core/
│   ├── assistant_manager.py  # 编排层（不导出）
│   └── provider_catalog.py   # 实施层：扫描/解析目录
├── API.md / QUICKSTART.md / glossary.yaml
├── __test__/
└── docs/
```

---

## 架构图

```text
Caller
  → Assistant.list_providers / get_provider
       → AssistantManager（编排，不导出）
            → ProviderCatalog（扫描 / 解析）
                 → ProjectContext.path.get_assistant_providers_directory
                 → Discovery.discover.files + Discovery.file.load_python_config
       → ProviderInfo（无 api_key 明文）
```

---

## 数据流（若有）

```text
userspace/extensions/assistant/providers/<id>/config.py
  + api_key.txt（可选）
  → Discovery 扫描
  → ProviderInfo
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
