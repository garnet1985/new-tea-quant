# heading

> 路径 `ui/text/heading`

| 参数 | 说明 |
|------|------|
| `level` | `h1`…`h5`：标签 + **固定字号阶梯** |
| `variant` | `plain`（默认）\| `bar`（左侧竖条） |
| `tone` | 竖条色（仅 `bar`） |
| `subtitle` / `subtitlePlacement` | 副标题；`below` \| `inline` |
| `gap` | `none` \| `md`（默认）\| `lg` |

块距约定：父级 `gap = 1rem`。标题在此之上再补上边距——`md` 视觉 **1.5rem**，`lg` 视觉 **2rem**；下边距仍由父级 gap（1rem）承担。

```js
<Heading level="h2">区块标题</Heading>
<Heading level="h2" variant="bar" tone="cyan">带竖条</Heading>
<Heading level="h3" gap="none">侧栏紧凑</Heading>
```
