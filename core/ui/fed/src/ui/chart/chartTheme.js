/**
 * L1 图表中性深色主题（ECharts option 片段）。
 * 业务 K 线 / 报告专用色（阴阳烛等）放 L2，不进这里。
 */

export const CHART_TEXT = 'rgba(255, 255, 255, 0.84)';
export const CHART_TEXT_MUTED = 'rgba(255, 255, 255, 0.58)';

export const CHART_AXIS_LABEL = {
  color: CHART_TEXT_MUTED,
  fontSize: 11,
};

export const CHART_AXIS_LABEL_SM = {
  color: CHART_TEXT_MUTED,
  fontSize: 10,
};

export const CHART_AXIS_LINE = {
  lineStyle: { color: 'rgba(255, 255, 255, 0.14)' },
};

export const CHART_SPLIT_LINE = {
  lineStyle: { color: 'rgba(255, 255, 255, 0.08)', width: 1 },
};

export const CHART_TOOLTIP = {
  backgroundColor: 'rgba(14, 14, 22, 0.94)',
  borderColor: 'rgba(255, 255, 255, 0.12)',
  borderWidth: 1,
  textStyle: {
    color: CHART_TEXT,
    fontSize: 12,
  },
};

export const CHART_GRID_BASE = {
  left: 36,
  right: 10,
  top: 20,
  bottom: 28,
};

/** 正值 / 强调柱（对齐 --ntq-cyan） */
export const CHART_BAR_POS = '#22d3ee';
/** 负值柱 */
export const CHART_BAR_NEG = '#f87171';

/**
 * 给 option 补上暗色轴 / tooltip（不覆盖已有字段）。
 * @param {object} option
 */
export function withChartTheme(option = {}) {
  return {
    ...option,
    textStyle: {
      color: CHART_TEXT,
      ...(option.textStyle || {}),
    },
    tooltip: {
      ...CHART_TOOLTIP,
      ...(option.tooltip || {}),
      textStyle: {
        ...CHART_TOOLTIP.textStyle,
        ...(option.tooltip?.textStyle || {}),
      },
    },
  };
}
