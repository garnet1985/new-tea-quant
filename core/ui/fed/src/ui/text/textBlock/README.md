# textBlock

> 路径 `ui/text/textBlock`

说明性文本块（摘要、提示、列表说明）。**不是标题**——标题用 `Heading`；**不是引用**——引用用 `Quote`。

```js
import TextBlock from 'ui/text/textBlock';

<TextBlock bar="cyan" surface="soft">用途说明…</TextBlock>
<TextBlock bar="warning" surface="soft">
  <ul>
    <li>反例一条</li>
  </ul>
</TextBlock>
```

| 参数 | 取值 | 默认 |
|------|------|------|
| `bar` | `cyan`…`muted` | `cyan` |
| `surface` | `none`…`gradient` | `soft` |
| `radius` | `none`…`lg` | `md` |
| `padding` | `none`…`xl` | `md` |

上方已有带竖条的 `Heading` 时，正文用普通 `Block` / 列表即可，不必再套一层竖条文本块。
