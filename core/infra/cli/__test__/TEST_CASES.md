# 测试用例 — `infra.cli` 公开 API

**模块：** `infra.cli`  
**覆盖版本：** `0.4.2`  
**本文件位置：** `__test__/`

---

## Scope

验证公开门面 `Cli` 的业务契约与入口约定。  
abbrev / parser / shared 脚手架等 helper 有 UT 即可，不在本文索引。

## 边界

**负责**

- `Cli` 导出面（仅 Facade）
- `Cli.user` / `Cli.dev` 入口的帮助、版本、默认 argv 行为
- `Cli.user.ensure_venv` / `bootstrap` 在 skip 环境下的无操作约定

**不负责**

- user / dev abbrev、parser 细节（有包内 UT，无本文索引）
- `Cli.shared.*` 脚手架 helper（有 API UT，无本文索引）
- 各业务 handler 完整正确性
- 依赖模块自身行为

**允许的测试类型（本目录）：** `api`

---

## Scenario：facade_export

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_cli_facade_exported` | `test_api.py` | `__all__` 仅为 `Cli`，且有 user/dev/shared |

---

## Scenario：user_entry

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_user_help_returns_zero` | `test_api.py` | `-h` 退出码 0 且打印帮助 |
| `test_user_bootstrap_noop_when_skipped` | `test_api.py` | skip env 下 `ensure_venv` / `bootstrap` 不抛错 |
| `test_user_default_argv_prints_help_then_version` | `test_api.py` | 空 argv：先帮助再版本 |
| `test_user_explicit_version_skips_help_preamble` | `test_api.py` | 显式 `version` 不打印帮助前缀 |

---

## Scenario：dev_entry

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_dev_help_returns_zero` | `test_api.py` | `-h` 退出码 0 且打印帮助 |
| `test_dev_version_returns_zero` | `test_api.py` | `version` 退出码 0 且打印版本 |
