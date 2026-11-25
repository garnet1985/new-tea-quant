/** 月历工具：month 为 1–12。 */

export const WEEKDAY_HEADS_ZH = ['一', '二', '三', '四', '五', '六', '日'];

function pad2(n) {
  return String(n).padStart(2, '0');
}

export function formatIsoDate(date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

export function monthTitle(year, month) {
  return `${year}年${month}月`;
}

/** @returns {{ year: number, month: number }} month 1–12 */
export function shiftMonth(year, month, delta) {
  const cursor = new Date(year, month - 1 + delta, 1);
  return { year: cursor.getFullYear(), month: cursor.getMonth() + 1 };
}

/**
 * 周一开始的月历格子；空位为 null，有日为 `YYYY-MM-DD`。
 * @param {number} year
 * @param {number} month 1–12
 */
export function buildMonthCells(year, month) {
  const monthIndex = month - 1;
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
