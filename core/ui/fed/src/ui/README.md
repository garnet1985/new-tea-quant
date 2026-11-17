# `src/ui` — 设计系统原语

本目录是**可累计的通用原语**（可离 NTQ）。产品壳在并列的 [`src/ntq-ui`](../ntq-ui/README.md)。

## 组件两层 + 变量两套

| 层 | 目录 | 变量 | 说明 |
|----|------|------|------|
| **通用原语** | `src/ui/<大类>/` | **`--ui-*`**（`styles/_ui-tokens.scss`） | 可脱离 NTQ 复用；独立视觉尺度 |
| **NTQ 公用** | `src/ntq-ui/` | **`--ntq-*`**（`styles/_ntq-tokens.scss`） | 壳 / 品牌 / 顶栏等产品层，组合通用原语 |
| **业务 mapping** | （尚未建目录） | — | 业务枚举 → 组件 props；不进图鉴 |

**`ui` 禁止依赖 `ntq-ui`。**

- 入口：`styles/_tokens.scss`（加载两套 + 过渡期把旧 `--ntq-space-*` 等别名到 `--ui-*`）。
- **禁止**在 `ui/**` 使用 Sass `$` 设计变量；尺度一律 `--ui-*` / `--ntq-*`。
- `@media` 断点写字面量并注释 `sync: --ui-…` / `--ntq-…`（media 不能可靠读 CSS 变量）。

## App 硬规则（与 `FED_STANDARD.md` 一致）

1. **`pages` / `containers` 只消费 `ui/` 与 `ntq-ui/`**，禁止直接使用 MUI（或其它 UI 库）拼页面。MUI 仅可藏在原语内部。
2. **缺口优先扩展 `ui` / `ntq-ui` 或增加选项**，再给业务用；不要在页面用临时样式 / 直连 MUI 绕过。
3. **变量用全局 CSS token**（`--ui-*` / `--ntq-*`），业务侧不另起一套 Sass `$` 或裸色号。

### Tag 业务用法

| 语义 | `variant` |
|------|-----------|
| 未达成 / 未完成 / 尚未配置 | `outline`（空心） |
| 已达成 / 已完成 / 已配置 | `solid`（实心） |
| 普通分类标签（非「未完成」态） | `solid`（实心） |

| 层 | 放什么 | 例子 |
|----|--------|------|
| **通用原语** | 元素与布局：长相、token、通用交互 | `Tag`、`DataGrid`、`Column`、`TextField` |
| **NTQ 公用** | 应用壳与高复用产品模板 | `appNav`、`pageLayout`、`memberStrip`、`reportBlock` |
| **业务 mapping** | 业务枚举 / 状态 → 组件 props | freshness→Tag；`buildMarketChartOption`→ChartPanel |

通用原语不收业务 status key；数据新鲜度等 mapping 用 **`ntq-ui/updateStatusChip`**（图鉴 ntq 栏）。

回测报告小节用 NTQ 固定模板 **`reportBlock`**，内部再拼
`MetricCard`/`MetricGrid`/`ChartPanel`/`Message`；不要各页自造边框壳，避免 agent 实现五花八门。

## 约定

- 只放 **L1 设计原语**（布局、按钮、输入、标题、消息、进度、步骤、图标、指标…）。
- **layout**：`column` / `block` / `section` / `tabs` / `sideNav` / `accordion` / `listToolbar` / `categoryChipStrip`（不含 Banner、面包屑）。
  - `Column`：版式 + `gap` + `divider`（竖线分栏）。
  - `Block`：`surface`（soft/panel/glass/gradient）+ `radius`（含 pill）+ `bordered`。
  - `Section`：纵向堆叠 + `gap`；表面仍用内嵌 Block。
  - `Tabs`：`variant="top"` 上方切换；`variant="side"` 左右分栏（同页切 panel）。
  - `SideNav`：左侧目录壳（`line` / `rail`）；可选 `sticky` 贴顶。整栏（标题+菜单）贴顶用外层 `Block sticky`。栏宽用 Column sidebar，右栏自管（Outlet 等）。
  - `Accordion`：折叠区块（panel / nested）；收起仍挂载子树。
  - `ListToolbar`：列表搜索 + 操作槽 + 可选 hint。
  - `CategoryChipStrip`：「全部」+ 横向滚动归类 CountTab。
- **text**（图鉴 `/dev/ui/text`）：`text` / `heading` / `separator` / `quote` / `textBlock` / `codeBlock`。磁盘仍在 `ui/text/*`。普通正文 / 链接用 HTML + class（`.ntq-muted` / `.ntq-link` 等）。
- **button**：`Button`（前后图标、纯图标、tooltip、`href`/`component` 外链自动后置 `>`）。品牌彩虹钮在 **`ntq-ui/rainbowButton`**。
- **display**（图鉴 `/dev/ui/display`）：`Icon`；`avatar`；`tag`；`definitionList`。业务 Freshness 映射属 L2。
- **data**（图鉴 `/dev/ui/data`）：`dataGrid`；`chartPanel`；`monthCalendar`；`metricCard` / `metricGrid`；`countTab` / `countBadge`。
- **input**：`field`；`textField` / `textArea`；`checkbox`；`radio`；`switch`；`select`；`searchSelect`；`searchField`；`autocomplete`；`date` / `dateRange`。
- **feedback**：`message` / `dialog` / `toast` / `HelpTooltip`；`loadingBars` / `loading` / `progressBar` / `progressRing`；`stepper`。
- **ntq-ui**（图鉴仍挂在 `/dev/ui/ntq`）：见 [`ntq-ui/README.md`](../ntq-ui/README.md)。
- 隐形图鉴 `/dev/ui` 合并展示 `ui` + `ntq-ui`。CSS 根类暂多仍为 `.ntq-*`（后续可改为 `ui-*`）。

### 统一导出（barrel）

```js
import { Section, Heading, Message, Dialog, Button, Icon, TextField } from 'ui';
import { BecomeMemberLink, MemberStrip, AppNav, RainbowButton } from 'ntq-ui';
```

深层路径仍可用；新代码优先 barrel。

## 命名：统一用 `variant` + `size`

| 参数 | 用途 | 例子 |
|------|------|------|
| **`variant`** | 形态 / 角色 | `Column variant="thirds"`、`Button variant="primary"`、`Loading variant="page"`、`Text variant="code"` |
| **`size`** | 尺寸档位 | `Icon size="md"`、`ProgressBar size="sm"`、`LoadingBars size="md"` |
| **`gap` / `padding`** | 间距 token | `none`…`xxs`…`xl` → `--ui-space-*` |

不要再用 `kind` 作为组件 API（业务域里的 job.kind 等除外）。

## 图鉴样本（`/dev/ui` 样例）

每个组件的样例通常按下面五个维度组织（没有的维度标明「不适用」，不要硬凑）：

1. **形态** — `variant`、`name`、`surface` 等全量枚举（过多再商量是否折叠）
2. **大小** — `size` / `iconSize` 等档位
3. **间距** — `gap` / `padding` 等
4. **颜色** — `tone` / 表面色等
5. **外观** — 圆角、描边、`shape`、动画等

展示文案用中文；仅参数名与取值保留英文，避免中英夹杂。

实现：`pages/uiPrototype/showcases/sample.js`（`SampleDim` / `SampleRow` / `SampleNA`）。

## Token 优先（禁止裸数字）

rem 基准：`html` 保持 **16px**（1rem = 16px）。默认正文 **14px**（`0.875rem` / `--ntq-font-normal`）：`body` + MUI `typography.body1` + `CssBaseline` 已对齐。`p` / `span` / `strong` 继承 body。字号与间距用 **rem** token，不要写裸 `px`。

### 块级堆叠（只走父级 gap）

| 角色 | 上下距 | 做法 |
|------|--------|------|
| 默认块 | **1rem** | 父级 `gap: var(--ntq-stack)`（`Section` 默认 `md`） |
| 标题 | 上 **1.5rem**（`lg`→**2rem**）/ 下 **1rem** | 父 gap 1rem + Heading 补上边距 |
| 分隔线 | 上下 **1rem** | 只靠父 gap；自身 `margin: 0` |

不要把子项 `margin-block` 和父级 `gap` 混用。

| 维度 | 合法值 | 全局变量（通用 `--ui-*`；过渡别名仍有 `--ntq-*`） |
|------|--------|----------|
| 间距 | `none` `xxs` `xs` `sm` `md` `lg` `xl` | `--ui-space-*` |
| 字号 | `xs` `sm` `normal` `md` `lg` `xl` | `--ui-font-*`（`normal` = 0.875rem） |
| 图标 | `sm` `md` `lg` `xl` `xxl` | `--ui-icon-*` |
| 圆角 | `none` `sm` `md` `lg` `pill` | `--ui-radius-*` |
| 表面 | `none` `soft` `panel` `glass` `gradient` | `--ui-surface-*`（Block；玻璃底可由 NTQ 注入） |
| 分隔 | `none` `line` | `--ui-divider-color` |

```js
// ✅
<Column variant="thirds" gap="md" />
<Heading level="h1">页面标题</Heading>
<Heading level="h2" variant="bar" tone="cyan" subtitle="说明">区块</Heading>
<p className="ntq-muted">次要说明</p>
<a className="ntq-link" href="/dev/ui">文字图鉴</a>
<Quote>优先用语义 token。</Quote>
<Text variant="code">/dev/ui</Text>
<Icon name="settings" size="md" />
<Loading variant="inline" />
<ProgressBar value={42} label="枚举信号" showPercent />
<ProgressRing value={65} label="回测" showPercent />
<Stepper
  activeId="price"
  items={[
    { id: 'enum', label: '机会盘点', status: 'done', href: '#enum' },
    { id: 'price', label: '价格回测', status: 'running', progress: 42 },
  ]}
/>
<Tag status="success">已启用</Tag>
<Tag color="violet" variant="outline">策略</Tag>
<CountTab label="全部" count={n} selected={!q} wide onClick={…} />
<CountBadge count={3} label="信号数" />
<MetricGrid columns={2}>
  <MetricCard title="机会总数" value="128" tip="…" />
</MetricGrid>
<DataGrid rows={rows} columns={columns} loading={loading} autoHeight />
<ChartPanel title="分布" tip="…" option={withChartTheme(option)} height={200} />
<TextField label="名称" value={v} onChange={…} />
<RadioGroup label="频率" value={f} options={[…]} onChange={…} />
<Message status="info">同步已完成。</Message>
<Message status="warning" variant="banner">维护窗口即将开始。</Message>
<Message color="violet" icon="chat">装饰性说明</Message>
showToast({ status: 'success', content: '已保存' });

// ❌
<Column kind="thirds" />
<Block padding={16} />
<p style={{ fontSize: 14 }}>...</p>
```

普通文字 class：`.ntq-muted` / `.ntq-caption` / `.ntq-label` / `.ntq-link`（`styles/_typography.scss`）。

改数值：覆盖 `styles/_ui-tokens.scss` / `_ntq-tokens.scss`（经 `_tokens.scss` 加载），不要在调用处写死像素；不要新增 Sass `$`。

表面风格约定：科技玻璃为默认（如 `CodeBlock variant="glass"`），最多再留一个轻变种（如 `soft`）。**Input 例外**：默认 `surface="solid"` 深色实底（辨识度）；`surface="glass"` / `radius="none"` 为扩展。按钮扩展：`radius="none"`。避免组合爆炸。

## 目录结构

```text
ui/<大类>/<widgetName>/
  <widgetName>.js
  index.js
  doc.js          # 图鉴唯一真相源（summary / params / scenarios）
  style.scss      # 如有
```

**文档约定**：组件用法看 `/dev/ui` 图鉴（读 `doc.js` + showcase）。**不要**再给每个组件加 `README.md`；本文件与 `ntq-ui/README.md` 只写包级边界与约定。

## 目录边界

- `views/` **已淘汰**；展示组件在 `ui/` / `ntq-ui/`，业务组合在 `pages/` / `containers/`。
- 新 API（`variant` / `size` / token）以本目录与图鉴为准。
