# 测试用例 — `infra.membership`（模块根）

**模块：** `infra.membership` · **版本：** `0.1.1`

**最低支持核心版本：** `>=0.5.3`

**本文件位置：** `__test__/`

---

## Scope

验证门面 `Membership`（`test_api.py`），对齐 `API.md`。

## 边界

**负责**

- 包根仅 `Membership`
- save / read / status / clear / token_file

**不负责**

- 官网验真、member_profile

**允许的测试类型（本目录）：** `api`

---

## Scenario：facade_api

| Case | 文件 | 说明 |
|------|------|------|
| `test_facade_exported_only` | `test_api.py` | `__all__` + 公开方法 |
| `test_save_read_clear` | `test_api.py` | 格式拒绝 / 写入 / 读回 / 清除 |
| `test_dropped_file_and_invalid_contents` | `test_api.py` | 注释行跳过；无效内容 → invalid |
