# stepper

步骤条（对齐回测 stepper 视觉）。纯展示 + 可选点击；不含路由/会话。

```js
import Stepper from 'ui/steps/stepper';
import { Link } from 'react-router-dom';

<Stepper
  activeId="price"
  items={[
    { id: 'enum', label: '机会盘点', status: 'done', href: '#enum' },
    { id: 'price', label: '价格回测', status: 'running', progress: 42 },
    { id: 'portfolio', label: '投资模拟', status: 'idle', to: '/x/portfolio', component: Link },
    { id: 'decision', label: '决策模拟', status: 'idle' },
  ]}
  onItemClick={(item) => { /* … */ }}
/>

// 不要进度环
<Stepper showProgress={false} activeId="enum" items={items} />
```

## 参数

| 参数 | 说明 | 默认 |
|------|------|------|
| `items` | 步骤数组 | `[]` |
| `activeId` | 当前选中 id | `null` |
| `showProgress` | running/pending 是否画环 | `true` |
| `onItemClick` | `(item, event) => void` | — |

### item 字段

| 字段 | 说明 |
|------|------|
| `id` | 唯一键（配合 `activeId`） |
| `label` | 无障碍 / title |
| `status` | `idle` `done` `failed` `running` `pending` |
| `progress` | 0–100，仅 `running` 时有意义 |
| `no` | 圆内数字；默认序号 |
| `href` | 普通链接 / 锚点 |
| `to` + `component` | 如 `component={Link}` `to="/path"` |
| `onClick` | 单步点击 |
| `disabled` | 禁用 |

视觉：`activeId` → 激活圆；`status=done` → 绿；`failed` → 红；`running`/`pending` → 可选进度环（复用 `ProgressRing`）。
