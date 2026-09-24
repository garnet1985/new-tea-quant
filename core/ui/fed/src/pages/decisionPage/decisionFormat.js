/** 决策者展示格式：日期 / 金额 / 月历。与 BFF DTO 的 YYYYMMDD 在 decisionApi 里互转。 */

export function formatMoney(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  return n.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatSignedMoney(value) {
  const n = Number(value) || 0;
  const sign = n > 0 ? '+' : '';
  return `${sign}${formatMoney(n)}`;
}

/** 工作台 version id：``1`` / ``v1`` 都显示成 v1。 */
export function formatSimVersion(raw) {
  const text = String(raw || '').trim();
  if (!text) return '—';
  return /^v/i.test(text) ? text : `v${text}`;
}

export function formatPct(ratio) {
  if (ratio == null || !Number.isFinite(Number(ratio))) return '—';
  return `${(Number(ratio) * 100).toFixed(0)}%`;
}

/** as-of 胜率：无样本为 — */
export function formatWinRate(rate, sampleSize) {
  if (sampleSize != null && Number(sampleSize) <= 0) return '—';
  if (rate == null || !Number.isFinite(Number(rate))) return '—';
  return `${(Number(rate) * 100).toFixed(0)}%`;
}

/** as-of 平均 ROI：有符号一位小数 */
export function formatAvgRoi(roi, sampleSize) {
  if (sampleSize != null && Number(sampleSize) <= 0) return '—';
  if (roi == null || !Number.isFinite(Number(roi))) return '—';
  const n = Number(roi) * 100;
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(1)}%`;
}

const STOCK_STATUS_LABELS = {
  st: 'ST',
  star_st: '*ST',
  delisted: '退',
};

/** 现场状态：``st`` / ``star_st`` / ``delisted`` → 展示标签。 */
export function mapStockStatusTags(raw) {
  const seen = new Set();
  const out = [];
  (Array.isArray(raw) ? raw : []).forEach((item) => {
    const tag = String(item || '').trim().toLowerCase();
    const label = STOCK_STATUS_LABELS[tag];
    if (!label || seen.has(tag)) return;
    seen.add(tag);
    out.push({ tag, label });
  });
  return out;
}

export function statusChipClassName(tag) {
  const key = String(tag || '').trim().toLowerCase();
  if (key === 'star_st') return 'is-star-st';
  if (key === 'delisted') return 'is-delisted';
  if (key === 'st') return 'is-st';
  return '';
}

function parseIsoDate(value) {
  return new Date(`${value}T00:00:00`);
}

function formatIsoDate(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function isWeekend(date) {
  const dow = date.getDay();
  return dow === 0 || dow === 6;
}

const WEEKDAY_LABELS = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];

export function weekdayLabel(dateStr) {
  if (!dateStr) return '';
  return WEEKDAY_LABELS[parseIsoDate(dateStr).getDay()] || '';
}

export function monthTitle(year, monthIndex) {
  return `${year}年${monthIndex + 1}月`;
}

export function ymKey(year, monthIndex) {
  return `${year}-${String(monthIndex + 1).padStart(2, '0')}`;
}

export function dateToYearMonth(dateStr) {
  if (!dateStr) return { year: new Date().getFullYear(), month: new Date().getMonth() };
  const date = parseIsoDate(dateStr);
  return { year: date.getFullYear(), month: date.getMonth() };
}

export function shiftMonth(year, monthIndex, delta) {
  const cursor = new Date(year, monthIndex + delta, 1);
  return { year: cursor.getFullYear(), month: cursor.getMonth() };
}

export function canShiftMonth(year, monthIndex, delta, startStr, endStr) {
  if (!startStr || !endStr) return false;
  const next = shiftMonth(year, monthIndex, delta);
  const key = ymKey(next.year, next.month);
  return key >= startStr.slice(0, 7) && key <= endStr.slice(0, 7);
}

/** 周一开始的月历格子，空位为 null。 */
export function buildMonthCells(year, monthIndex) {
  const first = new Date(year, monthIndex, 1);
  const pad = (first.getDay() + 6) % 7;
  const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < pad; i += 1) cells.push(null);
  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push(formatIsoDate(new Date(year, monthIndex, day)));
  }
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

export function countTradingDaysInclusive(fromDate, toDate) {
  if (!fromDate || !toDate || fromDate > toDate) return 0;
  let count = 0;
  const cursor = parseIsoDate(fromDate);
  const end = parseIsoDate(toDate);
  while (cursor <= end) {
    if (!isWeekend(cursor)) count += 1;
    cursor.setDate(cursor.getDate() + 1);
  }
  return count;
}

/** ``fromDate`` 之后到 ``toDate``（含）的开市日，周末跳过。 */
export function listOpenDaysAfter(fromDate, toDate) {
  if (!fromDate || !toDate || fromDate >= toDate) return [];
  const out = [];
  const cursor = parseIsoDate(fromDate);
  const end = parseIsoDate(toDate);
  cursor.setDate(cursor.getDate() + 1);
  while (cursor <= end) {
    if (!isWeekend(cursor)) out.push(formatIsoDate(new Date(cursor)));
    cursor.setDate(cursor.getDate() + 1);
  }
  return out;
}

/** as-of 当天及之前的机会数与成交，按 ISO 日期索引。未来日不进入。 */
export function indexCalendarDays(days, asOf) {
  const out = {};
  (days || []).forEach((day) => {
    const date = String(day?.date || '');
    if (!date || (asOf && date > asOf)) return;
    out[date] = {
      oppCount: Number(day.oppCount) || 0,
      actions: Array.isArray(day.actions) ? day.actions : [],
    };
  });
  return out;
}

export function calendarActionLabel(action) {
  const verb = action?.side === 'sell' ? '卖出' : '买入';
  const who = String(action?.name || action?.ticker || '标的').trim() || '标的';
  const shares = Number(action?.shares) || 0;
  return `${verb}${who} ${shares.toLocaleString()}股，花费${formatMoney(action?.amount)}`;
}

export function calendarActionDetail(action) {
  const verb = action?.side === 'sell' ? '卖出' : '买入';
  const name = String(action?.name || '').trim();
  const ticker = String(action?.ticker || '').trim();
  const who = name || ticker || '标的';
  const shares = Number(action?.shares) || 0;
  const lines = [`${verb} ${who}`];
  if (ticker && ticker !== who) lines.push(ticker);
  lines.push(`${shares.toLocaleString()} 股`);
  lines.push(`花费 ${formatMoney(action?.amount)}`);
  return lines.join('\n');
}

export function calendarActionNote(action) {
  return String(action?.note || '').trim();
}

/**
 * 持仓目标 → 主图止盈/止损虚线价位。
 * 基准优先买入日 K 线收盘（与前复权主图同尺度）；没有对应 K 线时退回 buyPrice。
 * 比例从目标文案 ``: +20.0%`` 解析；kind 缺失时按「止盈/止损」前缀推断。
 */
export function plannedGoalLevelsForChart({
  candles,
  buyDate,
  goals,
  buyPrice,
} = {}) {
  const ymd = String(buyDate || '').replace(/-/g, '');
  if (!/^\d{8}$/.test(ymd) && !(Number(buyPrice) > 0)) return null;

  let basis = null;
  if (/^\d{8}$/.test(ymd)) {
    const bar = (Array.isArray(candles) ? candles : []).find(
      (row) => String(row?.date || '').replace(/-/g, '') === ymd,
    );
    const close = Number(bar?.close);
    if (Number.isFinite(close) && close > 0) basis = close;
  }
  if (basis == null) {
    const fallback = Number(buyPrice);
    if (Number.isFinite(fallback) && fallback > 0) basis = fallback;
  }
  if (basis == null || !(basis > 0)) return null;

  const levels = [];
  (Array.isArray(goals) ? goals : []).forEach((goal) => {
    const text = String(goal?.text || '');
    let kind = String(goal?.kind || '').trim();
    if (kind !== 'take_profit' && kind !== 'stop_loss') {
      if (text.startsWith('止盈')) kind = 'take_profit';
      else if (text.startsWith('止损')) kind = 'stop_loss';
      else return;
    }
    const match = text.match(/:\s*([+-]?\d+(?:\.\d+)?)\s*%/);
    if (!match) return;
    const ratio = Number(match[1]) / 100;
    if (!Number.isFinite(ratio)) return;
    const price = Number((basis * (1 + ratio)).toFixed(2));
    if (!Number.isFinite(price) || price <= 0) return;
    levels.push({
      kind,
      ratio,
      price,
      label: kind === 'take_profit' ? '止盈' : '止损',
    });
  });
  return levels.length ? levels : null;
}
