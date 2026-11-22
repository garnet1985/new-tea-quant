/**
 * 将 ``meta.description`` 规范为字符串。
 * 推荐 settings 用三引号多行字符串（行与行之间是真实换行）。
 * 若误写成数组/tuple，片段之间会用 ``\\n`` 拼接后再展示。
 * @param {unknown} text
 * @returns {string}
 */
export function coerceMetaDescription(text) {
  if (text == null) return '';
  if (typeof text === 'string') return text.replace(/^\s+|\s+$/g, '');
  if (Array.isArray(text)) {
    return text
      .map((item) => String(item || '').replace(/^\s+|\s+$/g, ''))
      .filter(Boolean)
      .join('\n');
  }
  return String(text).replace(/^\s+|\s+$/g, '');
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
