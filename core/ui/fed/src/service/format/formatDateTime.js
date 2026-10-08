/**
 * 共用时间解析 / 展示。
 * 接受 ISO（含空格分隔、微秒）、YYYYMMDD、Date、unix 秒/毫秒。
 */

function pad2(n) {
  return String(n).padStart(2, '0');
}

function isSameLocalDay(a, b) {
  return a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate() === b.getDate();
}

/**
 * @param {unknown} raw
 * @returns {Date|null}
 */
export function parseDateTime(raw) {
  if (raw == null || raw === '') return null;
  if (raw instanceof Date) {
    return Number.isNaN(raw.getTime()) ? null : raw;
  }
  if (typeof raw === 'number' && Number.isFinite(raw)) {
    const ms = Math.abs(raw) < 1e12 ? raw * 1000 : raw;
    const d = new Date(ms);
    return Number.isNaN(d.getTime()) ? null : d;
  }
  const s = String(raw).trim();
  if (!s) return null;
  if (/^\d{8}$/.test(s)) {
    const d = new Date(
      Number(s.slice(0, 4)),
      Number(s.slice(4, 6)) - 1,
      Number(s.slice(6, 8)),
    );
    return Number.isNaN(d.getTime()) ? null : d;
  }
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
    const d = new Date(
      Number(s.slice(0, 4)),
      Number(s.slice(5, 7)) - 1,
      Number(s.slice(8, 10)),
    );
    return Number.isNaN(d.getTime()) ? null : d;
  }
  let normalized = s.includes('T') ? s : s.replace(' ', 'T');
  normalized = normalized.replace(/\.(\d{3})\d+/, '.$1');
  const parsed = new Date(normalized);
  if (!Number.isNaN(parsed.getTime())) return parsed;
  return null;
}

function formatClock(d, { seconds = false } = {}) {
  const hm = `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
  return seconds ? `${hm}:${pad2(d.getSeconds())}` : hm;
}

/**
 * @param {unknown} raw
 * @param {{ style?: 'list'|'absolute', now?: Date }} [options]
 * @returns {string}
 */
export function formatDateTime(raw, options = {}) {
  const style = options.style === 'absolute' ? 'absolute' : 'list';
  const now = options.now instanceof Date && !Number.isNaN(options.now.getTime())
    ? options.now
    : new Date();
  const d = parseDateTime(raw);
  if (!d) {
    const fallback = String(raw ?? '').trim();
    return fallback;
  }
  if (style === 'absolute') {
    return [
      `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`,
      formatClock(d, { seconds: true }),
    ].join(' ');
  }
  const clock = formatClock(d);
  if (isSameLocalDay(d, now)) return `今天 ${clock}`;
  const yesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1);
  if (isSameLocalDay(d, yesterday)) return `昨天 ${clock}`;
  if (d.getFullYear() === now.getFullYear()) {
    return `${d.getMonth() + 1}月${d.getDate()}日 ${clock}`;
  }
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${clock}`;
}

/**
 * 版本选择器次行：创建于 / 更新于 + 可读时间。
 * @param {{ createdAt?: string, updatedAt?: string }} version
 */
export function formatVersionPickTime(version) {
  const updated = String(version?.updatedAt || '').trim();
  const created = String(version?.createdAt || '').trim();
  const text = formatDateTime(updated || created, { style: 'list' });
  if (!text) return '';
  if (updated && created && updated !== created) return `更新于 ${text}`;
  return `创建于 ${text}`;
}

