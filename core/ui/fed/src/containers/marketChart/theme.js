/**
 * 市场图中性深色主题 token（无报告业务语义）。
 */

const CHART_TEXT = 'rgba(255, 255, 255, 0.84)';
const CHART_TEXT_MUTED = 'rgba(255, 255, 255, 0.58)';

export const MARKET_CHART_AXIS_LABEL_SM = {
  color: CHART_TEXT_MUTED,
  fontSize: 10,
};

export const MARKET_CHART_AXIS_LINE = {
  lineStyle: { color: 'rgba(255, 255, 255, 0.14)' },
};

export const MARKET_CHART_SPLIT_LINE = {
  lineStyle: { color: 'rgba(255, 255, 255, 0.08)', width: 1 },
};

export const MARKET_CHART_TOOLTIP = {
  backgroundColor: 'rgba(14, 14, 22, 0.94)',
  borderColor: 'rgba(255, 255, 255, 0.12)',
  borderWidth: 1,
  textStyle: {
    color: CHART_TEXT,
    fontSize: 12,
  },
};

/** A 股习惯：阳红阴绿 */
export const MARKET_CANDLE_UP_COLOR = '#FF4D67';
export const MARKET_CANDLE_DOWN_COLOR = '#00D9A5';

export const MARKET_CHART_BAR_POS = '#22d3ee';
export const MARKET_CHART_BAR_NEG = '#f87171';

export const MARKET_CHART_PANEL_DIVIDER = 'rgba(255, 255, 255, 0.42)';
/** 副图略提亮，和主图底区分开，边框才看得清 */
export const MARKET_CHART_SUB_PANE_BG = 'rgba(255, 255, 255, 0.07)';

/** 与 ECharts grid 左右对齐，信息卡 / 图例共用 */
export const MARKET_CHART_GRID_LEFT = 52;
export const MARKET_CHART_GRID_RIGHT = 16;

export const MARKET_CHART_LEGEND_TEXT = {
  color: 'rgba(255,255,255,0.72)',
  fontSize: 11,
};
