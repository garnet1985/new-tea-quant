# ntqButton

> 状态：**已实现** · 路径 `ui/button/ntqButton`

产品内默认的矩形操作按钮。基于 MUI `Button`。

## 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `variant` | `'glass' \| 'primary' \| 'attention' \| 'ghost'` | `'glass'` | 视觉变体 |
| `icon` | `string` | `''` | 图标名；无文案时为纯图标按钮 |
| `iconPlacement` | `'start' \| 'end'` | `'start'` | 图标在前 / 在后 |
| `iconSize` | `'sm' \| 'md' \| 'lg' \| 'xl'` | `'md'` | 图标尺寸 |
| `tooltip` | `string` | `''` | 悬停说明 |
| `children` | `ReactNode` | — | 文案；省略则为纯图标 |
| `href` / `component` | MUI 链接 props | — | 按钮样式的超链接 |
| `...rest` | MUI Button props | — | `onClick`、`disabled`、`size`、`aria-label` 等 |

## 用法

```js
import NtqButton from 'ui/button/ntqButton';
import { Link as RouterLink } from 'react-router-dom';

<NtqButton icon="add">添加</NtqButton>
<NtqButton icon="chevronRight" iconPlacement="end">下一步</NtqButton>
<NtqButton icon="settings" tooltip="设置" aria-label="设置" />
<NtqButton href="https://example.com" target="_blank" rel="noreferrer">外链</NtqButton>
<NtqButton component={RouterLink} to="/dev/ui">图鉴</NtqButton>
```

行内文字链用 `.ntq-link`（见文字规范），不要用本组件冒充正文链接。

## 反例

- 纯图标禁止省略 `tooltip` / `aria-label`
- 不要用裸 MUI `Button` 冒充规范按钮
- 不要用 `rainbowButton` 做普通 CRUD
