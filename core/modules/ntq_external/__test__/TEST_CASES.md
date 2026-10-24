# 测试用例 — `modules.ntq_external`

**模块：** `modules.ntq_external`  
**版本：** `0.1.0`  
**本文件位置：** `__test__/`

---

## Scope

验证模块根公开契约：包根导出 `register_trace_endpoint` 与 `site_urls`；地址集合键完整且为绝对地址；`Feedback` 门面方法齐全。

**不覆盖**：真实 HTTP 请求、会员凭证有效性、反馈落库。子包各有自己的 `__test__/`。

## 边界

**负责**

- Facade 导出面（对齐 `API.md`）
- `site_urls()` 的键与绝对地址
- trace 发送端登记可重复调用且不抛错

**不负责**

- 官网连通性与响应内容
- 会员登录态（测试环境按无凭证处理）
- UI 提示频率策略

**允许的测试类型（本目录）：** `api`

---

## Scenario：facade_contract

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_root_exports` | `test_api.py` | 包根 `__all__` 仅为两个函数且可调用 |
| `test_site_urls_shape` | `test_api.py` | 4 个页面地址 + 5 个文档地址齐全，均以 `http` 开头 |
| `test_register_trace_endpoint` | `test_api.py` | 返回 `None`，不抛异常 |
| `test_feedback_surface` | `test_api.py` | `Feedback` 的 7 个方法可调用 |

---

## Scenario：guest_profile

不联网验证访客态字段（需 monkeypatch `Membership.read` 返回空凭证）。

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_guest_profile_shape` | `test_member_profile.py`（待补） | `signed_in=False`、`reason="missing"`，不含凭证字段 |
