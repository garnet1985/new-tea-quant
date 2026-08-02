# 测试用例 — `infra.cmd_layout`

**模块：** `infra.cmd_layout`  
**覆盖版本：** `0.4.1`  
**本文件位置：** `__test__/`

---

## Scope

验证门面类 `CmdLayout` 公开契约，以及 title / separator / bar_chart / icon 的核心渲染行为。

## 边界

**负责**

- 包根仅导出 `CmdLayout`
- 各 namespace 公开方法可调用且行为符合 API

**不负责**

- 策略报告业务指标正确性
- 真实 Windows 控制台人工验收（用 mock 覆盖 emoji 回退）

**允许的测试类型（本目录）：** `api` · 各组件轻量单测

---

## Scenario：facade_export

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_cmd_layout_facade_exported` | `test_api.py` | `__all__` 仅为 `CmdLayout`，四 namespace齐全 |

---

## Scenario：bar_chart_api

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_bar_chart_namespace_callable` | `test_api.py` | render / from_values / print* 可调用 |
| `test_render_max_bar_full_width_and_pct` | `test_bar_chart.py` | 最高柱铺满与占比 |
| `test_from_values_histogram` 等 | `test_bar_chart.py` | 分桶与边界行为 |

---

## Scenario：title_separator_api

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_title_namespace_callable` | `test_api.py` | banner / section / print* |
| `test_separator_namespace_callable` | `test_api.py` | line / thick / star / blank / print* |
| `test_banner_wraps_with_stars` 等 | `test_title_separator.py` | 标题与分割线行为 |

---

## Scenario：icon_api

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_icon_namespace_callable` | `test_api.py` | get / i / supports_emoji |
| `test_get_aliases` 等 | `test_icon.py` | 别名、ASCII 回退、未知名 |
