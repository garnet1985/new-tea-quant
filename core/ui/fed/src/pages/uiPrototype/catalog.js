/**
 * UI 图鉴注册表。
 *
 * status: stub | ready
 * origin: new | migrate | gap
 *
 * 阶段约定：L1 在 src/ui；NTQ 壳在 src/ntq-ui；业务组合在 containers。
 * L2（业务 status→L1 props）另建，不进本图鉴。
 * widget.uiPath 可选：覆盖磁盘路径（默认 `${categoryId}/${widgetId}`）。
 */

export const UI_CATALOG_BASE = '/dev/ui';

/**
 * 旧大类 id → 合并后的大类（书签兼容）。
 * @type {Record<string, string>}
 */
export const UI_CATEGORY_ALIASES = {
  heading: 'text',
  separator: 'text',
  avatar: 'display',
  tag: 'display',
  icon: 'display',
  table: 'data',
  chart: 'data',
  calendar: 'data',
  metric: 'data',
  message: 'feedback',
  progress: 'feedback',
  steps: 'feedback',
};

/** @typedef {object} UiWidgetEntry
 * @property {string} id
 * @property {string} label
 * @property {'new'|'migrate'|'gap'} origin
 * @property {string|null} source
 * @property {'stub'|'ready'} status
 * @property {string} [uiPath]
 */

/** @typedef {object} UiCategoryEntry
 * @property {string} id
 * @property {string} label
 * @property {string} description
 * @property {UiWidgetEntry[]} widgets
 */

/** @type {UiCategoryEntry[]} */
export const UI_CATALOG = [
  {
    id: 'guidelines',
    label: 'NTQ 业务准则',
    description:
      '产品页布局、组合与 Tag 等业务约定；工程硬规则见 FED_STANDARD / ui/README。',
    widgets: [],
  },
  {
    id: 'layout',
    label: '布局',
    description: '分栏与区块：Column / Block / Section / Tabs / SideNav / ListToolbar / CategoryChipStrip。',
    widgets: [
      { id: 'column', label: 'column', origin: 'new', source: null, status: 'ready' },
      { id: 'block', label: 'block', origin: 'new', source: null, status: 'ready' },
      { id: 'section', label: 'section', origin: 'new', source: null, status: 'ready' },
      { id: 'tabs', label: 'tabs', origin: 'new', source: null, status: 'ready' },
      { id: 'sideNav', label: 'sideNav', origin: 'new', source: null, status: 'ready' },
      { id: 'accordion', label: 'accordion', origin: 'new', source: null, status: 'ready', uiPath: 'layout/accordion' },
      { id: 'listToolbar', label: 'listToolbar', origin: 'migrate', source: null, status: 'ready', uiPath: 'layout/listToolbar' },
      { id: 'categoryChipStrip', label: 'categoryChipStrip', origin: 'migrate', source: null, status: 'ready', uiPath: 'layout/categoryChipStrip' },
    ],
  },
  {
    id: 'text',
    label: '文字',
    description: '正文特殊字、标题、分隔线、引用、说明块与代码块；普通正文用 HTML + class。',
    widgets: [
      { id: 'text', label: 'text', origin: 'new', source: null, status: 'ready', uiPath: 'text/text' },
      { id: 'heading', label: 'heading', origin: 'new', source: null, status: 'ready', uiPath: 'text/heading' },
      { id: 'separator', label: 'separator', origin: 'new', source: null, status: 'ready', uiPath: 'text/separator' },
      { id: 'quote', label: 'quote', origin: 'new', source: null, status: 'ready', uiPath: 'text/quote' },
      { id: 'textBlock', label: 'textBlock', origin: 'new', source: null, status: 'ready', uiPath: 'text/textBlock' },
      { id: 'codeBlock', label: 'codeBlock', origin: 'new', source: null, status: 'ready', uiPath: 'text/codeBlock' },
    ],
  },
  {
    id: 'button',
    label: '按钮',
    description: '主操作与彩虹按钮。',
    widgets: [
      { id: 'button', label: 'button', origin: 'new', source: null, status: 'ready', uiPath: 'button/button' },
      {
        id: 'rainbowButton',
        label: 'rainbowButton',
        origin: 'new',
        source: null,
        status: 'ready',
        uiPath: 'ntq-ui/rainbowButton',
      },
    ],
  },
  {
    id: 'display',
    label: '展示',
    description: '图标、头像、标签、键值行等行内展示原语。',
    widgets: [
      { id: 'icon', label: 'icon', origin: 'new', source: null, status: 'ready', uiPath: 'icon/icon' },
      { id: 'avatar', label: 'avatar', origin: 'new', source: null, status: 'ready', uiPath: 'avatar/avatar' },
      { id: 'tag', label: 'tag', origin: 'new', source: null, status: 'ready', uiPath: 'tag/tag' },
      { id: 'definitionList', label: 'definitionList', origin: 'migrate', source: null, status: 'ready', uiPath: 'display/definitionList' },
    ],
  },
  {
    id: 'data',
    label: '数据',
    description: '表格、图表、月历与指标卡；业务 option / 事件标注属 L2。',
    widgets: [
      {
        id: 'dataGrid',
        label: 'dataGrid',
        origin: 'new',
        source: null,
        status: 'ready',
        uiPath: 'table/dataGrid',
      },
      {
        id: 'chartPanel',
        label: 'chartPanel',
        origin: 'migrate',
        source: 'ui/chart/chartPanel',
        status: 'ready',
        uiPath: 'chart/chartPanel',
      },
      {
        id: 'monthCalendar',
        label: 'monthCalendar',
        origin: 'new',
        source: null,
        status: 'ready',
        uiPath: 'calendar/monthCalendar',
      },
      { id: 'metricCard', label: 'metricCard', origin: 'migrate', source: 'ui/metric/metricCard', status: 'ready', uiPath: 'metric/metricCard' },
      { id: 'metricGrid', label: 'metricGrid', origin: 'migrate', source: 'ui/metric/metricGrid', status: 'ready', uiPath: 'metric/metricGrid' },
      { id: 'countBadge', label: 'countBadge', origin: 'migrate', source: 'ui/metric/countBadge', status: 'ready', uiPath: 'metric/countBadge' },
      { id: 'countTab', label: 'countTab', origin: 'migrate', source: 'ui/metric/countTab', status: 'ready', uiPath: 'metric/countTab' },
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
      { id: 'searchField', label: 'searchField', origin: 'migrate', source: 'ui/input/searchField', status: 'ready' },
      { id: 'autocomplete', label: 'autocomplete', origin: 'new', source: null, status: 'ready' },
      { id: 'date', label: 'date', origin: 'new', source: null, status: 'ready' },
      { id: 'dateRange', label: 'dateRange', origin: 'new', source: null, status: 'ready' },
    ],
  },
  {
    id: 'feedback',
    label: '反馈',
    description: '消息、对话框、Toast、帮助提示、加载与进度、步骤条。',
    widgets: [
      { id: 'message', label: 'message', origin: 'new', source: null, status: 'ready', uiPath: 'message/message' },
      { id: 'dialog', label: 'dialog', origin: 'new', source: null, status: 'ready', uiPath: 'message/dialog' },
      { id: 'toast', label: 'toast', origin: 'new', source: null, status: 'ready', uiPath: 'message/toast' },
      {
        id: 'helpTooltip',
        label: 'helpTooltip',
        origin: 'migrate',
        source: 'ui/message/helpTooltip',
        status: 'ready',
        uiPath: 'message/helpTooltip',
      },
      { id: 'loadingBars', label: 'loadingBars', origin: 'new', source: null, status: 'ready', uiPath: 'progress/loadingBars' },
      { id: 'loading', label: 'loading', origin: 'new', source: null, status: 'ready', uiPath: 'progress/loading' },
      { id: 'progressBar', label: 'progressBar', origin: 'new', source: null, status: 'ready', uiPath: 'progress/progressBar' },
      { id: 'progressRing', label: 'progressRing', origin: 'new', source: null, status: 'ready', uiPath: 'progress/progressRing' },
      { id: 'stepper', label: 'stepper', origin: 'new', source: null, status: 'ready', uiPath: 'steps/stepper' },
    ],
  },
  {
    id: 'ntq',
    label: 'NTQ 特有',
    description: '应用壳与报告模板：品牌、导航、面包屑、Banner、页壳、会员条、ReportBlock 等。',
    widgets: [
      {
        id: 'appBrand',
        label: 'brand',
        origin: 'migrate',
        source: 'ntq-ui/appBrand',
        status: 'ready',
        uiPath: 'ntq-ui/appBrand',
      },
      {
        id: 'appVersion',
        label: 'version',
        origin: 'migrate',
        source: 'ntq-ui/appVersion',
        status: 'ready',
        uiPath: 'ntq-ui/appVersion',
      },
      {
        id: 'appNav',
        label: 'nav',
        origin: 'migrate',
        source: 'ntq-ui/appNav',
        status: 'ready',
        uiPath: 'ntq-ui/appNav',
      },
      {
        id: 'appBreadcrumbs',
        label: 'breadcrumb',
        origin: 'migrate',
        source: 'ntq-ui/appBreadcrumbs',
        status: 'ready',
        uiPath: 'ntq-ui/appBreadcrumbs',
      },
      {
        id: 'pageBanner',
        label: 'banner',
        origin: 'migrate',
        source: 'ntq-ui/pageBanner',
        status: 'ready',
        uiPath: 'ntq-ui/pageBanner',
      },
      {
        id: 'pageLayout',
        label: 'pageLayout',
        origin: 'migrate',
        source: 'ntq-ui/pageLayout',
        status: 'ready',
        uiPath: 'ntq-ui/pageLayout',
      },
      {
        id: 'memberStrip',
        label: 'memberStrip',
        origin: 'migrate',
        source: 'containers/memberStrip',
        status: 'ready',
        uiPath: 'ntq-ui/memberStrip',
      },
      {
        id: 'proBadge',
        label: 'proBadge',
        origin: 'new',
        source: null,
        status: 'ready',
        uiPath: 'ntq-ui/proBadge',
      },
      {
        id: 'becomeMemberLink',
        label: 'becomeMemberLink',
        origin: 'migrate',
        source: 'ntq-ui/becomeMemberLink',
        status: 'ready',
        uiPath: 'ntq-ui/becomeMemberLink',
      },
      {
        id: 'reportBlock',
        label: 'reportBlock',
        origin: 'migrate',
        source: 'ntq-ui/reportBlock',
        status: 'ready',
        uiPath: 'ntq-ui/reportBlock',
      },
      {
        id: 'pythonDictEditor',
        label: 'pythonDictEditor',
        origin: 'migrate',
        source: 'ntq-ui/pythonDictEditor',
        status: 'ready',
        uiPath: 'ntq-ui/pythonDictEditor',
      },
      {
        id: 'descriptionText',
        label: 'descriptionText',
        origin: 'migrate',
        source: null,
        status: 'ready',
        uiPath: 'ntq-ui/descriptionText',
      },
      {
        id: 'pageBackground',
        label: 'pageBackground',
        origin: 'migrate',
        source: null,
        status: 'ready',
        uiPath: 'ntq-ui/pageBackground',
      },
      {
        id: 'updateStatusChip',
        label: 'updateStatusChip',
        origin: 'migrate',
        source: null,
        status: 'ready',
        uiPath: 'ntq-ui/updateStatusChip',
      },
    ],
  },
];

export function resolveCategoryId(categoryId) {
  if (!categoryId) return categoryId;
  return UI_CATEGORY_ALIASES[categoryId] || categoryId;
}

export function getCategory(categoryId) {
  const id = resolveCategoryId(categoryId);
  return UI_CATALOG.find((entry) => entry.id === id) || null;
}

export function categoryPath(categoryId) {
  return `${UI_CATALOG_BASE}/${resolveCategoryId(categoryId)}`;
}

/**
 * 组件磁盘相对路径（相对 `src/` 的子树）。
 * 默认落在 `ui/${categoryId}/${widgetId}`；`uiPath` 可写 `icon/icon` 或 `ntq-ui/appNav`。
 */
export function widgetUiPath(categoryId, widget) {
  return widget.uiPath || `${categoryId}/${widget.id}`;
}

export function defaultCategoryPath() {
  // 默认进第一个「有组件」的大类，跳过空的业务准则栏
  const firstWithWidgets = UI_CATALOG.find((entry) => entry.widgets.length > 0);
  return categoryPath((firstWithWidgets || UI_CATALOG[0]).id);
}

export function originLabel(origin) {
  if (origin === 'new') return '新建规范';
  if (origin === 'gap') return '缺口（新建）';
  if (origin === 'migrate') return '迁入';
  return origin;
}

export function statusLabel(status) {
  if (status === 'stub') return '未实现';
  if (status === 'ready') return '已实现';
  return status;
}
