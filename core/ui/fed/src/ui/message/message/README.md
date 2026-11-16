# message

消息条：状态模式（固定 icon）或颜色模式（icon 可传/省略）。

```js
import Message from 'ui/message/message';

// 状态：图标固定
<Message status="success">已保存。</Message>
<Message status="info">一般说明（青色）。</Message>
<Message status="warning" variant="banner">通栏警告。</Message>

// 颜色：可省略或传入 icon
<Message color="violet">紫色说明</Message>
<Message color="muted">中性白边</Message>
<Message color="cyan" icon="settings">带图标</Message>
```

| 参数 | 合法值 | 默认 |
|------|--------|------|
| `status` | `success` `error` `warning` `info` | `info` |
| `color` | `green` `error` `warning` `muted` `cyan` `violet` | — |
| `variant` | `inline`（圆角、无 bar）`banner`（有 bar、无圆角） | `inline` |
| `icon` | 图标名 / 节点；**仅颜色模式** | 省略=无图标 |
| `onClose` | `() => void` | — |

内边距 `1rem`；状态图标 `xl`（2rem，与文案垂直居中）：`success`→success · `error`→cancel · `warning`→warning · `info`→info（青）。更大场景用 `NtqIcon size="xxl"`（3rem）。
