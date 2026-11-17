# progressRing

圆环进度（对齐回测 step 环：细描边、青色）。

```js
import ProgressRing from 'ui/progress/progressRing';

<ProgressRing value={65} showPercent />
<ProgressRing value={40} label="回测" showPercent />
<ProgressRing /> // indeterminate
<ProgressRing value={80} size="sm">{3}</ProgressRing>
```

| 参数 | 合法值 | 默认 |
|------|--------|------|
| `value` | 0–100 / null | `null`（不确定） |
| `size` | `sm` `md` | `md` |
| `label` | ReactNode | — |
| `showPercent` | boolean | `false` |
| `children` | ReactNode | —（覆盖环心） |
