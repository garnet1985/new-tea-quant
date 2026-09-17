# 测试用例 — `modules.assistant`

**模块：** `modules.assistant`  
**版本：** `0.1.0`  
**本文件位置：** `__test__/`

---

## Scope

验证门面 `Assistant` 与 `ProviderInfo` 公开契约（对齐 `API.md`）。

## 边界

**负责**

- 包导出、方法可调用、返回类型
- 对当前 userspace 的发现冒烟（目录缺失则跳过）

**不负责**

- 扫描算法细节（见 `core/__test__`）
- 大模型 HTTP

**允许的测试类型（本目录）：** `api` · `integration`

---

## Scenario：facade

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_facade_export` | `test_api.py` | 包根只导出 `Assistant` |
| `test_list_and_get_callable` | `test_api.py` | 公开方法可调用；空名返回 `None` |
| `test_provider_info_fields` | `test_api.py` | `ProviderInfo` 字段齐全且不含 `api_key` |
| `test_live_userspace_discovers_zhipu` | `test_api.py` | 本机 userspace 能扫到预置 `zhipu` |
