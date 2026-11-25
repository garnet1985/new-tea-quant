/**
 * UI 组件允许的语义 token（props 名 ↔ CSS 变量）。
 * 组件 props 只收这些名字，禁止传入 16 / '16px' 等原始数值。
 *
 * CSS 两套：
 * - 通用原语：styles/_ui-tokens.scss → `--ui-*`
 * - NTQ 产品：styles/_ntq-tokens.scss → `--ntq-*`
 * 入口 styles/_tokens.scss 另提供旧名 `--ntq-space-*` 等 → `--ui-*` 的过渡别名。
 * 设计尺度只用 CSS 变量；禁止 Sass `$` 设计变量。
 *
 * 命名约定：
 * - variant：形态 / 角色（如 button 的 glass、column 的 thirds）
 * - size：尺寸档位（sm|md|lg|…）
 * - gap / padding：间距 token
 */

export const SPACE_TOKENS = ['none', 'xxs', 'xs', 'sm', 'md', 'lg', 'xl'];
export const FONT_TOKENS = ['xs', 'sm', 'normal', 'md', 'lg', 'xl'];
export const RADIUS_TOKENS = ['none', 'sm', 'md', 'lg', 'pill'];
export const ALIGN_TOKENS = ['stretch', 'start', 'center', 'end'];

/**
 * Wrapper / Block 表面（三档 + 旧名兼容）。
 * - glass：透光玻璃（浅白抬亮，无 blur）
 * - frost：毛玻璃（抬亮 + blur）
 * - frost-strong：渐变毛玻璃（ink 遮罩 + blur）
 * 旧名：soft→glass，panel→frost，gradient→frost-strong
 */
export const SURFACE_TOKENS = [
  'none',
  'glass',
  'frost',
  'frost-strong',
  'soft',
  'panel',
  'gradient',
];

const SURFACE_ALIASES = {
  soft: 'glass',
  panel: 'frost',
  gradient: 'frost-strong',
};

/** 把 surface prop 归一到三档（或 none）。 */
export function resolveSurfaceToken(surface) {
  const raw = pickToken(surface, SURFACE_TOKENS, 'none');
  if (raw === 'none') return 'none';
  return SURFACE_ALIASES[raw] || raw;
}

/** 输入控件表面：solid=默认深色实底；glass=半透明玻璃（与 wrapper 三档无关） */
export const INPUT_SURFACE_TOKENS = ['solid', 'glass'];

/** Column 列间分隔 */
export const DIVIDER_TOKENS = ['none', 'line'];

/** Text 特殊字形 */
export const TEXT_VARIANTS = ['code', 'rainbow', 'accent'];

/** Heading 标签层级（字号随 level 固定缩小，不可单独改 size） */
export const HEADING_LEVELS = ['h1', 'h2', 'h3', 'h4', 'h5'];

/** Heading 形态：默认无竖条；bar = 官网式左侧色条 */
export const HEADING_VARIANTS = ['plain', 'bar'];

/** Heading / TextBlock 竖条色 */
export const HEADING_BAR_TOKENS = ['cyan', 'violet', 'green', 'warning', 'error', 'muted'];

/** Heading 上下间距：none=收紧；md=上1.5/下1；lg=上2/下1（单位 rem，见 --ntq-stack） */
export const HEADING_GAP_TOKENS = ['none', 'md', 'lg'];

/** Heading 副标题位置 */
export const HEADING_SUBTITLE_PLACEMENTS = ['below', 'inline'];

/** Column 分栏形态 */
export const COLUMN_VARIANTS = [
  'halves',
  'thirds',
  'quarters',
  'asideMain',
  'mainAside',
  'sidebar',
  'sidebarEnd',
];

/** Tabs 布局形态：上方横排 / 左右分栏 */
export const TABS_VARIANTS = ['top', 'side'];

/** SideNav 选中条形态：底边 / 左侧轨 */
export const SIDE_NAV_VARIANTS = ['line', 'rail'];

/** Icon 尺寸 */
export const ICON_SIZE_TOKENS = ['sm', 'md', 'lg', 'xl', 'xxl'];

/** Icon 色调 */
export const ICON_TONE_TOKENS = ['', 'muted', 'success', 'error', 'warning', 'disabled', 'cyan', 'violet'];

/** LoadingBars / ProgressBar / ProgressRing 尺寸 */
export const LOADING_BARS_SIZE_TOKENS = ['md', 'sm'];
export const PROGRESS_SIZE_TOKENS = ['sm', 'md'];
export const PROGRESS_RING_SIZE_TOKENS = ['sm', 'md'];

/** Loading 场景形态 */
export const LOADING_VARIANTS = ['page', 'inline', 'inlineRow'];

/** Message 状态（固定图标，不可改） */
export const MESSAGE_STATUSES = ['success', 'error', 'warning', 'info'];

/** Message 颜色模式（可传 / 省略 icon；含状态色 + 紫） */
export const MESSAGE_COLORS = ['green', 'error', 'warning', 'muted', 'cyan', 'violet'];

/** Message 形态：圆角无 bar / 通栏有 bar 无圆角 */
export const MESSAGE_VARIANTS = ['inline', 'banner'];

/** HelpTooltip 触发图标形态 */
export const HELP_TOOLTIP_VARIANTS = ['help', 'info', 'warning'];

/** Stepper 步骤执行状态（与 activeId 正交） */
export const STEPPER_ITEM_STATUSES = ['idle', 'done', 'failed', 'running', 'pending'];

/** Field 标签位置 */
export const FIELD_LABEL_PLACEMENTS = ['above', 'inline', 'none'];

/** RadioGroup 排列方向 */
export const RADIO_DIRECTIONS = ['column', 'row'];

/** RadioGroup 形态：圆点 / 大按钮卡片（扫描页） */
export const RADIO_VARIANTS = ['plain', 'button'];

/** Tag 语义状态（与 Message status 对齐；neutral = 中性灰） */
export const TAG_STATUSES = ['success', 'error', 'warning', 'info', 'neutral'];

/** Tag 颜色模式（含紫；与 Message color 对齐） */
export const TAG_COLORS = ['green', 'error', 'warning', 'muted', 'cyan', 'violet'];

/** Tag 形态：浅底 / 描边 / 实心 */
export const TAG_VARIANTS = ['soft', 'outline', 'solid'];

/** Tag 尺寸 */
export const TAG_SIZE_TOKENS = ['sm', 'md'];

/** DataGrid 行高密度 */
export const DATA_GRID_DENSITY_TOKENS = ['sm', 'md'];

/** DataGrid 单元格布局：单行居中 / 多行换行顶齐 */
export const DATA_GRID_CELL_LAYOUT_TOKENS = ['center', 'wrap'];

/** MetricGrid 列数（≥900px；窄屏默认 1 列，denseXs 时 2 列） */
export const METRIC_GRID_COLUMN_TOKENS = [2, 3, 4];

/** Avatar 尺寸 */
export const AVATAR_SIZE_TOKENS = ['sm', 'md', 'lg'];

/** MonthCalendar 格子密度：紧凑选日 / 可塞事件 */
export const MONTH_CALENDAR_DENSITY_TOKENS = ['sm', 'md'];

/** @param {string} value @param {string[]} allowed @param {string} fallback */
export function pickToken(value, allowed, fallback) {
  if (allowed.includes(value)) return value;
  return fallback;
}
