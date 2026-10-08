/** 报告内金额：千分位 + 固定两位小数 */

const REPORT_MONEY_FMT = { minimumFractionDigits: 2, maximumFractionDigits: 2 };

export function formatReportMoney(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '--';
  return Number(value).toLocaleString(undefined, REPORT_MONEY_FMT);
}
