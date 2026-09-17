# Assistant — 快速开始

**模块：** `modules.assistant` · **版本：** `0.1.0`

发现已配置的供应商并发送一轮对话。

---

## 前置条件

- `userspace/extensions/assistant/providers/<id>/` 中有 `config.py` 与非空 `api_key.txt`
- 公开契约见 [API.md](./API.md)

---

## 最小示例

```python
from core.modules.assistant import Assistant

print(Assistant.list_providers())
print(Assistant.chat("只回复 pong", provider_id="zhipu"))
```

**预期结果：** 助手文本为 `pong`（或等价短回复）。

---

## 下一步

- [API.md](./API.md)
- [glossary.yaml](./glossary.yaml)
- [README.md](./README.md)

```bash
python3 -m pytest core/modules/assistant/__test__/ core/modules/assistant/core/__test__/ -q
```
