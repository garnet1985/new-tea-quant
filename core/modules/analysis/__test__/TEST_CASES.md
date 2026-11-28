# 测试用例 — `modules.analysis`

**模块：** `modules.analysis` · **版本：** `0.1.1`

**最低支持核心版本：** `>=0.5.0`

**本文件位置：** `__test__/`

---

## Scope

验证公开契约：包根仅导出 `Analysis`；`Analysis.Classical` / `Analysis.ML` 可调用；`contracts` 无公开符号。数学细节见各 `test_*.py`。

## 边界

**负责**

- Facade 导出面与 namespace 可达性（对齐 `API.md`）
- 轻量 smoke（如 `quantile_buckets` 返回 `ok`）

**不负责**

- 全量数值金标准（见包内单测）
- strategy 产物格式

**允许的测试类型（本目录）：** `api` 及领域单测（`test_univariate` 等）

---

## Scenario：facade_and_classical

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_facade_exports` | `test_api.py` | 包根 `__all__` 仅为 `Analysis` |
| `test_classical_namespace` | `test_api.py` | Classical/ML 挂在 Facade 上且可调用 |
| `test_quantile_buckets_ok` | `test_api.py` | 分桶 smoke |
| `test_contracts_empty` | `test_api.py` | `contracts.__all__` 为空 |