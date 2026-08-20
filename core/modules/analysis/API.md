# Analysis API 文档

**版本：** `0.1.0`  
**最低支持核心版本：** `>=0.4.4`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。

术语见 [glossary.yaml](./glossary.yaml)。概念见 [CONCEPTS.md](./docs/CONCEPTS.md)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。未决选型见 [DESIGN.md](./docs/DESIGN.md)。

**公开约定：** 包根仅导出 `Analysis`。跨模块类型从 [`contracts.py`](./contracts.py) 导入。实现位于 `core/`，禁止 deep-import。

本版本 **无行为 API**（无方法、无 namespace）。`contracts` 亦无公开符号。

---

## Analysis

**描述：** 回测后 inputs→outputs 归因门面（骨架占位）

- **状态：** `experimental`
- **引入版本：** `0.1.0`
- **描述：** 仅可 import，以确认模块存在。归因入口形状待设计点拍板后写入本节，并同步 `__test__/test_api.py`。

**举例：**

```python
from core.modules.analysis import Analysis

assert Analysis is not None
```

---

## contracts

本版本无公开符号。
