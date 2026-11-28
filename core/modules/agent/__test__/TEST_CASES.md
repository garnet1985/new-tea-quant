# 测试用例 — `modules.agent`

**模块：** `modules.agent` · **版本：** `0.1.2`

**最低支持核心版本：** `>=0.6.0`

**本文件位置：** `__test__/`

---

## Scope

只验证模块根公开契约：包根仅导出 `Agent`，`contracts` 导出 `AgentError` / `ToolSpec`，工具清单形状正确，未知工具抛错。

**不覆盖**：写策略、跑回测、报告写作、navigator 分流、provider 适配。这些在 `core/code/` 各包的 `__test__/` 里。

## 边界

**负责**

- Facade 导出面（对齐 `API.md`）
- `ToolSpec` 类型与工具名唯一性
- 未知工具的异常约定

**不负责**

- LLM 调用与提示词内容
- 会话存储、偏好、计费
- 任何需要 API Key 的路径

**允许的测试类型（本目录）：** `api`

---

## Scenario：facade_contract

模块可 import，门面方法齐全。

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_facade_exports` | `test_api.py` | 包根 `__all__` 仅为 `Agent`，10 个门面方法可调用 |
| `test_tool_specs_are_unique_and_typed` | `test_api.py` | 工具清单非空、均为 `ToolSpec`、名字不重复、`implemented` 为布尔 |
| `test_unknown_tool_raises` | `test_api.py` | 未知工具名抛 `AgentError` |
