# appBreadcrumbs

NTQ 面包屑。

```js
import AppBreadcrumbs from 'ntq-ui/appBreadcrumbs';

<AppBreadcrumbs
  items={[{ label: '策略', to: '/strategies' }]}
  current="动量策略"
/>
```

| 参数 | 默认 | 说明 |
|------|------|------|
| `items` | `[]` | `{ label, to }[]` 祖先链 |
| `current` | — | 当前页 |
