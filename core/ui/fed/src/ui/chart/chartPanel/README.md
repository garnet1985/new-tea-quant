# chartPanel

图表壳（ECharts）。只收 `option`；K 线等业务图由 L2 拼 option。

```js
import ChartPanel from 'ui/chart/chartPanel';
import { withChartTheme, CHART_BAR_POS, CHART_GRID_BASE } from 'ui/chart/chartTheme';

<ChartPanel
  title="每股机会数分布"
  tip="直方图"
  height={200}
  option={withChartTheme({
    grid: CHART_GRID_BASE,
    xAxis: { type: 'category', data: ['0', '1', '2'] },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: [3, 8, 2], itemStyle: { color: CHART_BAR_POS } }],
  })}
/>
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `title` / `tip` / `note` | — | 标题区 |
| `option` | — | ECharts option |
| `fallback` | `null` | 无数据占位 |
| `height` | `180` | 画布高（px 数字或 CSS） |
| `framed` | `true` | 描边框 |
| `loading` | `false` | 加载态 |
