/**
 * 报告区图表横轴 / tooltip：紧凑日期 YYYYMMDD → YYYY-MM-DD。
 * 非 8 位纯数字（如 T0、分位标签）原样返回。
 */
export function formatReportChartDateLabel(value) {
  if (value == null || value === '') return '';
  const s = String(value).trim();
  if (/^\d{8}$/.test(s)) {
    return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
  }
  return s;
}
