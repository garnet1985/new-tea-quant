# progressBar

线性进度条（回测风格：紫→青渐变）。

```js
import ProgressBar from 'ui/progress/progressBar';

<ProgressBar value={42} />
<ProgressBar value={42} label="枚举信号" showPercent />
<ProgressBar size="md" /> // indeterminate
```

| 参数 | 合法值 | 默认 |
|------|--------|------|
| `value` | 0–100 / null | `null`（不确定） |
| `size` | `sm` `md` | `sm` |
| `label` | ReactNode | — |
| `showPercent` | boolean | `false` |
