# heading

> 路径 `ui/text/heading`

| 参数 | 说明 |
|------|------|
| `level` | `h1`…`h5`：标签 + **固定字号阶梯**（越大越靠前，不可单独改 font-size） |
| `variant` | `plain`（默认）\| `bar`（左侧竖条，参考官网） |
| `tone` | 竖条色：`cyan` `violet` `green` `warning` `error` `muted`（仅 `bar`） |
| `subtitle` | 副标题（更小、muted） |
| `subtitlePlacement` | `below`（默认）\| `inline` |
| `gap` | `none`…`xl`：上下外边距，**上 > 下 > 普通段落间距** |

```js
<Heading level="h1">页面标题</Heading>
<Heading level="h2" subtitle="一句话说明">区块标题</Heading>
<Heading level="h2" subtitle="行内副题" subtitlePlacement="inline">标题</Heading>
<Heading level="h2" variant="bar" tone="cyan">带竖条</Heading>
<Heading level="h3" variant="bar" tone="warning">小节</Heading>
<Heading level="h3" gap="none">侧栏紧凑</Heading>
```

`variant="bar"` 时：标题上下与左侧加一点 padding，再画竖条；**无背景**。

改间距：覆盖 `--ntq-heading-gap-*-mt/mb`；改竖条：`--ntq-heading-bar-*`。
