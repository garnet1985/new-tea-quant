/**
 * 市场图横轴 / tooltip：YYYYMMDD → YYYY-MM-DD；其它标签原样。
 */
export function formatMarketChartDateLabel(value) {
  if (value == null || value === '') return '';
  const s = String(value).trim();
  if (/^\d{8}$/.test(s)) {
    return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
  }
  return s;
}
