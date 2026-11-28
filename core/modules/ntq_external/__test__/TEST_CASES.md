# 测试用例 — `modules.ntq_external`

**模块：** `modules.ntq_external` · **版本：** `0.2.1`

**最低支持核心版本：** `>=0.6.0`

**本文件位置：** `__test__/`

---

## Scope

验证模块根公开契约：包根导出 `register_trace_endpoint` 与 `site_urls`；地址集合键完整且为绝对地址；`Feedback` 门面方法齐全；安装演示包 URL / 下载逻辑（不联网）。

**不覆盖**：真实 HTTP 请求、会员凭证有效性、反馈落库、官网 `/agent/policy` 联调。子包各有自己的 `__test__/`（含 `ai/__test__/test_agent_policy.py`）。

## 边界

**负责**

- Facade 导出面（对齐 `API.md`）
- `site_urls()` 的键与绝对地址
- trace 发送端登记可重复调用且不抛错
- `install_demo` URL 与本地跳过/校验写入

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
| `test_site_urls_shape` | `test_api.py` | 5 个页面地址 + 5 个文档地址齐全，均以 `http` 开头 |
| `test_register_trace_endpoint` | `test_api.py` | 返回 `None`，不抛异常 |
| `test_feedback_surface` | `test_api.py` | `Feedback` 的 7 个方法可调用 |

---

## Scenario：install_demo

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_install_demo_urls_default` | `test_install_demo.py` | 默认 URL 落在 `/api/v1/ntq-data/install/demo` |
| `test_install_demo_url_env_override` | `test_install_demo.py` | `NTQ_INSTALL_DEMO_URL` 可覆盖 |
| `test_download_install_demo_skips_when_present` | `test_install_demo.py` | 已有 zip 且非 force 不下载 |
| `test_download_install_demo_writes_and_checks_sha` | `test_install_demo.py` | 写入 zip + meta，校验 sha256 |

---

## Scenario：guest_profile

不联网验证访客态字段（需 monkeypatch `Membership.read` 返回空凭证）。

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_missing_token_offers_register` | `test_member_profile.py` | `signed_in=False`、`reason="missing"`，不含凭证字段 |
| `test_rejected_token_offers_register` | `test_member_profile.py` | `reason=rejected` |
| `test_profile_returns_name_avatar_points` | `test_member_profile.py` | 已登录字段归一化 |
