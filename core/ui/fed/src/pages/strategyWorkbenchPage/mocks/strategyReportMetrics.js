/**
 * 策略报告 metrics 入口。
 * 资金报告仅认 ``result.capital_allocation``（V2-07 完整槽位，snake_case）；无数据返回 ``null``。
 */
import { normalizeCapitalMetricsFromSummary } from '../reportMetrics/strategyReportMetricsNormalize';

export * from '../reportMetrics/strategyReportMetricsNormalize';

export function buildCapitalMetrics(executionState) {
  return normalizeCapitalMetricsFromSummary(executionState?.result?.capital_allocation);
}
