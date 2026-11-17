# button

> 状态：**已实现** · 路径 `ui/button/button`

通用矩形操作按钮。基于 MUI `Button`。CSS 根类暂仍为 `.ntq-button`。

## 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `variant` | `'glass' \| 'primary' \| 'danger' \| 'attention' \| 'ghost'` | `'glass'` | 视觉变体；`danger`=红实底无动画 |
| `radius` | `'default' \| 'none'` | `'default'` | 扩展：`none`=直角 |
| `icon` | `string` | `''` | 图标名；无文案时为纯图标按钮 |
| `iconPlacement` | `'start' \| 'end'` | `'start'` | 图标在前 / 在后 |
| `iconSize` | `'sm' \| 'md' \| 'lg' \| 'xl'` | `'md'` | 图标尺寸 |
| `tooltip` | `string` | `''` | 悬停说明 |
| `children` | `ReactNode` | — | 文案；省略则为纯图标 |
| `href` / `component` | MUI 链接 props | — | 按钮样式的超链接 |
| `...rest` | MUI Button props | — | `onClick`、`disabled`、`size`、`aria-label` 等 |

## 用法

```js
import Button from 'ui/button/button';
// 或：import { Button } from 'ui';
import { Link as RouterLink } from 'react-router-dom';

<Button icon="add">添加</Button>
<Button icon="chevronRight" iconPlacement="end">下一步</Button>
<Button icon="settings" tooltip="设置" aria-label="设置" />
<Button href="https://example.com" target="_blank" rel="noreferrer">外链</Button>
{/* ↑ http(s) / target=_blank 且未传 icon 时，自动后置 chevronRight */}
<Button component={RouterLink} to="/dev/ui">图鉴</Button>
```

外链无专用「跳出」图标；约定用后置 `chevronRight`（`>`）表示。行内文字链用 `.ntq-link`。

## 反例

- 纯图标禁止省略 `tooltip` / `aria-label`
- 不要用裸 MUI `Button` 冒充规范按钮
- 不要用 `RainbowButton`（`ntq-ui`）做普通 CRUD
