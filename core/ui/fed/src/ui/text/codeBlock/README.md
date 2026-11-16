# codeBlock

> 路径 `ui/text/codeBlock`

多行代码块。**默认科技玻璃**；另有一个轻底变种。

**行内**路径、短代码用 `<Text variant="code">`，不要用本组件。

```js
import CodeBlock from 'ui/text/codeBlock';

<CodeBlock language="js">{`const n = 1;`}</CodeBlock>
<CodeBlock variant="soft">{`npm run start`}</CodeBlock>
```

| 参数 | 取值 | 默认 |
|------|------|------|
| `variant` | `glass` \| `soft` | `glass` |
| `language` | 字符串（仅标注，落在上 padding 内） | `''` |

圆角 / 描边 / 内边距固定，不开放。语法高亮暂未接入。
