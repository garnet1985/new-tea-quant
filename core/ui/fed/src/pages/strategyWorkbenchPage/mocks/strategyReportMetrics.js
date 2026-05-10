/**
 * 策略报告 metrics 入口：从 ``reportMetrics`` 重导出纯转换；
 * ``buildCapitalMetrics`` 仅使用 ``capital_allocation`` 槽位或 ``result.capital`` 摘要；无数据时返回 ``null``（不设演示回落）。
 */
import {
  buildCapitalMetricsFromBase,
  normalizeCapitalMetricsFromSummary,
} from '../reportMetrics/strategyReportMetricsNormalize';

export * from '../reportMetrics/strategyReportMetricsNormalize';

export function buildCapitalMetrics(executionState) {
  const fromSlot = normalizeCapitalMetricsFromSummary(executionState?.result?.capital_allocation);
  if (fromSlot) return fromSlot;

  const summary = executionState?.result?.capital;
  const parsed = summary
    ? {
      ...summary,
      totalReturnPct: summary.totalReturnPct !== undefined
        ? Number(summary.totalReturnPct)
        : Number((Number(summary.totalReturn || 0) * 100).toFixed(2)),
      maxDrawdownPct: summary.maxDrawdownPct !== undefined
        ? Number(summary.maxDrawdownPct)
        : Number((Number(summary.maxDrawdown || 0) * 100).toFixed(2)),
      winRatePct: summary.winRatePct !== undefined
        ? Number(summary.winRatePct)
        : Number((Number(summary.winRate || 0) * 100).toFixed(2)),
    }
    : null;
  const hasRealCapitalMetrics = Boolean(
    parsed && Object.keys(parsed).length > 0,
  );
  if (!hasRealCapitalMetrics) return null;
  return buildCapitalMetricsFromBase(parsed);
}
