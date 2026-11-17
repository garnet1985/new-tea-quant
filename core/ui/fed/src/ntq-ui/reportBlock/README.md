# reportBlock

报告区块固定模板（对齐旧 `views/sectionBlock`）。

```js
import ReportBlock from 'ntq-ui/reportBlock';
import MetricGrid from 'ui/metric/metricGrid';
import MetricCard from 'ui/metric/metricCard';

<ReportBlock title="机会盘点" tip="统计窗口说明">
  <MetricGrid columns={2}>
    <MetricCard title="机会总数" value="128" />
    <MetricCard title="完整度" value="96%" />
  </MetricGrid>
</ReportBlock>
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `title` | — | 标题 |
| `tip` | — | 帮助 |
| `action` | `null` | 右侧操作 |
| `children` | — | 内容 |
