# FED 写法

前端在 `fed/src`。这里是写法和目录的约定。产品结构见 `docs/`，不在本文。

`service/`、`styles/`、`views/` 和 `containers/` 已经就位。展示放 `views/`，能力放 `containers/`。不要再新建 `components/`。

## 目录

| 目录 | 放什么 |
|------|--------|
| `api` | 和 BFF 的路径、参数、返回形状。URL 或参数变了只改这里。 |
| `service` | 全局辅助，没有界面、也没有某一页的业务。请求怎么发、超时、错误类型在这里，不在 `api`。 |
| `assets` | 图片、字体、第三方库。库自带的样式跟库走。 |
| `styles` | 全局样式：SCSS 变量、字体、MUI 主题、盈亏色。组件自己的样式留在该组件目录。 |
| `views` | 根上的展示组件。一组件一目录，含样式、逻辑和已有测试。不写业务，不发请求。 |
| `containers` | 一块能力：业务逻辑，并拼 `views`。可以决定显示哪一块、数据怎么灌。不写颜色、间距、排版。 |
| `pages` | 路由页。进页时读路由、决定挂哪些容器、处理这一页特有的空态。 |

页面要轻。一块能力（设置、报告、版本选择、K 线、导航、守卫、AI 对话、全页引导）直接放 `containers`，不等第二个页面来了再搬。只属于这个路由的加载顺序留在 `pages`。只被一个容器用的请求封装放在那个容器旁边，不提到根上的 `service`。

NTQ 图标的 SVG 留在图标组件目录里，不进 `assets`。小页面可以先是一个文件，变大再拆。

## 谁引用谁

`views` 只接收数据，不引用 `api`、`containers`、`pages`。`containers` 可以引用 `views`、`api`、`service`，不引用 `pages`。`pages` 引用容器来拼这一页，自己不调用 `api`。`service` 不引用界面。

没有界面的公共 hook 放进 `service`。跟某一块能力走的 hook 放在那个容器旁边。

## 源文件命名

目录和 `.js` 文件用小写开头的驼峰，例如 `strategyListPage.js`。不用帕斯卡式文件名，以免和组件符号混在一起。

一个组件目录里，主文件和它的测试、服务同名，用点号标明职责：

- `abc.js`：编排。页面的进页接线、容器如何拼 view，都写在这里。
- `abc.test.js`：测 `abc.js`。
- `abc.service.js`：给这个编排提供的逻辑，不返回界面。
- `abc.service.test.js`：测这份服务。

样式固定叫 `style.scss`，不叫 `abc.scss`。view 通常只有 `abc.js` 和 `style.scss`。服务只有一个文件时跟 `abc.js` 放在一起；拆成多个文件时再放进该目录下的 `service/`。测试跟在被测文件旁边，不另开测试目录。

目录对外只从 `index.js` 转出主组件。外面不要引用目录里的内部文件。

类、类型、枚举，以及在 JSX 里使用的函数组件名，用帕斯卡。普通函数、变量、hook 用驼峰。文件名不必和组件名逐字相同：`strategyListPage.js` 里导出 `StrategyListPage` 是正常写法。

样式 class 用 kebab-case。

## 样式

全局样式在 `styles/`：变量、mixin、全站骨架，另加一份 MUI 覆盖。按钮和输入框跟着 MUI 主题走。第三方库自带的 CSS 留在 `assets` 里那个库旁边。组件的样式不要收进一个总文件。

页面和 view 的样式就叫 `style.scss`，放在自己的目录里。类名要能看出是谁的：根类用块名，例如 `ntq-metric-card`；子元素用 `ntq-metric-card__value`；状态用 `ntq-metric-card--compact`。样式是全局生效的，不要写没有块名的 `.title`。

改一个 view 的样子，改那个 view 的 `style.scss`，或者由容器传入修饰类。修饰类仍定义在 view 里。页面自己的 `style.scss` 只排这一页的区域。

容器默认没有 `style.scss`。两块 view 的相对位置，优先做成一个负责排布的 view。只是这一处拼接、没有可复用的 view 时，容器才可以有一份。

颜色、间距、字号用类或变量来改。`sx` 和 `style` 都算行内样式，原则上不用。只有运行时才知道的值可以留在行内，例如量出来的宽度、拖拽位移、图表坐标。
