/** 单股 K 线内存 LRU；任意回测 run 开始时调用 ``clearStockKlineMemoryCache``。 */

const MAX_ENTRIES = 20;

/** @type {Map<string, object>} */
const cache = new Map();

function touch(key, value) {
  cache.delete(key);
  cache.set(key, value);
  while (cache.size > MAX_ENTRIES) {
    const oldest = cache.keys().next().value;
    cache.delete(oldest);
  }
}

export function buildStockKlineCacheKey({
  strategyName,
  versionId,
  stockId,
  term = 'daily',
  adjust = 'qfq',
  startDate = '',
  endDate = '',
}) {
  return [
    String(strategyName || '').trim(),
    String(versionId || '').trim(),
    String(stockId || '').trim(),
    String(term || '').trim(),
    String(adjust || '').trim(),
    String(startDate || '').trim(),
    String(endDate || '').trim(),
  ].join('|');
}

export function getStockKlineMemoryCache(key) {
  if (!key || !cache.has(key)) return null;
  const value = cache.get(key);
  cache.delete(key);
  cache.set(key, value);
  return value;
}

export function setStockKlineMemoryCache(key, payload) {
  if (!key || !payload) return;
  touch(key, payload);
}

export function clearStockKlineMemoryCache() {
  cache.clear();
}

/** 同策略/版本/股票任意已缓存 K 线（供 price/capital Tab 复用）。 */
export function findStockKlineCacheByStock({ strategyName, versionId, stockId }) {
  const prefix = [
    String(strategyName || '').trim(),
    String(versionId || '').trim(),
    String(stockId || '').trim(),
  ].join('|');
  if (!prefix || prefix === '||') return null;
  for (const [key, value] of cache.entries()) {
    if (key.startsWith(`${prefix}|`) && Array.isArray(value?.candles) && value.candles.length > 0) {
      touch(key, value);
      return value;
    }
  }
  return null;
}
