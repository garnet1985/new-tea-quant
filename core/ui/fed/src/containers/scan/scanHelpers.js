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

/** 工作台主号（整数）；无则 0。 */
export function readWorkbenchVersion(pack) {
  if (!pack || typeof pack !== 'object') return 0;
  const raw = pack.workbench_version ?? pack.workbenchVersion;
  const n = Number(raw);
  if (Number.isFinite(n) && n > 0) return Math.trunc(n);
  const label = String(pack.strategy_version ?? pack.strategyVersion ?? '').trim();
  const m = /^v?(\d+)$/i.exec(label);
  if (!m) return 0;
  const fromLabel = Number(m[1]);
  return Number.isFinite(fromLabel) && fromLabel > 0 ? Math.trunc(fromLabel) : 0;
}

/** ``vN`` 展示名；无版本返回空串。 */
export function formatStrategyVersionLabel(ver) {
  const n = Number(ver);
  if (!Number.isFinite(n) || n <= 0) return '';
  return `v${Math.trunc(n)}`;
}

/** 机会数量旁 warning 图标 hover 文案。 */
export const SCAN_VERSION_STALE_TIP = '当前结果基于的策略版本不是最新版本，建议您重新扫描';
export const SCAN_SETTINGS_STALE_TIP = '策略设置或环境已变更，当前结果可能过时，建议您重新扫描';
