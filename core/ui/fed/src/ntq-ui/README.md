# `src/ntq-ui` — NTQ 特有公用组件

应用壳与产品向固定模板（导航、面包屑、页头 Banner、页壳、会员条、彩虹按钮、报告区块等）。

与 `src/ui` **通用原语**分开：这里组合 `ui`，并使用 **`--ntq-*`** 产品变量（`styles/_ntq-tokens.scss`）。通用尺度仍走 `--ui-*`。

**硬规则**

- `ntq-ui` 可以依赖 `ui`；**`ui` 禁止依赖 `ntq-ui`**
- 尺度用 `--ntq-*` / `--ui-*`；禁止 Sass `$` 设计变量
- 路由表 / 站点 URL / 业务映射由应用层传入，不写死在组件里

| 组件 | 状态 | 说明 |
|------|------|------|
| `appBrand` | ready | 顶栏品牌标 |
| `appVersion` | ready | 顶栏版本号展示（label 由 container 传入） |
| `appNav` | ready | 顶栏导航壳（`items` 驱动） |
| `appBreadcrumbs` | ready | 面包屑（`items` + `current`） |
| `pageBanner` | ready | 页头标题条 |
| `pageLayout` | ready | 标准页壳（面包屑 + Banner + 正文） |
| `memberStrip` | ready | 顶栏会员挂角展示壳 |
| `proBadge` | ready | Pro 彩虹描边徽章 |
| `becomeMemberLink` | ready | 「成为会员」注册入口（`href` 由应用传入） |
| `rainbowButton` | ready | 品牌强调按钮（运行 / 助手等；非通用 CRUD） |
| `reportBlock` | ready | 回测/报告小节固定壳 |
| `pythonDictEditor` | ready | JSON / Python dict 调试面板 |
| `pageBackground` | ready | 主壳随机背景 |
| `updateStatusChip` | ready | 数据/计算更新状态 |
| `descriptionText` | ready | 多行说明文案（可截断） |
| `globalHelper` | ready | 页面引导遮罩卡 + 问号 FAB（路由/文案目录在 containers） |

```js
import { BecomeMemberLink, MemberStrip, RainbowButton, PageLayout } from 'ntq-ui';
```

图鉴 `/dev/ui` 合并展示本目录与 `ui`。组件用法以图鉴 + 各组件 `doc.js` 为准；**不要**再给每个组件加 `README.md`。
