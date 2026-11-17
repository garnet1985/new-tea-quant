# FED 写法

前端在 `fed/src`。这里是写法和目录的约定。产品结构见 `docs/`，不在本文。设计系统原语细则见 `fed/src/ui/README.md`。

`service/`、`styles/`、`ui/`、`views/`、`containers/` 已经就位。制定策略的设置、报告、执行，以及选股、决策模拟，都在 `containers/`，对外只从各自的 `index.js` 引出。`pages/` 里制定策略和选股只做进页接线。不要再新建 `components/`。

## 目录

| 目录 | 放什么 |
|------|--------|
| `api` | 和 BFF 的路径、参数、返回形状。URL 或参数变了只改这里。 |
| `service` | 全局辅助，没有界面、也没有某一页的业务。请求怎么发、超时、错误类型在这里，不在 `api`。 |
| `assets` | 图片、字体、第三方库。库自带的样式跟库走。 |
| `styles` | 全局样式：两套 CSS token（`--ui-*` 通用、`--ntq-*` 产品）、字体、MUI 主题兜底、盈亏色。Sass `$`（`_variables.scss`）待淘汰。组件自己的样式留在该组件目录。 |
| `ui` | **通用原语**（可离 NTQ 的累计公共资产）。只谈长相、token、通用交互；不写业务、不发请求、不写死路由表。 |
| `ntq-ui` | **NTQ 产品内复用壳**（导航、会员条、ReportBlock、RainbowButton 等）。组合 `ui`，用 `--ntq-*`；**路由 / 站点 URL 由应用传入**。 |
| `views` | **旧展示层（迁移中只读）**。尚未迁完的页面仍可引用；**新代码与替换优先 `ui/` + `ntq-ui/`**，不要在 `views` 里继续加新标准件。 |
| `containers` | 一块能力：业务逻辑，并拼 `ui` / `ntq-ui`（及尚未迁完的 `views`）。可以决定显示哪一块、数据怎么灌。不写颜色、间距、排版。 |
| `pages` | 路由页。进页时读路由、决定挂哪些容器、处理这一页特有的空态。 |

页面要轻。一块能力（设置、报告、版本选择、K 线、导航、守卫、AI 对话、全页引导）直接放 `containers`，不等第二个页面来了再搬。只属于这个路由的加载顺序留在 `pages`。只被一个容器用的请求封装放在那个容器旁边，不提到根上的 `service`。

图标 SVG 留在 `ui/icon/icon/icons`（旧副本仍可能在 `views`），不进 `assets`。小页面可以先是一个文件，变大再拆。

### `ui` / `ntq-ui` 怎么用（摘要）

- **通用原语（`ui`）**：`layout` / `text` / `Button` / `Icon` / `input` / `display`（头像、标签）/ `data` / `feedback`（含 `Dialog` / `HelpTooltip`）等。API 优先 `variant` + `size` + 语义 `gap`/`padding`。
- **NTQ 特有（`ntq-ui`）**：应用壳与固定模板，例如 `appBrand` / `appNav` / `pageLayout` / `becomeMemberLink` / `rainbowButton` / `reportBlock`。**路由表、站点 URL、会员资料由 container 传入**。
- **依赖方向**：`ntq-ui` → `ui`；**`ui` 禁止 import `ntq-ui`**。
- **图鉴**：手输 `/dev/ui`（合并展示两层）。含 **NTQ 业务准则**（`/dev/ui/guidelines`）。

## App 使用 UI 的硬规则

1. **`pages` / `containers` 只能使用 `ui/` 与 `ntq-ui/`**，**禁止直接 `import` `@mui/material`（或其它 UI 库）拼界面**。MUI 若出现，只允许藏在 `ui/*` / `ntq-ui/*` 内部实现里。
2. **现有组件盖不住时：优先扩展 `ui` 或 `ntq-ui`（或增加选项）**，再给业务用。确认弹层用 `Dialog`；「成为会员」用 `BecomeMemberLink`（`href` 由应用传入）。优先 `import { … } from 'ui'` / `from 'ntq-ui'`。
3. **视觉数值只用全局 CSS 变量**：通用 `--ui-*`，产品壳 `--ntq-*`。禁止业务 SCSS 新写 Sass `$`；禁止页面写死色号/间距绕过 token。

业务向的组合约定（Tag 空心/实心等）见 **NTQ 业务准则**（`/dev/ui/guidelines`）与下文 Tag 条。

## 谁引用谁

`ui` / `ntq-ui` / `views` 只接收数据，不引用 `api`、`containers`、`pages`。`containers` 可以引用 `ui`、`ntq-ui`、`views`、`api`、`service`，不引用 `pages`。`pages` 引用容器来拼这一页，自己不调用 `api`。`service` 不引用界面。

新拼装优先：`containers` → `ui` + `ntq-ui`。`views` 仅过渡；同一能力迁完后删掉对旧 view 的引用。

没有界面的公共 hook 放进 `service`。跟某一块能力走的 hook 放在那个容器旁边。

## 源文件命名

目录和 `.js` 文件用小写开头的驼峰，例如 `strategyListPage.js`。不用帕斯卡式文件名，以免和组件符号混在一起。

一个组件目录里，主文件和它的测试、服务同名，用点号标明职责：

- `abc.js`：编排。页面的进页接线、容器如何拼 view，都写在这里。
- `abc.test.js`：测 `abc.js`。
- `abc.service.js`：给这个编排提供的逻辑，不返回界面。
- `abc.service.test.js`：测这份服务。

样式固定叫 `style.scss`，不叫 `abc.scss`。`ui` / view 通常只有主文件和 `style.scss`（`ui` 另可有 `doc.js` / `README.md` 供图鉴）。服务只有一个文件时跟 `abc.js` 放在一起；拆成多个文件时再放进该目录下的 `service/`。测试跟在被测文件旁边，不另开测试目录。

目录对外只从 `index.js` 转出主组件。外面不要引用目录里的内部文件。

类、类型、枚举，以及在 JSX 里使用的函数组件名，用帕斯卡。普通函数、变量、hook 用驼峰。文件名不必和组件名逐字相同：`strategyListPage.js` 里导出 `StrategyListPage` 是正常写法。

样式 class 用 kebab-case。

## 样式

全局样式在 `styles/`：token 分两套——**`--ui-*`**（`_ui-tokens.scss`，通用原语）与 **`--ntq-*`**（`_ntq-tokens.scss`，壳/品牌/视区）；入口 `_tokens.scss`。Sass `_variables.scss` 已标淘汰，`ui/**` 禁止再用。MUI 主题只作尚未迁完控件的兜底。按钮、输入、标签、布局等**标准外观以 `ui/` 为准**，不要在业务里再铺一套。第三方库自带的 CSS 留在 `assets` 里那个库旁边。组件的样式不要收进一个总文件。

页面和组件的样式就叫 `style.scss`，放在自己的目录里。类名要能看出是谁的：根类用块名，例如 `ntq-metric-card`；子元素用 `ntq-metric-card__value`；状态用 `ntq-metric-card--compact`。样式是全局生效的，不要写没有块名的 `.title`。

改一个原语的样子，改 `ui/.../style.scss`（或通过 props / 语义 token）。修饰类仍定义在该组件里。页面自己的 `style.scss` 只排这一页的区域。

容器默认没有 `style.scss`。两块 UI 的相对位置，优先用 `ui/layout`（`Column` / `Section` / `Block`）或 NTQ 模板（如 `reportBlock`）。只是这一处拼接、没有可复用壳时，容器才可以有一份。

颜色、间距、字号用 token / 类来改（`rem` 基准 16px，正文默认 14px）：**一律走全局 `--ui-*` / `--ntq-*`**。`sx` 和 `style` 都算行内样式，原则上不用。只有运行时才知道的值可以留在行内，例如量出来的宽度、拖拽位移、图表坐标。

`html` / `body` 不要随手加 `overflow-x: auto|hidden`（会破坏 `position: sticky`）；窄于内容 `min-width` 时靠视口横向滚动即可。

### Tag（业务形态）

产品里用 `ui/tag` 时：

- **未达成 / 未完成 / 尚未配置** → `variant="outline"`（空心）
- **已达成 / 已完成 / 已配置** 以及**普通分类标签** → `variant="solid"`（实心）
- 不要用默认 `soft` 表达业务完成态；色相仍用 `status` / `color`。
