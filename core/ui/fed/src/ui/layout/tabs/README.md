# tabs

> 路径 `ui/layout/tabs`

布局 Tab 原语。

| `variant` | 形态 |
|-----------|------|
| `top`（默认） | 上方横排页签，下方内容 |
| `side` | 左侧竖排导航，右侧内容（窄屏自动改横排） |

```js
import Tabs from 'ui/layout/tabs';

<Tabs
  variant="top"
  items={[
    { id: 'overview', label: '概览', content: <p>概览内容</p> },
    { id: 'detail', label: '详情', content: <p>详情内容</p> },
  ]}
/>

<Tabs
  variant="side"
  defaultValue="general"
  items={[
    { id: 'general', label: '通用', content: <p>通用设置</p> },
    { id: 'account', label: '账户', content: <p>账户设置</p> },
  ]}
/>
```

| 参数 | 默认 |
|------|------|
| `variant` | `top` |
| `gap` | `md`（1rem，列表与面板之间） |
| `value` / `defaultValue` / `onChange` | 受控 / 非受控 |
