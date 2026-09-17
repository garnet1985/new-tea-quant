# Assistant API 文档

**版本：** `0.1.0`  
**最低支持核心版本：** `>=0.5.0`

> 须与 `module_info.yaml` 一致。公开入口状态最高 **`beta`**。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Assistant`；快照与异常从 [`contracts.py`](./contracts.py) 导入。`AssistantManager` / `ProviderCatalog` / `OpenAICompatibleClient` 位于 `core/`，禁止 deep-import。

---

## Assistant

**描述：** AI 助理门面（静态 API）。发现 userspace 供应商并发送一轮非流式聊天。

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

### chat

`Assistant.chat(content: str, *, provider_id: Optional[str] = None, history: Optional[list[dict]] = None) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 发送一句用户消息；未指定 `provider_id` 时使用第一个 `enabled` 且已配置密钥的供应商。请求会附带一段 NTQ 系统提示；`history` 只传此前的 user/assistant 轮次（最多 16 条），不落盘
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `content` | `str` | 用户消息；空白则失败 |
| `provider_id` (可选) | `str \| None` | 指定供应商目录名；默认自动挑选 |
| `history` (可选) | `list[dict] \| None` | 此前 `{role, content}` 列表；只接受 `user` / `assistant` |

- **返回值：** `str` — 助手文本
- **错误与异常：** `AssistantError` — 未配置供应商 / 密钥、请求失败、返回无法解析
- **举例：**

```python
from core.modules.assistant import Assistant

print(Assistant.chat("只回复 pong"))
print(Assistant.chat("你好", provider_id="zhipu"))
print(Assistant.chat("那策略呢", history=[{"role": "user", "content": "NTQ 是什么"}, {"role": "assistant", "content": "..."}]))
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

---

## AssistantError

**描述：** 配置缺失或供应商调用失败（`contracts.AssistantError`）。异常消息不含 api_key。
