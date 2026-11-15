# ntqButton

> 状态：**已实现** · 路径 `ui/button/ntqButton`

产品内默认的矩形操作按钮。基于 MUI `Button`，用 NTQ 视觉变体覆盖样式。

## 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `variant` | `'glass' \| 'primary' \| 'attention' \| 'ghost'` | `'glass'` | 视觉变体：玻璃描边 / 主色实心 / 吸睛描边 / 轻量文本 |
| `icon` | `string` | `''` | 可选前置图标名，走 `NtqIcon` 注册表（如 `add`、`settings`） |
| `iconSize` | `'sm' \| 'md' \| 'lg' \| 'xl'` | `'md'` | 前置图标尺寸 token |
| `children` | `ReactNode` | — | 按钮文案 |
| `...rest` | MUI Button props | — | 透传（`onClick`、`disabled`、`size`、`type` 等）。`variant` / `color` / `startIcon` / `className` 由本组件接管 |

## 使用场景

- 对话框主操作 / 取消：`primary` + `ghost`
- 列表行内次要操作：`glass`（可配 `size="small"`）
- 需要短暂吸引注意的入口：`attention`
- 带图标的工具操作：`glass` / `primary` + `icon`

## 反例

- 不要在业务页直接用裸 MUI `Button` 冒充规范按钮
- 不要用 `rainbowButton` 做普通 CRUD；那是强调态 / 品牌态圆形或胶囊按钮
- 不要把业务布局逻辑塞进按钮
- 不要同时传入 MUI 的 `variant` / `color` 期望覆盖 NTQ 变体——会被本组件覆盖

## 导入

```js
import NtqButton from 'ui/button/ntqButton';
```

> `views/ntqButton` 现阶段只读、另作迁移；标准以本目录为准。
