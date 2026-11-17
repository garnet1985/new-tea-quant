/**
 * UI 图鉴注册表。
 *
 * status:
 * - stub: src/ui 下仅有占位，尚未实现
 * - ready: 已迁入/实现，图鉴可展示样例与文档
 *
 * origin:
 * - new: src/ui 新建规范原语（不替换 views）
 * - migrate: 计划从现有 views/（或 container）迁入/重写
 * - gap: 业务需要，但尚无独立 view
 *
 * 阶段约定：先完成 src/ui（L1 原语）；views/ 只读，不在此阶段改 views 做迁移。
 * L2（业务 status→L1 props 映射）另建，不进本图鉴。
 *
 * layout：布局原语；text：正文/特殊字；heading / separator：独立大类。
 * tag：状态/分类小块；table：DataGrid；chart：ChartPanel 壳（非 K 线业务）。
 * widget.uiPath 可选：覆盖磁盘路径（默认 `${categoryId}/${widgetId}`）。
 * ntq：应用壳 / 特有复合组件（nav、banner、pythonDictEditor…）；views/ 只读待迁。
 */

export const UI_CATALOG_BASE = '/dev/ui';

/**
 * @typedef {object} UiWidgetEntry
 * @property {string} id
 * @property {string} label
 * @property {'new'|'migrate'|'gap'} origin
 * @property {string|null} source
 * @property {'stub'|'ready'} status
 * @property {string} [uiPath] 相对 src/ui 的目录，缺省为 `${categoryId}/${id}`
 */

/**
 * @typedef {object} UiCategoryEntry
 * @property {string} id
 * @property {string} label
 * @property {string} description
 * @property {UiWidgetEntry[]} widgets
 */

/** @type {UiCategoryEntry[]} */
export const UI_CATALOG = [
  {
    id: 'layout',
    label: '布局',
    description: '分栏与区块：Column / Block / Section / Tabs / SideNav（左侧目录壳）。',
    widgets: [
      { id: 'column', label: 'column', origin: 'new', source: null, status: 'ready' },
      { id: 'block', label: 'block', origin: 'new', source: null, status: 'ready' },
      { id: 'section', label: 'section', origin: 'new', source: null, status: 'ready' },
      { id: 'tabs', label: 'tabs', origin: 'new', source: null, status: 'ready' },
      { id: 'sideNav', label: 'sideNav', origin: 'new', source: null, status: 'ready' },
    ],
  },
  {
    id: 'text',
    label: '文字',
    description: '行内特殊字、引用、说明块、多行代码；普通正文 / 链接用 HTML + class。',
    widgets: [
      { id: 'text', label: 'text', origin: 'new', source: null, status: 'ready', uiPath: 'text/text' },
      { id: 'quote', label: 'quote', origin: 'new', source: null, status: 'ready', uiPath: 'text/quote' },
      { id: 'textBlock', label: 'textBlock', origin: 'new', source: null, status: 'ready', uiPath: 'text/textBlock' },
      { id: 'codeBlock', label: 'codeBlock', origin: 'new', source: null, status: 'ready', uiPath: 'text/codeBlock' },
    ],
  },
  {
    id: 'heading',
    label: '标题',
    description: '页面与区块标题：level / variant(bar) / subtitle / gap。',
    widgets: [
      { id: 'heading', label: 'heading', origin: 'new', source: null, status: 'ready', uiPath: 'text/heading' },
    ],
  },
  {
    id: 'separator',
    label: '分隔线',
    description: '小节分隔：左侧文案 + 右侧横线。',
    widgets: [
      { id: 'separator', label: 'separator', origin: 'new', source: null, status: 'ready', uiPath: 'text/separator' },
    ],
  },
  {
    id: 'button',
    label: '按钮',
    description: '主操作与各类按钮形态。',
    widgets: [
      { id: 'ntqButton', label: 'ntqButton', origin: 'new', source: null, status: 'ready' },
      { id: 'rainbowButton', label: 'rainbowButton', origin: 'new', source: null, status: 'ready' },
    ],
  },
  {
    id: 'avatar',
    label: '头像',
    description: '圆形头像（图 / 首字母）；会员条组合属 L2。',
    widgets: [
      { id: 'avatar', label: 'avatar', origin: 'new', source: null, status: 'ready', uiPath: 'avatar/avatar' },
    ],
  },
  {
    id: 'tag',
    label: '标签',
    description: '状态 / 分类小块；业务 status→样式映射属 L2。',
    widgets: [
      { id: 'tag', label: 'tag', origin: 'new', source: null, status: 'ready', uiPath: 'tag/tag' },
    ],
  },
  {
    id: 'calendar',
    label: '日历',
    description: '月历网格壳；交易事件标注属 L2（renderDay）。',
    widgets: [
      {
        id: 'monthCalendar',
        label: 'monthCalendar',
        origin: 'new',
        source: null,
        status: 'ready',
        uiPath: 'calendar/monthCalendar',
      },
    ],
  },
  {
    id: 'table',
    label: '表格',
    description: '数据表：DataGrid 封装（中文、Loading、密度）。',
    widgets: [
      {
        id: 'dataGrid',
        label: 'dataGrid',
        origin: 'new',
        source: null,
        status: 'ready',
        uiPath: 'table/dataGrid',
      },
    ],
  },
  {
    id: 'chart',
    label: '图表',
    description: '图表壳与中性主题；K 线 / 业务 option 属 L2，不进本组件。',
    widgets: [
      {
        id: 'chartPanel',
        label: 'chartPanel',
        origin: 'migrate',
        source: 'views/chartPanel',
        status: 'ready',
        uiPath: 'chart/chartPanel',
      },
    ],
  },
  {
    id: 'input',
    label: '输入',
    description: '表单字段与控件；number 暂用 TextField type="number"。',
    widgets: [
      { id: 'field', label: 'field', origin: 'new', source: null, status: 'ready' },
      { id: 'textField', label: 'textField', origin: 'new', source: null, status: 'ready' },
      { id: 'textArea', label: 'textArea', origin: 'new', source: null, status: 'ready' },
      { id: 'checkbox', label: 'checkbox', origin: 'new', source: null, status: 'ready' },
      { id: 'radio', label: 'radio', origin: 'new', source: null, status: 'ready' },
      { id: 'switch', label: 'switch', origin: 'new', source: null, status: 'ready' },
      { id: 'select', label: 'select', origin: 'new', source: null, status: 'ready' },
      { id: 'searchSelect', label: 'searchSelect', origin: 'new', source: null, status: 'ready' },
      { id: 'searchField', label: 'searchField', origin: 'migrate', source: 'views/searchField', status: 'ready' },
      { id: 'autocomplete', label: 'autocomplete', origin: 'new', source: null, status: 'ready' },
      { id: 'date', label: 'date', origin: 'new', source: null, status: 'ready' },
      { id: 'dateRange', label: 'dateRange', origin: 'new', source: null, status: 'ready' },
    ],
  },
  {
    id: 'ntq',
    label: 'NTQ 特有',
    description: '应用壳：品牌、导航、面包屑、页头 Banner、Python dict 编辑器等。',
    widgets: [
      {
        id: 'appBrand',
        label: 'brand',
        origin: 'migrate',
        source: 'views/appBrand',
        status: 'ready',
        uiPath: 'ntq/appBrand',
      },
      {
        id: 'appNav',
        label: 'nav',
        origin: 'migrate',
        source: 'views/appNav',
        status: 'ready',
        uiPath: 'ntq/appNav',
      },
      {
        id: 'appBreadcrumbs',
        label: 'breadcrumb',
        origin: 'migrate',
        source: 'views/appBreadcrumbs',
        status: 'ready',
        uiPath: 'ntq/appBreadcrumbs',
      },
      {
        id: 'pageBanner',
        label: 'banner',
        origin: 'migrate',
        source: 'views/pageBanner',
        status: 'ready',
        uiPath: 'ntq/pageBanner',
      },
      {
        id: 'pythonDictEditor',
        label: 'pythonDictEditor',
        origin: 'migrate',
        source: 'views/pythonDictInputPanel',
        status: 'ready',
        uiPath: 'ntq/pythonDictEditor',
      },
    ],
  },
  {
    id: 'message',
    label: '消息',
    description: '消息条、Toast 与说明 Tooltip。',
    widgets: [
      { id: 'message', label: 'message', origin: 'new', source: null, status: 'ready' },
      { id: 'toast', label: 'toast', origin: 'new', source: null, status: 'ready' },
      {
        id: 'ntqHelpTooltip',
        label: 'ntqHelpTooltip',
        origin: 'migrate',
        source: 'views/ntqHelpTooltip',
        status: 'ready',
      },
    ],
  },
  {
    id: 'icon',
    label: '图标',
    description: 'NTQ 图标原语（size/tone 用 token）。',
    widgets: [
      { id: 'ntqIcon', label: 'ntqIcon', origin: 'new', source: null, status: 'ready' },
    ],
  },
  {
    id: 'progress',
    label: '进度',
    description: '加载动画、线性进度（回测条）与圆环进度（step 环）。',
    widgets: [
      { id: 'loadingBars', label: 'loadingBars', origin: 'new', source: null, status: 'ready' },
      { id: 'loading', label: 'loading', origin: 'new', source: null, status: 'ready' },
      { id: 'progressBar', label: 'progressBar', origin: 'new', source: null, status: 'ready' },
      { id: 'progressRing', label: 'progressRing', origin: 'new', source: null, status: 'ready' },
    ],
  },
  {
    id: 'steps',
    label: '步骤',
    description: '多步流程步骤条（回测视觉；可点击跳转，进度环可选）。',
    widgets: [
      {
        id: 'stepper',
        label: 'stepper',
        origin: 'new',
        source: null,
        status: 'ready',
      },
    ],
  },
  {
    id: 'metric',
    label: '指标',
    description: '指标卡 / 网格、计数角标与筛选 Tab。业务 status→Tag 映射属第二层，不进本目录。',
    widgets: [
      { id: 'metricCard', label: 'metricCard', origin: 'migrate', source: 'views/metricCard', status: 'ready' },
      {
        id: 'metricGrid',
        label: 'metricGrid',
        origin: 'migrate',
        source: 'views/metricGrid',
        status: 'ready',
      },
      { id: 'countBadge', label: 'countBadge', origin: 'migrate', source: 'views/countBadge', status: 'ready' },
      { id: 'countTab', label: 'countTab', origin: 'migrate', source: 'views/countTab', status: 'ready' },
    ],
  },
];

export function getCategory(categoryId) {
  return UI_CATALOG.find((entry) => entry.id === categoryId) || null;
}

export function categoryPath(categoryId) {
  return `${UI_CATALOG_BASE}/${categoryId}`;
}

/** 组件在 src/ui 下的相对目录 */
export function widgetUiPath(categoryId, widget) {
  return widget.uiPath || `${categoryId}/${widget.id}`;
}

export function defaultCategoryPath() {
  return categoryPath(UI_CATALOG[0].id);
}

export function originLabel(origin) {
  if (origin === 'new') return '新建规范';
  if (origin === 'gap') return '缺口（新建）';
  if (origin === 'migrate') return '待迁入';
  return origin;
}

export function statusLabel(status) {
  if (status === 'stub') return '未实现';
  if (status === 'ready') return '已实现';
  return status;
}
