# text

> 路径 `ui/text/text`

**行内**特殊字形。形态用 **`variant`**。普通正文不要包本组件。

| 需求 | 做法 |
|------|------|
| 普通段落 | `<p>` |
| 次要说明 / 图注 / 字段名 | `.ntq-muted` / `.ntq-caption` / `.ntq-label` |
| 链接 | `.ntq-link`（可嵌 `NtqIcon`；不是组件） |
| 行内代码字符（路径、键名） | `<Text variant="code">` · 等宽青色，无底无边 |
| 品牌彩虹字 | `<Text variant="rainbow">` |
| 青色强调 | `<Text variant="accent">` |
| 引用块 | `<Quote>`（见 `ui/text/quote`） |
| 多行代码块 | `<CodeBlock>`（见 `ui/text/codeBlock`） |
| 标题 | `<Heading level="h1"…"h5">` |

```js
<Text variant="code">/dev/ui</Text>
<Text variant="rainbow">New Tea Quant</Text>
<Text variant="accent">仅此一词</Text>

<a className="ntq-link" href="/docs">文档</a>
<a className="ntq-link" href="/dev/ui/heading">
  标题图鉴
  <NtqIcon name="chevronRight" size="sm" />
</a>
```

不单独拆 `rainbowText` / `Link` 组件——彩虹字是 `variant="rainbow"`；链接是 `.ntq-link`。
