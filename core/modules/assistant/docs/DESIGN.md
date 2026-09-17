# Assistant 设计说明

**版本：** `0.1.0`

**相关文档：** [架构总览](./ARCHITECTURE.md)

---

## userspace 目录约定

```text
userspace/extensions/assistant/providers/
└── <provider_id>/
    ├── config.py              # 必须：顶层 PROVIDER = {...}
    ├── api_key.txt            # 可选：密钥，打包时剥离
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
- **enabled：** 缺省 `True`；`False` 仍会出现在列表中，由调用方决定是否使用

路径一律经 `ProjectContext.path.get_assistant_root` / `get_assistant_providers_directory` / `get_assistant_provider_directory`，禁止硬编码 `userspace/...`。

---

## 设计决策

### 1. 发现先于调用

先跑通「本机有哪些供应商」，再接 HTTP。门面本版本只有 `list_providers` / `get_provider`。

### 2. userspace 只放配置，不放协议代码

智谱 / 硅基流动等均为 OpenAI 兼容接口。适配器留在 core；userspace 只提供 `base_url`、`model`、密钥文件。

### 3. 路径走 ProjectContext

与 data_source / tags / adapters 相同，避免安装后 userspace 根目录变化时写死相对路径。

### 4. 快照不含密钥

公开 `ProviderInfo.has_api_key`。真正读 Key 留给后续调用层，且不得进入 BFF 响应。

### 5. Facade / Manager / Catalog 三层

对齐根目录代码风格：包根只导出 `Assistant`。`AssistantManager` 是内部编排（发现、日后的调用与默认供应商），`ProviderCatalog` 是实施层（扫目录、解析 `PROVIDER`）。禁止把 Manager 导出成第二个入口。
