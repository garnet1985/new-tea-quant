# `src/ui` — 设计系统原语

本目录是后续产品页**唯一**应复用的 UI widget 来源。

## 两层分工

| 层 | 放什么 | 例子 |
|----|--------|------|
| **L1 · `src/ui`（本目录）** | 元素与布局原语：长相、token、通用交互 | `Tag`、`DataGrid`、`ChartPanel`、`CountTab` |
| **L2 · 业务 mapping（尚未建目录）** | 业务枚举 / 状态 → L1 组件的 props；领域 option 构建 | freshness→Tag；`buildMarketChartOption`→ChartPanel |

L1 不收业务 status key；views 里的 `freshnessStatusChip` 等属 L2，稳定后再迁，不进图鉴。

## 约定

- 只放 **L1 设计原语**（布局、按钮、输入、标题、消息、进度、步骤、图标、指标…）。
- **layout**：`column` / `block` / `section` / `tabs` / `sideNav`（不含 Banner、面包屑）。
  - `Column`：版式 + `gap` + `divider`（竖线分栏）。
  - `Block`：`surface`（soft/panel/glass/gradient）+ `radius`（含 pill）+ `bordered`。
  - `Section`：纵向堆叠 + `gap`；表面仍用内嵌 Block。
  - `Tabs`：`variant="top"` 上方切换；`variant="side"` 左右分栏（同页切 panel）。
  - `SideNav`：左侧目录壳（`line` / `rail`）；栏宽用 Column sidebar，右栏自管（Outlet 等）。
- **text**：
  - **文字**（图鉴 `/dev/ui/text`）：`text` / `quote` / `textBlock` / `codeBlock`。
  - **标题**（图鉴 `/dev/ui/heading`）：`heading`（`level` + `variant`/`subtitle`/`gap`）。
  - **分隔线**（图鉴 `/dev/ui/separator`）：`separator`。
  - 磁盘仍在 `ui/text/*`；图鉴大类分开便于浏览。
  - 普通正文 / 链接用 HTML + class（`.ntq-muted` / `.ntq-link` 等），不是组件。
- **icon** / **button**：见各目录 README。`NtqButton` 支持前后图标、纯图标、tooltip、以及 `href`/`component` 做成按钮样式超链接（行内文字链仍用 `.ntq-link`）。
- **tag**：通用标签 / 状态小块 — `status` 或 `color`；`variant` soft（半透明）/ outline / solid（同色实心）；`size` sm/md；可选 `icon` / `onDelete`。业务 Freshness 等仍在 **metric**。
- **table**：`dataGrid`（MUI DataGrid 封装；默认中文、Loading 覆盖层、`density` sm/md）。列定义仍由业务传入。列表 Search / CountTab 过滤由**上层**组合（`SearchField` + `CountTab` → `displayRows` → `DataGrid`），不塞进表格。
- **chart**：`chartPanel`（标题 / tip / ECharts 壳）+ `chartTheme`（中性暗色轴/tooltip）。K 线等业务 option 属 L2（`marketChart`），不进本组件。
- **metric**：`metricCard` + `metricGrid`；`countTab` / `countBadge`。
- **progress**：`loadingBars` / `loading`；`progressBar`（回测线性条，可选 label + showPercent）；`progressRing`（step 圆环，可选 label / showPercent / 环心 children）。
- **steps**：`stepper`（回测步骤条；`activeId` + `status`；可 `href` / RouterLink / `onItemClick`；`showProgress` 可关进度环）。
- **input**：通用表单原语 — `field`；`textField` / `textArea`；`checkbox`；`radio`；`switch`；`select`；`searchSelect`；`searchField`；`autocomplete`；`date` / `dateRange`。数值暂用 `TextField type="number"`。
- **avatar**：圆形头像（图 / 首字母）；`size` sm/md/lg。
- **calendar**：`monthCalendar` 月历壳（`density` sm/md + `renderDay`）；交易事件属 L2。
- **ntq**：应用壳 — `appBrand`；`appNav`；`appBreadcrumbs`；`pageBanner`；`pythonDictEditor`。见 `ui/ntq/README.md`。
- **message**：
  - `message`：`variant="inline"` 圆角+border+底色无 bar；`banner` 有 bar 无圆角。`status`（图标固定）或 `color`（icon 可传/省略）。
  - `toast`：右下角短暂弹出（`ToastHost` + `showToast({ status, content })`）；内部复用 Message。
  - `ntqHelpTooltip`：说明气泡（对齐 app；`variant` help/info/warning；图标固定 md）。
- 隐形图鉴 `/dev/ui` **只能**展示本目录下的组件。

## 命名：统一用 `variant` + `size`

| 参数 | 用途 | 例子 |
|------|------|------|
| **`variant`** | 形态 / 角色 | `Column variant="thirds"`、`Button variant="primary"`、`Loading variant="page"`、`Text variant="code"` |
| **`size`** | 尺寸档位 | `Icon size="md"`、`ProgressBar size="sm"`、`LoadingBars size="md"` |
| **`gap` / `padding`** | 间距 token | `none`…`xxs`…`xl` → `--ntq-space-*` |

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

| 维度 | 合法值 | 全局变量 |
|------|--------|----------|
| 间距 | `none` `xxs` `xs` `sm` `md` `lg` `xl` | `--ntq-space-*`（rem；`xxs`=2px，`md`=1rem） |
| 字号 | `xs` `sm` `normal` `md` `lg` `xl` | `--ntq-font-*`（rem；`normal` = 0.875rem = 14px） |
| 图标 | `sm` `md` `lg` `xl` `xxl` | `--ntq-icon-*`（`xxl` = 3rem） |
| 圆角 | `none` `sm` `md` `lg` `pill` | `--ntq-radius-*` |
| 表面 | `none` `soft` `panel` `glass` `gradient` | `--ntq-surface-*`（Block） |
| 分隔 | `none` `line` | `--ntq-divider-color`（Column） |

```js
// ✅
<Column variant="thirds" gap="md" />
<Heading level="h1">页面标题</Heading>
<Heading level="h2" variant="bar" tone="cyan" subtitle="说明">区块</Heading>
<p className="ntq-muted">次要说明</p>
<a className="ntq-link" href="/dev/ui">文字图鉴</a>
<Quote>优先用语义 token。</Quote>
<Text variant="code">/dev/ui</Text>
<NtqIcon name="settings" size="md" />
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

改数值：覆盖 `styles/_tokens.scss`，不要在调用处写死像素。

表面风格约定：科技玻璃为默认（如 `CodeBlock variant="glass"`），最多再留一个轻变种（如 `soft`）；后续 input 等同理，避免 surface/radius/padding 组合爆炸。

## 目录结构

```text
ui/<大类>/<widgetName>/
  <widgetName>.js
  index.js
  README.md
  doc.js
```

## 与 views 的关系

- **现阶段 `views/` 只读**：先把 `src/ui` 标准做完，再单独开迁移，避免被旧实现带偏。
- 可参考 views 的视觉与用法，但新 API（`variant` / `size` / token）以 `ui/` 为准。
- 业务页暂时继续用 views；标准稳定后再改 import。
