# 测试用例 — `infra.system_actions`（模块根）

**模块：** `infra.system_actions`  
**覆盖版本：** `0.2.0`  
**本文件位置：** `__test__/`

---

## Scope

验证门面 `SystemActions` 与 `contracts` / `types`（`test_api.py`）。  
租约行为单测在 `core/pipeline_lease/__test__/`。

## 边界

**负责：** 公开 namespace API；contracts 异常与常量  
**不负责：** 策略/Tag 业务执行

**允许的测试类型（本目录）：** `api`

---

## Scenario：facade_api

| Case | 文件 | 说明 |
|------|------|------|
| `test_facade_export` | `test_api.py` | `__all__` + pipeline / scaffold / types |
| `test_pipeline_*` / `scaffold_*` | `test_api.py` | 方法存在与抽检 |
| `test_contracts_and_types` | `test_api.py` | contracts ≡ types |
| `test_pipeline_lease_construct` | `test_api.py` | lease 返回上下文管理器 |
