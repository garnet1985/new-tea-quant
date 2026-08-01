# 测试用例 — `<模块公开 API / 或包名>`

<!--
  本文件位于模块根 __test__/（API / integration / performance_smoke）。
  功能包另建 <package>/__test__/TEST_CASES.md。
  正式性能 → ../__performance__/CASES.md。
-->

**模块：** `<namespace.module_name>`  
**覆盖版本：** `<module.version>`  
**本文件位置：** `__test__/`

---

## Scope

`<本目录负责验证什么。例：模块公开 API 契约。>`

## 边界

**负责**

- `<测什么>`

**不负责**

- `<明确不测什么；不要测依赖模块的行为>`
- 可调用依赖的公开 API 作 fixture，但不把依赖正确性当本 suite 断言目标

**允许的测试类型（本目录）：** `api`（必须）· `integration`（可选）· `performance_smoke`（可选）  
正式 bench → [../__performance__/CASES.md](../__performance__/CASES.md)

---

## Scenario：`<scenario 短名>`

`<验哪一类行为 / 哪一块 API 节。>`

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_<name>` | `test_api.py` | `<一句话>` |

### Case 明细（可选）

#### `test_<name>`

- **文件：** `test_api.py`
- **对应 API：** `<Class.method>`
- **断言要点：** `<期望行为>`

---

## Scenario：`<另一 scenario>`

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_<name>` | `test_api.py` | `<…>` |
