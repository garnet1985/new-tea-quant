# 测试用例 — `infra.cli` 公开 API / CLI 行为

**模块：** `infra.cli`  
**覆盖版本：** `0.4.1`  
**本文件位置：** `__test__/`

---

## Scope

验证模块公开门面类（Facade / `Cli`）契约，以及 user / dev 短别名展开等与入口相关的轻量行为。

## 边界

**In scope**

- `Cli` 导出面与 `user` / `dev` / `shared` 公开方法
- user / dev 侧 abbrev 展开（含 dev `pack` 的 `-core_v`）

**Out of scope**

- 各业务 handler 的完整业务正确性（应在对应模块或集成测试中覆盖）
- 依赖模块（project_context / system_actions）自身行为

**允许的测试类型（本目录）：** `api` · 入口相关轻量用例（`test_user_cli.py` / `test_dev_cli.py`）

---

## Scenario：facade_export

导出面收紧为唯一 Facade。

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_cli_facade_exported` | `test_api.py` | `__all__` 仅为 `Cli`，且有 user/dev/shared |

---

## Scenario：user_api

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_user_main_callable` | `test_api.py` | `Cli.user.main` 可调用 |
| `test_user_bootstrap_callable` | `test_api.py` | `Cli.user.bootstrap` 可调用 |

---

## Scenario：dev_api

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_dev_main_callable` | `test_api.py` | `Cli.dev.main` 可调用 |

---

## Scenario：shared_api

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_shared_expand_argv` | `test_api.py` | 短别名展开 |
| `test_shared_is_help_argv` | `test_api.py` | help argv 判定 |
| `test_shared_aliases_for` | `test_api.py` | 长命令 → 短别名列表 |

---

## Scenario：user_abbrev

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_expand_argv` | `test_user_cli.py` | user 短命令展开 |

---

## Scenario：dev_abbrev

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_expand_argv` | `test_dev_cli.py` | dev 短命令展开（含 pack `-core_v`） |
