import './strategyReportPanel.scss';

export { default as StrategyReportPanel } from './strategyReportPanel';
export { default as CapitalAllocationReport } from './reports/capitalAllocationReport';
export {
  REPORT_CHART_AXIS_LABEL,
  REPORT_CHART_AXIS_LINE,
  REPORT_CHART_SPLIT_LINE,
  REPORT_CHART_TOOLTIP,
} from './lib/reportChartsTheme';
export {
  COMPARE_EMPTY_OTHER_VERSION_ZH,
  COMPARE_NO_REPORT_FOR_SNAPSHOT_ZH,
} from './constants/strategyReportConstants';
export { slotFromResultReport } from './lib/strategyReportSlotResolve';
export { normalizeCapitalMetricsFromSummary } from './reportMetrics/strategyReportMetricsNormalize';
export { clearStockKlineMemoryCache } from './lib/stockKlineMemoryCache';
