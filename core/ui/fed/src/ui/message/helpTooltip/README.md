# helpTooltip

统一说明 Tooltip。图标固定 `md`。CSS 根类暂仍为 `.ntq-help-tooltip*`。

```js
import HelpTooltip from 'ui/message/helpTooltip';
// 或：import { HelpTooltip } from 'ui';

<HelpTooltip title="字段含义说明" />
<HelpTooltip title="注意配额" variant="warning" shine />
<HelpTooltip title="更多信息" variant="info" placement="bottom" />
```

| 参数 | 合法值 | 默认 |
|------|--------|------|
| `title` | ReactNode | —（空则不渲染） |
| `variant` | `help` `info` `warning` | `help` |
| `shine` | boolean | `false` |
| `placement` | MUI placement | `top` |
| `ariaLabel` | string | 按 variant |
