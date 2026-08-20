# 测试用例 — `modules.analysis`

**模块：** `modules.analysis`  
**覆盖版本：** `0.1.0`  
**本文件位置：** `__test__/`

---

## Scope

验证骨架公开契约：包根只导出 `Analysis`；无行为 API；`contracts` 无公开符号。

## 边界

**负责**

- Facade 导出面与空 API 形状（对齐 `API.md`）

**不负责**

- 归因正确性（尚无实现）
- strategy 产物格式、BE 调度

**允许的测试类型（本目录）：** `api`

---

## Scenario：facade_scaffold

空模块可 import，且不提前锁行为方法。

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_facade_export` | `test_api.py` | 包根 `__all__` 仅为 `Analysis` |
| `test_no_behavior_api` | `test_api.py` | Facade 无公开行为方法 |
| `test_contracts_empty` | `test_api.py` | `contracts.__all__` 为空 |
