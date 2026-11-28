# 测试用例 — `infra.cmd_layout` 公开 API

**模块：** `infra.cmd_layout` · **版本：** `0.3.0`

**最低支持核心版本：** `>=0.5.0`

**本文件位置：** `__test__/`

---

## Scope

验证门面类 `CmdLayout` 的公开业务契约（导出面与各 namespace 主路径行为）。

## 边界

**负责**

- 包根导出 `CmdLayout` / `i`
- title / bar_chart / table / text / icon 的主路径产品行为

**不负责**

- 包内 helper 边界细节（→ 各包 `__test__/`）
- 策略报告业务指标正确性
- 真实 Windows 控制台人工验收（用 mock 覆盖 emoji 回退）

**允许的测试类型（本目录）：** `api`

---

## Scenario：facade_export

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_cmd_layout_facade_exported` | `test_api.py` | `__all__`；五命名空间；无 separator / banner / section |

---

## Scenario：layout_output

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_title_h1_h2_h3_h4` | `test_api.py` | h1–h4 形态 |
| `test_bar_chart_render_max_bar_and_pct` | `test_api.py` | 最高柱铺满与占比 |
| `test_bar_chart_from_values` | `test_api.py` | 直方图预留入口可调用 |
| `test_table_render` | `test_api.py` | 表头/分隔/数据行 |
| `test_text_meta_and_numbered` | `test_api.py` | meta 拼接与编号列表 |
| `test_icon_emoji_and_ascii_fallback` | `test_api.py` | emoji 与 ASCII 回退 |
| `test_print_h1_to_stream` | `test_api.py` | print_h1 写入指定 stream |
