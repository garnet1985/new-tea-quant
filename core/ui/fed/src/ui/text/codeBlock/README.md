# codeBlock

> 路径 `ui/text/codeBlock`

多行代码块。等宽字体；表面 / 圆角用语义 token。

**行内**路径、短代码用 `<Text variant="code">`，不要用本组件。

```js
import CodeBlock from 'ui/text/codeBlock';

<CodeBlock language="js">{`const n = 1;`}</CodeBlock>
```

| 参数 | 取值 | 默认 |
|------|------|------|
| `language` | 字符串（仅标注） | `''` |
| `surface` | `none`…`gradient` | `panel` |
| `radius` | `none`…`lg`（`pill` 回落 `lg`） | `md` |
| `padding` | `none`…`xl` | `md` |
| `bordered` | boolean | `true` |

语法高亮（highlight.js 等）暂未接入；需要时再加，不改调用方结构。
