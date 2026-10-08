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

/** 归一成 YYYYMMDD；无法识别则空串。 */
export function normalizeMarketChartDateToken(value) {
  const s = String(value ?? '').trim();
  if (/^\d{8}$/.test(s)) return s;
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s.replace(/-/g, '');
  return '';
}

/**
 * ``updateAxisPointer`` 的 x 轴 value 有时是类目**索引**（如 434），不是日期串。
 * 优先认日期 token；否则用 categories[index] 映射。
 */
export function resolveAxisPointerDate(params, categories = []) {
  const cats = Array.isArray(categories) ? categories : [];
  const candidates = [];
  const axes = params?.axesInfo || params?.batch?.[0]?.axesInfo;
  if (Array.isArray(axes)) {
    axes.forEach((ax) => {
      candidates.push(ax?.value, ax?.axisValue);
    });
  }
  candidates.push(params?.value, params?.axisValue);

  for (let i = 0; i < candidates.length; i += 1) {
    const raw = candidates[i];
    if (raw == null || raw === '') continue;
    const asDate = normalizeMarketChartDateToken(raw);
    if (asDate) return asDate;
    const idx = Number(raw);
    if (Number.isInteger(idx) && idx >= 0 && idx < cats.length) {
      const mapped = normalizeMarketChartDateToken(cats[idx]);
      if (mapped) return mapped;
    }
  }
  return '';
}
