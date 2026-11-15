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
 * 阶段约定：先完成 src/ui 标准；views/ 只读，不在此阶段改 views 做迁移。
 *
 * layout：布局原语；text：正文/特殊字；heading / separator：独立大类。
 * widget.uiPath 可选：覆盖磁盘路径（默认 `${categoryId}/${widgetId}`）。
 * pageLayout、Banner 等继续留在 views/，迁移另做。
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
    description: '分栏与区块：Column（variant/gap/divider）+ Block（surface/radius）+ Section。',
    widgets: [
      { id: 'column', label: 'column', origin: 'new', source: null, status: 'ready' },
      { id: 'block', label: 'block', origin: 'new', source: null, status: 'ready' },
      { id: 'section', label: 'section', origin: 'new', source: null, status: 'ready' },
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
    id: 'input',
    label: '输入',
    description: '搜索、文本与结构化取值输入。',
    widgets: [
      { id: 'searchField', label: 'searchField', origin: 'migrate', source: 'views/searchField', status: 'stub' },
      { id: 'pythonDictInputPanel', label: 'pythonDictInputPanel', origin: 'migrate', source: 'views/pythonDictInputPanel', status: 'stub' },
      { id: 'textField', label: 'textField', origin: 'gap', source: null, status: 'stub' },
    ],
  },
  {
    id: 'message',
    label: '消息',
    description: '提示条、内联帮助与状态文案。',
    widgets: [
      { id: 'message', label: 'message', origin: 'migrate', source: 'views/message', status: 'stub' },
      { id: 'ntqHelpTooltip', label: 'ntqHelpTooltip', origin: 'migrate', source: 'views/ntqHelpTooltip', status: 'stub' },
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
    description: '加载与进度条原语（pageLoadingState 等组合壳暂留 views）。',
    widgets: [
      { id: 'loadingBars', label: 'loadingBars', origin: 'new', source: null, status: 'ready' },
      { id: 'loading', label: 'loading', origin: 'new', source: null, status: 'ready' },
      { id: 'progressBar', label: 'progressBar', origin: 'new', source: null, status: 'ready' },
    ],
  },
  {
    id: 'steps',
    label: '步骤',
    description: '多步流程与步骤条。',
    widgets: [
      {
        id: 'stepper',
        label: 'stepper',
        origin: 'gap',
        source: 'containers/strategyDesign/stepper',
        status: 'stub',
      },
    ],
  },
  {
    id: 'metric',
    label: '指标',
    description: '指标卡、计数与状态芯片。',
    widgets: [
      { id: 'metricCard', label: 'metricCard', origin: 'migrate', source: 'views/metricCard', status: 'stub' },
      { id: 'countBadge', label: 'countBadge', origin: 'migrate', source: 'views/countBadge', status: 'stub' },
      { id: 'countTab', label: 'countTab', origin: 'migrate', source: 'views/countTab', status: 'stub' },
      { id: 'freshnessStatusChip', label: 'freshnessStatusChip', origin: 'migrate', source: 'views/freshnessStatusChip', status: 'stub' },
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
