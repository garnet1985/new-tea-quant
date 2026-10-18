# Agent — 快速开始

**模块：** `modules.agent` · **版本：** `0.1.0`

查看已登记、尚未实现的工具。

---

## 前置条件

无。本版不读取 API Key，也不发网络请求。

---

## 最小示例

```python
from core.modules.agent import Agent

for tool in Agent.list_tools():
    print(tool.name, tool.implemented)
```

**预期结果：** 打印 6 个工具名，`implemented` 均为 `False`。

---

## 下一步

- [API.md](./API.md)
- [设计](./docs/DESIGN.md)

```bash
python3 -m pytest core/modules/agent/__test__/ core/modules/agent/core/__test__/ -q
```
