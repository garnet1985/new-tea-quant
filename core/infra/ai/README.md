# AI 通道（`infra.ai`）

发现 userspace 供应商、写入 API Key，并发送 OpenAI 兼容的裸补全。对外入口为 `AiChannel`。

**不做：** 百科挑文档、业务门禁、工具循环（均在 `modules.agent`）。

## 公开用法

```python
from core.infra.ai import AiChannel

AiChannel.list_providers()
AiChannel.set_api_key("zhipu", "…")
AiChannel.complete(
    [{"role": "user", "content": "ping"}],
    provider_id="zhipu",
)
```

供应商目录：`userspace/extensions/llm_providers/<id>/`。
