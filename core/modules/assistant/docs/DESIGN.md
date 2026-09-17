# Assistant 设计说明

**版本：** `0.1.0`

**相关文档：** [架构总览](./ARCHITECTURE.md)

---

## userspace 目录约定

```text
userspace/extensions/assistant/providers/
└── <provider_id>/
    ├── config.py              # 必须：顶层 PROVIDER = {...}
    ├── api_key.txt            # 调用前必须：密钥，打包时剥离
    └── api_key.txt.example
```

`config.py` 示例：

```python
PROVIDER = {
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "model": "glm-4-flash",
    "enabled": True,
}
```

- **身份：** 文件夹名即 `provider_id`；忽略 config 里的 `id` 字段
- **合法条目：** 必须有非空 `base_url` 与 `model`
- **enabled：** 缺省 `True`；`False` 仍会出现在列表中，调用时会失败
- **chat 默认挑选：** 第一个 `enabled` 且 `has_api_key` 的供应商

路径一律经 `ProjectContext.path.get_assistant_root` / `get_assistant_providers_directory` / `get_assistant_provider_directory`，禁止硬编码 `userspace/...`。

---

## 设计决策

### 1. 发现先于调用

先能列出供应商，再发 HTTP。`chat` 复用同一套发现结果。

### 2. userspace 只放配置，不放协议代码

智谱 / 硅基流动等均为 OpenAI 兼容接口。HTTP 适配器留在 core；userspace 只提供 `base_url`、`model`、密钥文件。

### 3. 路径走 ProjectContext

与 data_source / tags / adapters 相同，避免安装后 userspace 根目录变化时写死相对路径。

### 4. 快照不含密钥

公开 `ProviderInfo.has_api_key`。真正读 Key 只发生在 `AssistantManager.chat` 内部，且不得进入 BFF 响应或异常字符串。

### 5. Facade / Manager / Catalog 三层

对齐根目录代码风格：包根只导出 `Assistant`。`AssistantManager` 是内部编排（发现、选供应商、调用），`ProviderCatalog` 与 `OpenAICompatibleClient` 是实施层。禁止把 Manager 导出成第二个入口。

### 6. HTTP 用标准库 urllib

与 `infra.trace` / `infra.feedback` 一致，不新增运行时 HTTP 依赖。本版本只做非流式补全。
