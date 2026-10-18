# 测试用例 — `modules.agent`

**模块：** `modules.agent`  
**版本：** `0.1.0`  
**本文件位置：** `__test__/`

---

## Scope

验证门面 `Agent` 与 `ToolSpec` 公开契约（对齐 `API.md`）。

## 边界

**负责**

- 包导出、`list_tools` 的名字与未实现标记
- `ToolSpec` 字段不含可执行体

**不负责**

- 写入准则与运行循环（见 `core/__test__`）

**允许的测试类型（本目录）：** `api`

---

## Scenario：facade

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_facade_export` | `test_api.py` | 包根只导出 `Agent` |
| `test_list_tools_are_registered_but_not_implemented` | `test_api.py` | 六个工具名，`implemented` 为假 |
| `test_tool_spec_fields` | `test_api.py` | 字段不含 handler / api_key |
