# ntqHelpTooltip

统一说明 Tooltip（视觉与交互对齐 `views/ntqHelpTooltip`）。图标固定 `md`。

```js
import NtqHelpTooltip from 'ui/message/ntqHelpTooltip';

<NtqHelpTooltip title="字段含义说明" />
<NtqHelpTooltip title="注意配额" variant="warning" shine />
<NtqHelpTooltip title="更多信息" variant="info" placement="bottom" />
```

| 参数 | 合法值 | 默认 |
|------|--------|------|
| `title` | ReactNode | —（空则不渲染） |
| `variant` | `help` `info` `warning` | `help` |
| `shine` | boolean | `false` |
| `placement` | MUI placement | `top` |
| `ariaLabel` | string | 按 variant |

产品页仍可继续用 `views/ntqHelpTooltip`；本目录为设计系统标准。
