/**
 * UI 组件允许的语义 token（与 styles/_tokens.scss 对应）。
 * 组件 props 只收这些名字，禁止传入 16 / '16px' 等原始数值。
 * 对应 CSS 变量见 styles/_tokens.scss（字号/间距为 rem；html 16px，正文 0.875rem）。
 *
 * 命名约定：
 * - variant：形态 / 角色（如 button 的 glass、column 的 thirds）
 * - size：尺寸档位（sm|md|lg|…）
 * - gap / padding：间距 token
 */

export const SPACE_TOKENS = ['none', 'xs', 'sm', 'md', 'lg', 'xl'];
export const FONT_TOKENS = ['xs', 'sm', 'normal', 'md', 'lg', 'xl'];
export const RADIUS_TOKENS = ['none', 'sm', 'md', 'lg', 'pill'];
export const ALIGN_TOKENS = ['stretch', 'start', 'center', 'end'];

/** Block 表面（背景 / 玻璃 / 渐变） */
export const SURFACE_TOKENS = ['none', 'soft', 'panel', 'glass', 'gradient'];

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

/** Icon 尺寸 */
export const ICON_SIZE_TOKENS = ['sm', 'md', 'lg', 'xl', 'xxl'];

/** Icon 色调 */
export const ICON_TONE_TOKENS = ['', 'muted', 'success', 'error', 'warning', 'disabled', 'cyan', 'violet'];

/** LoadingBars / ProgressBar 尺寸 */
export const LOADING_BARS_SIZE_TOKENS = ['md', 'sm'];
export const PROGRESS_SIZE_TOKENS = ['sm', 'md'];

/** Loading 场景形态 */
export const LOADING_VARIANTS = ['page', 'inline', 'inlineRow'];

/** Message 状态（固定图标，不可改） */
export const MESSAGE_STATUSES = ['success', 'error', 'warning', 'info'];

/** Message 颜色模式（可传 / 省略 icon；含状态色 + 紫） */
export const MESSAGE_COLORS = ['green', 'error', 'warning', 'muted', 'cyan', 'violet'];

/** Message 形态：圆角无 bar / 通栏有 bar 无圆角 */
export const MESSAGE_VARIANTS = ['inline', 'banner'];

/** NtqHelpTooltip 触发图标形态 */
export const HELP_TOOLTIP_VARIANTS = ['help', 'info', 'warning'];

/** @deprecated 用 MESSAGE_STATUSES；保留别名以免旧引用报错 */
export const MESSAGE_TONES = MESSAGE_STATUSES;

/** @param {string} value @param {string[]} allowed @param {string} fallback */
export function pickToken(value, allowed, fallback) {
  if (allowed.includes(value)) return value;
  return fallback;
}
