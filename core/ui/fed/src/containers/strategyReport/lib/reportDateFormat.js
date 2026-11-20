import { formatCalendarDate } from 'service/format/formatDateTime';

/**
 * 报告区图表横轴 / tooltip：紧凑日期 → ``YYYY-MM-DD``。
 * 非日期串（如 T0、分位标签）原样返回。
 */
export function formatReportChartDateLabel(value) {
  return formatCalendarDate(value);
}
