# metricGrid

MetricCard 网格布局。

```js
import MetricGrid from 'ui/metric/metricGrid';
import MetricCard from 'ui/metric/metricCard';

<MetricGrid columns={2}>
  <MetricCard title="A" value="1" />
  <MetricCard title="B" value="2" />
</MetricGrid>
```

| 参数 | 合法值 | 默认 |
|------|--------|------|
| `columns` | `2` `3` `4` | `2` |
| `denseXs` | boolean | `false` |
