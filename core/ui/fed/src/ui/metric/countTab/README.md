# countTab

带计数的筛选 Tab（列表「全部 / 归类」过滤条）。

```js
import CountTab from 'ui/metric/countTab';

<CountTab label="全部" count={12} selected={!query} wide onClick={() => setQuery('')} />
<CountTab
  label="动量"
  count={3}
  selected={query === '动量'}
  title="动量"
  onClick={() => setQuery('动量')}
/>
```

| 参数 | 合法值 | 默认 |
|------|--------|------|
| `label` | ReactNode | — |
| `count` | number / string | — |
| `selected` | boolean | `false` |
| `wide` | boolean | `false` |
| `onClick` | `() => void` | — |
| `title` | string | — |

过滤逻辑与横向滚动容器由上层实现；本组件只负责单项外观与选中态。
