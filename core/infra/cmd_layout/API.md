# 命令行布局 API 文档

**版本：** `0.1.2`  
**最低支持核心版本：** `>=0.4.0`

> 须与 `module_info.yaml` 的 `version` / `compatible_core_versions` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> 所列入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

---

## CmdLayout

**描述：** 命令行布局门面类（Facade）— 下挂 `bar_chart` / `title` / `separator` / `icon` 命名空间（namespace）

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
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `values` | `Sequence[float]` | 连续样本 |
| `bins` (可选) | `int` | 分桶数；默认 `10` |
| `title` (可选) | `str` | 默认空 |
| `width` (可选) | `int` | 默认 `20` |
| `show_count` (可选) | `bool` | 默认 `True` |
| `show_pct` (可选) | `bool` | 默认 `True` |
| `label_format` (可选) | `str` | 边界格式，如 `".2f"` 或 `":.2f"`；默认 `".2f"` |
| `skip_empty` (可选) | `bool` | 默认 `False` |

- **返回值：** `str`
- **举例：**

```python
text = CmdLayout.bar_chart.from_values(rois, bins=10, title="ROI", label_format=".2f")
```

#### print

`CmdLayout.bar_chart.print(buckets, *, title="", width=20, show_count=True, show_pct=True, skip_empty=False, headers=None, stream=None) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 等同 `render`，并打印到 `stream`（默认标准输出 stdout）
- **参数：** 同 `render`，另加 `stream`（可选，`TextIO | None`）
- **返回值：** `str` — 与打印内容相同

#### print_from_values

`CmdLayout.bar_chart.print_from_values(values, *, bins=10, title="", width=20, show_count=True, show_pct=True, label_format=".2f", skip_empty=False, stream=None) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.1.0`
- **描述：** 等同 `from_values`，并打印到 `stream`（默认 stdout）
- **参数：** 同 `from_values`，另加 `stream`（可选）
- **返回值：** `str`

---

### title

**描述：** ASCII 标题块

#### banner

`CmdLayout.title.banner(text, *, char="*", width=None, center=False, pad=None) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 主标题：上下规则线包裹正文；未指定 `width` 时按正文终端列宽（CJK 全角计 2）加默认边距
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `text` | `str` | 标题正文 |
| `char` (可选) | `str` | 规则线字符（取首字符）；默认 `"*"` |
| `width` (可选) | `int \| None` | 规则线宽度；默认按正文推导 |
| `center` (可选) | `bool` | 是否在规则宽度内居中正文；默认 `False` |
| `pad` (可选) | `int \| None` | 未指定 `width` 时附加的边距列数；默认模块内置值 |

- **返回值：** `str`
- **举例：**

```python
CmdLayout.title.banner("枚举报告")
```

#### section

`CmdLayout.title.section(text, *, char="-") -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 小节标题，形如 `-- 文本 --`
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `text` | `str` | 小节文字 |
| `char` (可选) | `str` | 两侧装饰字符；默认 `"-"` |

- **返回值：** `str`
- **举例：**

```python
CmdLayout.title.section("枚举汇总")  # -- 枚举汇总 --
```

#### print_banner

`CmdLayout.title.print_banner(text, *, char="*", width=None, center=False, pad=None, stream=None) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 等同 `banner` 并打印到 `stream`（默认 stdout）
- **返回值：** `str`

#### print_section

`CmdLayout.title.print_section(text, *, char="-", stream=None) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 等同 `section` 并打印到 `stream`（默认 stdout）
- **返回值：** `str`

---

### separator

**描述：** ASCII 分割线

#### line

`CmdLayout.separator.line(*, char="-", width=60) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 单行分割线
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `char` (可选) | `str` | 默认 `"-"` |
| `width` (可选) | `int` | 默认 `60` |

- **返回值：** `str`

#### thick

`CmdLayout.separator.thick(*, width=60) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 粗分割线（`=`）
- **参数：** `width`（可选，默认 `60`）
- **返回值：** `str`

#### star

`CmdLayout.separator.star(*, width=60) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 星号分割线（`*`，与 banner 风格一致）
- **参数：** `width`（可选，默认 `60`）
- **返回值：** `str`

#### blank

`CmdLayout.separator.blank() -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 空行内容（打印时输出一个换行）
- **参数：** 无
- **返回值：** `str` — 空字符串

#### print_line / print_thick / print_star / print_blank

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 对应 `line` / `thick` / `star` / `blank`，并打印到 `stream`（默认 stdout）；均返回与打印内容相同的字符串
- **举例：**

```python
CmdLayout.separator.print_line(width=40)
```

---

### icon

**描述：** 跨平台图标（UTF-8 终端用 emoji；Windows 非 UTF-8 标准输出时用 ASCII 回退）

#### get

`CmdLayout.icon.get(icon_name: str) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** 按名称取图标字符串（支持别名，大小写不敏感）；未知名称返回空串
- **参数：**

| 名字 | 类型 | 说明 |
|------|------|------|
| `icon_name` | `str` | 如 `success`、`chart`（别名 → `bar_chart`） |

- **返回值：** `str`
- **举例：**

```python
CmdLayout.icon.get("success")  # ✅ 或 [OK]
```

#### i

`CmdLayout.icon.i(icon_name: str) -> str`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** `get` 的简写
- **参数：** 同 `get`
- **返回值：** `str`

#### supports_emoji

`CmdLayout.icon.supports_emoji() -> bool`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** 当前标准输出是否适合输出 emoji
- **参数：** 无
- **返回值：** `bool`
