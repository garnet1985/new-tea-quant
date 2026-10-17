# 测试用例 — `infra.progress`

**模块：** `infra.progress`  
**版本：** `0.1.0`  
**本文件位置：** `__test__/`

---

## Scope

公开门面：开始、步骤、子步骤、结束、读取，以及比例。

## 边界

**负责**

- `Progress.open`、`step`、`sub`、`close`、`read`、`fraction`
- 步骤变化时子步骤被清零
- 包根只导出 `Progress`

**不负责**

- 业务模块何时调用
- 界面怎么画百分比

**允许的测试类型（本目录）：** `api`

## 用例

| 用例 | 类型 | 入口 |
|------|------|------|
| 门面导出与方法存在 | api | `test_api.py` |
| 步骤清掉子步骤，结束后步骤收到总数 | api | `test_api.py` |
| 比例把当前子步骤算进去 | api | `test_api.py` |
