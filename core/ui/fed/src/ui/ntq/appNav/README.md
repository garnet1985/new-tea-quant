# appNav

NTQ 顶栏导航壳（items 驱动）。

```js
import AppNav from 'ui/ntq/appNav';

<AppNav
  items={[
    { label: '制定策略', to: '/strategy-design', icon: 'tactic' },
    { label: '策略选股', to: '/scan', icon: 'monitoring' },
    {
      label: '高级功能',
      icon: 'dataObject',
      match: '/advanced',
      children: [
        { label: '特征标签', to: '/advanced/tags' },
        { label: '数据源', to: '/advanced/data-sources' },
      ],
    },
    { label: '文档', href: 'https://example.com/docs', icon: 'help' },
    { label: '设置', to: '/settings/membership', icon: 'settings', match: '/settings' },
  ]}
/>
```

需在 React Router 树内使用（`useLocation` / `Link`）。产品路由表与站点 URL 由应用层组装后传入。
