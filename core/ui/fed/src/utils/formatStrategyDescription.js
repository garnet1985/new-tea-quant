/**
 * 策略 ``meta.description`` 为单行/多行字符串；仅按显式换行拆分，其余交给 CSS 自动折行。
 * 列表型说明请写在 ``meta.details.entry`` 等字段。
 * @param {unknown} text
 * @returns {string[]}
 */
export function splitStrategyDescription(text) {
  const raw = String(text || '').trim();
  if (!raw) return [];

  return raw
    .split(/\n+/)
    .map((line) => line.replace(/\s+/g, ' ').trim())
    .filter(Boolean);
}
