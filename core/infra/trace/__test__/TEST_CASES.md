# 测试用例 — `infra.trace`（模块根）

**模块：** `infra.trace`  
**覆盖版本：** `0.2.0`  
**本文件位置：** `__test__/`

---

## Scope

验证门面 `Trace` 与 `contracts` / `types`（`test_api.py`）。  
队列 / 同意 / ask 行为在 `core/__test__/`。

## 边界

**负责：** 公开 Facade API；配置解析抽检（含 target_url）  
**不负责：** 接收端服务实现

**允许的测试类型（本目录）：** `api`

---

## Scenario：facade_api

| Case | 文件 | 说明 |
|------|------|------|
| `test_trace_facade_exported` | `test_api.py` | `__all__` + 方法 |
| `test_config_namespace` | `test_api.py` | load 含 target_url |
| `test_consent_namespace` | `test_api.py` | consent API |
| `test_types_and_defaults` | `test_api.py` | types ≡ contracts；Defaults 单源 |
| `test_endpoint_env_override` | `test_api.py` | NTQ_TRACE_ENDPOINT |
