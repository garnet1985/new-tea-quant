# sideNav

左侧目录壳（竖排项 + 选中态）。

```js
import SideNav from 'ui/layout/sideNav';
import Column from 'ui/layout/column';

<Column variant="sidebar" gap="none" divider="line">
  <SideNav
    variant="line"
    activeId={categoryId}
    items={[
      { id: 'layout', label: '布局', to: '/dev/ui/layout', meta: 4 },
      { id: 'button', label: '按钮', to: '/dev/ui/button', meta: 2 },
    ]}
  />
  <main>{/* Outlet / 内容 */}</main>
</Column>
```

| 参数 | 合法值 | 默认 |
|------|--------|------|
| `variant` | `line` `rail` | `line` |
| `items` | `{ id, label, to?, meta? }[]` | `[]` |
| `activeId` | string | `''` |

同页切面板用 `Tabs variant="side"`；全站顶栏用 `AppNav`。
