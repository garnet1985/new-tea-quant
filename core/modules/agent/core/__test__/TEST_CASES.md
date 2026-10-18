# 测试用例 — `modules.agent.core`

**模块：** `modules.agent`  
**版本：** `0.1.0`  
**本文件位置：** `core/__test__/`

---

## Scope

写入准则与未接通的运行循环。

## 边界

**负责**

- 相对路径只落到策略、标签、适配器目录
- 空白消息与未接通模型时 `RunLoop` 的错误

**不负责**

- 门面导出（见模块根 `__test__/test_api.py`）

**允许的测试类型（本目录）：** `unit`

---

## Scenario：policy

| Case | 文件 | 说明 |
|------|------|------|
| `test_allows_strategy_tag_and_adapter_files` | `test_policy.py` | 三个允许根下的相对路径 |
| `test_rejects_paths_outside_write_roots` | `test_policy.py` | core、密钥、绝对路径、`..`、空路径 |

## Scenario：loop

| Case | 文件 | 说明 |
|------|------|------|
| `test_run_loop_is_not_connected` | `test_run_loop.py` | 空白消息与未接通模型 |
