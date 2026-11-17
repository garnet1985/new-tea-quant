# rainbowButton

> 状态：**已实现** · 路径 `ntq-ui/rainbowButton`

品牌强调按钮：彩虹描边 / 色带图标。用于「运行」「助手」「帮助」等少数高曝光入口，**不是**通用 CRUD 按钮。

## 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `shape` | `'circle' \| 'pill'` | `'circle'` | 外形：圆形图标钮 / 圆角胶囊（可带文案） |
| `size` | `'sm' \| 'lg'` | `'sm'` | 圆形尺寸；胶囊主要靠自身 min-height |
| `ring` | `'spin' \| 'still' \| 'plain'` | `'spin'` | 描边：色带旋转 / 静止渐变 / 灰边无彩虹 |
| `glow` | `boolean` | `false` | 外圈光晕（助手等浮层入口常用） |
| `quiet` | `boolean` | `false` | 压暗光晕并关闭脉冲（例如对话面板已打开时） |
| `shimmer` | `boolean` | `false` | 胶囊文案上的色带流动 |
| `icon` | `'play' \| 'refresh' \| 'cancel' \| ''` | `''` | `play`/`refresh` 色带裁进图标；`cancel` 走 `Icon` |
| `mark` | `'help' \| 'ai' \| ''` | `''` | 特殊字标：问号帮助 / AI 角标 |
| `children` | `ReactNode` | — | 胶囊文案；圆形通常不用 |
| `...rest` | button HTML attrs | — | 透传原生 `button`（`onClick`、`disabled`、`aria-label` 等） |

## 使用场景

- 策略 / Tag / 数据源「运行」：`circle` + `icon="play"`
- 全局助手入口：`circle` + `mark="ai"` + `glow`
- 帮助入口：`circle` + `mark="help"`
- 强调主 CTA 胶囊：`shape="pill"` + `ring="spin"` + 文案（可 `shimmer`）
- 取消 / 次要同排：`pill` + `ring="plain"`

## 反例

- 不要用它替代 `ntqButton` 做编辑、保存、删除等常规操作
- 同一屏不要堆很多彩虹钮，会稀释强调效果
- 圆形按钮务必提供 `aria-label`（仅图标时）
- 不要在业务里复制彩虹 SCSS；统一从本组件引用

## 导入

```js
import RainbowButton from 'ntq-ui/rainbowButton';
```

> `views/rainbowButton` 现阶段只读、另作迁移；标准以本目录为准。
