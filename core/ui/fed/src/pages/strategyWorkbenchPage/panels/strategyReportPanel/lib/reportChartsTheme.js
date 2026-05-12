/**
 * 策略报告区 ECharts 共用样式（深色背景：轴标签、轴线、分割线、柱图、tooltip）。
 */

export const REPORT_CHART_GRID_BASE = { left: 36, right: 10, top: 20, bottom: 28 };

export const REPORT_CHART_GRID_ROI_BUCKET = { left: 30, right: 10, top: 20, bottom: 50 };

/** 与面板主文案层级接近 */
const CHART_TEXT = 'rgba(255, 255, 255, 0.84)';
const CHART_TEXT_MUTED = 'rgba(255, 255, 255, 0.58)';

export const REPORT_CHART_AXIS_LABEL = {
  color: CHART_TEXT_MUTED,
  fontSize: 11,
};

/** K 线等略紧凑场景 */
export const REPORT_CHART_AXIS_LABEL_SM = {
  color: CHART_TEXT_MUTED,
  fontSize: 10,
};

export const REPORT_CHART_AXIS_LINE = {
  lineStyle: { color: 'rgba(255, 255, 255, 0.14)' },
};

export const REPORT_CHART_SPLIT_LINE = {
  lineStyle: { color: 'rgba(255, 255, 255, 0.08)', width: 1 },
};

/** 柱顶数据标签等 */
export const REPORT_CHART_DATA_LABEL = {
  color: CHART_TEXT,
  fontSize: 10,
};

/** 散点 / 标记文字 */
export const REPORT_CHART_MARKER_LABEL = {
  color: CHART_TEXT,
  fontSize: 11,
};

export const REPORT_CHART_TOOLTIP = {
  backgroundColor: 'rgba(14, 14, 22, 0.94)',
  borderColor: 'rgba(255, 255, 255, 0.12)',
  borderWidth: 1,
  textStyle: {
    color: CHART_TEXT,
    fontSize: 12,
  },
};

export const REPORT_CHART_BAR_SHADOW = {
  shadowBlur: 12,
  shadowColor: 'rgba(0, 0, 0, 0.45)',
  shadowOffsetY: 4,
};

/** 正值 / 中性柱（与报告区 accent 一致） */
export const REPORT_CHART_BAR_COLOR_POS = '#22d3ee';

/** 负值柱 */
export const REPORT_CHART_BAR_COLOR_NEG = '#f87171';

const BAR_RADIUS_POS = [4, 4, 0, 0];
const BAR_RADIUS_NEG = [0, 0, 4, 4];

/**
 * 将一维数值数组转为带圆角、颜色、阴影的柱状图 data（负柱红、正柱青）。
 */
export function reportChartSignedBarData(values, radiusPos = BAR_RADIUS_POS, radiusNeg = BAR_RADIUS_NEG) {
  if (!Array.isArray(values)) return [];
  return values.map((cell) => {
    const raw = cell != null && typeof cell === 'object' && Object.prototype.hasOwnProperty.call(cell, 'value')
      ? cell.value
      : cell;
    const n = Number(raw);
    if (!Number.isFinite(n)) {
      return {
        value: 0,
        itemStyle: {
          color: REPORT_CHART_BAR_COLOR_POS,
          borderRadius: radiusPos,
          ...REPORT_CHART_BAR_SHADOW,
        },
      };
    }
    const isNeg = n < 0;
    return {
      value: n,
      itemStyle: {
        color: isNeg ? REPORT_CHART_BAR_COLOR_NEG : REPORT_CHART_BAR_COLOR_POS,
        borderRadius: isNeg ? radiusNeg : radiusPos,
        ...REPORT_CHART_BAR_SHADOW,
      },
    };
  });
}
