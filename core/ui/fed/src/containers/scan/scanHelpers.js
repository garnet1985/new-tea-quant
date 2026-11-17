/** Scan 页小工具（无 React 状态）。 */

export function readOpportunityCount(pack) {
  if (!pack || typeof pack !== 'object') return null;
  const raw = pack.total_opportunities ?? pack.totalOpportunities ?? pack.opportunity_count;
  if (raw == null || raw === '') return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

/** 图鉴 / 调试用：是否展示「报告生成时刻」 */
export const SHOW_REPORT_GENERATED_AT = false;

export function formatScanDate(v) {
  const raw = String(v || '').trim();
  if (!raw) return '';
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
  if (/^\d{8}$/.test(raw)) return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`;
  return raw;
}
