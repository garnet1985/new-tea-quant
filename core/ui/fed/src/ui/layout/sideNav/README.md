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
| `variant` | `line`（底边） `rail`（左侧色条高亮，设置页） | `line` |
| `radius` | `sm` `none`（扩展直角） | `sm` |
| `sticky` | `true` `false` | `false` |
| `items` | `{ id, label, to?, meta? }[]` | `[]` |
| `activeId` | string | `''` |

`sticky`：仅菜单贴顶。侧栏还有标题 / 说明要一起贴顶时，用外层 `<Block sticky>`，SideNav 不再开 sticky。

同页切面板用 `Tabs variant="side"`；全站顶栏用 `AppNav`。
