# Assistant API 文档

**版本：** `0.1.0`  
**最低支持核心版本：** `>=0.4.5`

> 须与 `module_info.yaml` 一致。公开入口状态最高 **`beta`**。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Assistant`；快照类型从 [`contracts.py`](./contracts.py) 导入。`AssistantManager` / `ProviderCatalog` 位于 `core/`，禁止 deep-import。

---

## Assistant

**描述：** AI 助理门面（静态 API）。本版本只做供应商发现。

### list_providers

`Assistant.list_providers() -> list[ProviderInfo]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 扫描 `userspace/extensions/assistant/providers/*/config.py`，返回合法供应商快照（按 `provider_id` 排序）
- **参数：** 无
- **返回值：** `list[ProviderInfo]` — 不含 api_key 明文；目录不存在时为空列表
- **举例：**

```python
from core.modules.assistant import Assistant

for item in Assistant.list_providers():
    print(item.provider_id, item.model, item.has_api_key)
```

### get_provider

`Assistant.get_provider(provider_id: str) -> ProviderInfo | None`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 按供应商目录名取一条快照；空名、路径穿越、不存在或配置不合法时返回 ``None``
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `provider_id` | `str` | 与 `providers/` 下文件夹名一致 |

- **返回值：** `ProviderInfo | None`
- **举例：**

```python
from core.modules.assistant import Assistant

zhipu = Assistant.get_provider("zhipu")
```

---

## ProviderInfo

**描述：** 供应商发现结果的只读数据类（`contracts.ProviderInfo`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `provider_id` | `str` | 文件夹名（不以 config 内 `id` 为准） |
| `directory` | `Path` | 供应商目录绝对路径 |
| `base_url` | `str` | OpenAI 兼容根地址（无末尾 `/`） |
| `model` | `str` | 模型名 |
| `enabled` | `bool` | `config.py` 的 `enabled`，缺省 `True` |
| `has_api_key` | `bool` | `api_key.txt` 存在且非空 |
