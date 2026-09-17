# Assistant — 快速开始

**模块：** `modules.assistant` · **版本：** `0.1.0`

发现 `userspace/extensions/assistant/providers/` 下已配置的供应商。

---

## 前置条件

- userspace 中存在至少一个供应商目录（安装后可先用预置的 `zhipu`）
- 公开契约见 [API.md](./API.md)

---

## 最小示例

```python
from core.modules.assistant import Assistant

providers = Assistant.list_providers()
zhipu = Assistant.get_provider("zhipu")
print([item.provider_id for item in providers])
print(None if zhipu is None else (zhipu.model, zhipu.has_api_key))
```

**预期结果：** 列表里出现 `zhipu`；`model` 为 `glm-4-flash`。

---

## 下一步

- [API.md](./API.md)
- [glossary.yaml](./glossary.yaml)
- [README.md](./README.md)

```bash
python3 -m pytest core/modules/assistant/__test__/ core/modules/assistant/core/__test__/ -q
```
