/**
 * 策略报告区 ECharts 共用样式（横轴灰线、分割线、轴标签色），与各图 grid 组合使用。
 */

export const REPORT_CHART_GRID_BASE = { left: 36, right: 10, top: 20, bottom: 28 };

export const REPORT_CHART_GRID_ROI_BUCKET = { left: 30, right: 10, top: 20, bottom: 50 };

export const REPORT_CHART_AXIS_LABEL = {
  color: '#5F6368',
  fontSize: 11,
};

/** K 线等略紧凑场景 */
export const REPORT_CHART_AXIS_LABEL_SM = {
  color: '#5F6368',
  fontSize: 10,
};

export const REPORT_CHART_AXIS_LINE = {
  lineStyle: { color: '#D0D7DE' },
};

export const REPORT_CHART_SPLIT_LINE = {
  lineStyle: { color: '#ECEFF1' },
};
