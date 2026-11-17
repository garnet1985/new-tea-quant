# tipLabel

一行文字 + 可选 HelpTooltip。

## 参数

| Prop | 默认 | 说明 |
|------|------|------|
| `children` | — | 标签文案 |
| `tip` | `''` | 说明；空则不渲染问号 |
| `shine` | `false` | HelpTooltip 高亮 |
| `variant` | `'section'` | `section` / `caption` / `field` / `title` |
| `component` | `'span'` | 文案标签名（如 `h3`） |
| `textClassName` | `''` | 覆盖预设字号类 |
| `placement` | `'top'` | tooltip 方向 |
| `className` | `''` | 根节点；可用 `ntq-tip-label--below` |

## 使用场景

区块标题、表单字段标签、手风琴标题旁的说明。

## 反例

不要用 TipLabel 代替完整 Field 标签行（带 hint/error 时用 `ui` Field）。
