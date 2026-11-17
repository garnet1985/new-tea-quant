# tag

通用标签 / 状态小块（替代散落的 MUI `Chip`）。

```js
import Tag from 'ui/tag/tag';

<Tag status="success">已启用</Tag>
<Tag status="warning" variant="outline">待更新</Tag>
<Tag color="violet" icon="tactic">策略</Tag>
<Tag status="neutral" onDelete={() => {}}>筛选条件</Tag>
```

| 参数 | 合法值 | 默认 |
|------|--------|------|
| `status` | `success` `error` `warning` `info` `neutral` | `neutral` |
| `color` | `green` `error` `warning` `muted` `cyan` `violet` | — |
| `variant` | `soft` / `outline` / `solid` | `soft` | 产品：未达成=`outline`；已达成与分类标签=`solid` |
| `size` | `sm` `md` | `sm` |
| `icon` | NtqIcon 名 / 节点 | — |
| `onDelete` | `() => void` | — |
