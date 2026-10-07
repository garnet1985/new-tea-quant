/**
 * 工作台 version id：``v3`` / ``3`` / 数字 3 → ``v3``。
 */

export function parseWorkbenchVersionNumber(value) {
  if (value == null || value === '') return 0;
  const s = String(value).trim();
  if (!s) return 0;
  const m = s.match(/^v?(\d+)$/i);
  if (!m) return 0;
  const n = Number(m[1]);
  return Number.isFinite(n) && n > 0 ? n : 0;
}

export function normalizeWorkbenchVersionId(value) {
  const n = parseWorkbenchVersionNumber(value);
  return n > 0 ? `v${n}` : '';
}
