# 命令行布局 API 文档

**版本：** `0.2.0`  
**最低支持核心版本：** `>=0.5.0`

> 须与 `module_info.yaml` 的 `version` / `compatible_core_versions` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> 所列入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

---

## 包级短入口

### i

`from core.infra.cmd_layout import i`

- **类型：** `function`（`CmdLayout.icon.i` 的别名）
- **状态：** `beta`
- **引入版本：** `0.1.2`
- **描述：** 跨平台图标短入口；等价于 `CmdLayout.icon.get` / `CmdLayout.icon.i`
- **举例：**

```python
from core.infra.cmd_layout import i

print(f"{i('success')} 完成")  # ✅ 或 [OK]
```

---

## CmdLayout

**描述：** 命令行布局门面类（Facade）— 下挂 `bar_chart` / `title` / `separator` / `table` / `text` / `icon` 命名空间

### bar_chart

**描述：** 水平 ASCII 分布条形图 / 直方图（Windows / Linux / macOS 默认纯 ASCII 填充）

#### render

`CmdLayout.bar_chart.render(buckets, *, title="", width=20, show_count=True, show_pct=True, skip_empty=False, headers=None) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 将已分桶数据渲染为多行 ASCII 条形图字符串；负值按 0 处理
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `buckets` | `Sequence` | 每项为 `(label, value)`、含 `label`/`value`（或 `count`）的 mapping，或内部 `BarBucket` |
| `title` (可选) | `str` | 首行标题；默认空 |
| `width` (可选) | `int` | 条内格子数；最高柱铺满；默认 `20` |
| `show_count` (可选) | `bool` | 是否显示计数；默认 `True` |
| `show_pct` (可选) | `bool` | 是否显示占比；默认 `True` |
| `skip_empty` (可选) | `bool` | 是否跳过值为 0 的柱；默认 `False` |
| `headers` (可选) | `tuple[str, str, str, str] \| None` | 可选列标题 `(label, bar, count, pct)` |

- **返回值：** `str` — 多行图字符串
- **举例：**

```python
from core.infra.cmd_layout import CmdLayout

text = CmdLayout.bar_chart.render(
    [("win", 42), ("loss", 18)],
    title="胜负",
)
```

#### from_values

`CmdLayout.bar_chart.from_values(values, *, bins=10, title="", width=20, show_count=True, show_pct=True, label_format=".2f", skip_empty=False) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 对连续样本等宽分桶后渲染直方图；空列表仅返回 title（若有）；全相等样本输出单柱
- **返回值：** `str`

#### print / print_from_values

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 等同 `render` / `from_values`，并打印到 `stream`（默认 stdout）

---

### title

**描述：** ASCII 标题块。新报告优先 `h1` / `h2` / `h3` / `h4`；`banner` / `section` 保留兼容。

#### h1

`CmdLayout.title.h1(text, *, char="*", width=None, center=False, pad=None) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 报告总标题：前空行 + 星号框（同 `banner`）+ 打印后再空行
- **返回值：** `str`

#### h2

`CmdLayout.title.h2(text, *, char="=", min_width=24) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 大节：前空行 + 正文 + 等号下划线；线宽 `max(display_width(text), min_width)`
- **返回值：** `str`

#### h3

`CmdLayout.title.h3(text, *, char="-") -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 小节：前空行 + `--- 文本 ---`
- **返回值：** `str`

#### h4

`CmdLayout.title.h4(text, *, prefix="###") -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 细节标题：前空行 + `### 文本`
- **返回值：** `str`

#### print_h1 / print_h2 / print_h3 / print_h4

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 对应 `h1` / `h2` / `h3` / `h4` 并打印到 `stream`

#### banner

`CmdLayout.title.banner(text, *, char="*", width=None, center=False, pad=None) -> str`

- **类型：** `static`
- **状态：** `beta`
- **描述：** 星号框主体（无前后空行）；新代码请用 `h1`
- **返回值：** `str`

#### section

`CmdLayout.title.section(text, *, char="-") -> str`

- **类型：** `static`
- **状态：** `beta`
- **描述：** 形如 `-- 文本 --`；新代码请用 `h3`
- **返回值：** `str`

#### print_banner / print_section

- **类型：** `static`
- **状态：** `beta`
- **描述：** 等同 `banner` / `section` 并打印

---

### separator

**描述：** ASCII 分割线。新报告优先用标题层级，少叠 `separator` + `section`。

#### line / thick / star / blank

`CmdLayout.separator.line(*, char="-", width=60) -> str`  
`CmdLayout.separator.thick(*, width=60) -> str`  
`CmdLayout.separator.star(*, width=60) -> str`  
`CmdLayout.separator.blank() -> str`

- **类型：** `static`
- **状态：** `beta`
- **描述：** 单行 `-` / `=` / `*` / 空行内容

#### print_line / print_thick / print_star / print_blank

- **类型：** `static`
- **状态：** `beta`
- **描述：** 对应上述并打印到 `stream`

---

### table

**描述：** ASCII 对照表（首列左齐、其余右齐；列宽按终端显示宽度，CJK 计 2）

#### render

`CmdLayout.table.render(headers, rows, *, indent=3, gap=2) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 表头 + 分隔行 + 数据行；`headers` 为空时返回空串
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `headers` | `Sequence[str]` | 列名 |
| `rows` | `Sequence[Sequence[str]]` | 行；短行右侧补空 |
| `indent` (可选) | `int` | 左缩进空格；默认 `3` |
| `gap` (可选) | `int` | 列间距；默认 `2` |

- **返回值：** `str`

#### print

`CmdLayout.table.print(headers, rows, *, indent=3, gap=2, stream=None) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 等同 `render` 并打印（空表不打印）

---

### text

**描述：** 行内排版片段（不负责业务文案）

#### meta

`CmdLayout.text.meta(parts, *, sep=" · ") -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 过滤空段后用间隔符拼接（如 `组 3 · 对照上 4 套`）

#### kv

`CmdLayout.text.kv(label, value, *, sep=": ") -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** `label: value`

#### indent

`CmdLayout.text.indent(line, *, spaces=3) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 整段每行左缩进

#### numbered / bullets

`CmdLayout.text.numbered(items, *, indent=0, empty="") -> str`  
`CmdLayout.text.bullets(items, *, indent=0, marker="-", empty="") -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 编号 / 项目符号列表；空列表时返回缩进后的 `empty`（若有）

#### print_meta / print_kv / print_indent / print_numbered / print_bullets

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 对应上述并打印到 `stream`

---

### icon

**描述：** 跨平台图标（UTF-8 终端用 emoji；Windows 非 UTF-8 标准输出时用 ASCII 回退）

#### get / i

`CmdLayout.icon.get(icon_name: str) -> str`  
`CmdLayout.icon.i(icon_name: str) -> str`

- **类型：** `static`
- **状态：** `beta`
- **描述：** 按名称取图标；`i` 为简写；未知名返回空串

#### supports_emoji

`CmdLayout.icon.supports_emoji() -> bool`

- **类型：** `static`
- **状态：** `beta`
- **描述：** 当前标准输出是否适合输出 emoji
