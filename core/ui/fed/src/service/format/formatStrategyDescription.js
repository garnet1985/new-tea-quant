/**
 * 将 ``meta.description`` 规范为字符串（settings 里误写 tuple 时由后端/前端统一展平）。
 * @param {unknown} text
 * @returns {string}
 */
export function coerceMetaDescription(text) {
  if (text == null) return '';
  if (typeof text === 'string') return text.trim();
  if (Array.isArray(text)) {
    return text
      .map((item) => String(item || '').trim())
      .filter(Boolean)
      .join('');
  }
  return String(text).trim();
}

/**
 * 策略 ``meta.description`` 为单行/多行字符串；仅按显式换行拆分，其余交给 CSS 自动折行。
 * 列表型说明请写在 ``meta.details.entry`` 等字段。
 * @param {unknown} text
 * @returns {string[]}
 */
export function splitStrategyDescription(text) {
  const raw = coerceMetaDescription(text);
  if (!raw) return [];

  return raw
    .split(/\n+/)
    .map((line) => line.replace(/\s+/g, ' ').trim())
    .filter(Boolean);
}
