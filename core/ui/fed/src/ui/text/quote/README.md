# quote

> 路径 `ui/text/quote`

引用块，**只有一种固定样式**：左边白色竖条、轻微白底、四面缩进、斜体。无间距 / 字号 / 颜色变体。

```js
import Quote from 'ui/text/quote';

<Quote>优先用语义 token，不要在调用处写死像素。</Quote>
```

说明性提示 / 警告列表用 `TextBlock`；本组件只表达引用语气。
