# metricCard

报告指标卡。

```js
import MetricCard from 'ui/metric/metricCard';

<MetricCard title="机会总数" value="128" tip="统计窗口内触发次数" />
<MetricCard title="涨停无法买入" value="12 / 100" hint="占比 12%" />
```

| 参数 | 说明 | 默认 |
|------|------|------|
| `title` | 指标名 | — |
| `value` | 主值 | — |
| `hint` | 次要说明 | — |
| `tip` / `titleTip` | 标题旁帮助 | — |

网格布局用 `MetricGrid`。
