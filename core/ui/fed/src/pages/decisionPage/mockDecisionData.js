/** 决策者 UI 静态 mock。接 BFF 后由此替换，不改页面结构。 */

export const DECISION_STRATEGY = {
  key: 'rsi_v1',
  versionId: 3,
  range: '2024-01-02 → 2025-06-30',
  maxPortfolioSize: 5,
  lotSize: 100,
  strategyWinRate: '58%',
  strategyAvgRoi: '+3.1%',
  strategySample: 86,
};

export const INITIAL_SESSIONS = [
  { id: 1, status: 'in_progress', date: '2025-04-07', cash: 999314.65, holdings: 1 },
  { id: 2, status: 'in_progress', date: '2025-03-12', cash: 1012440, holdings: 2 },
  { id: 3, status: 'completed', date: '2025-06-30', cash: 1086210.4, holdings: 0 },
];

export const SESSION_DAYS = {
  1: [
    {
      date: '2025-04-07',
      cash: 999314.65,
      calendar: [
        { date: '03-10', state: 'past' },
        { date: '03-21', state: 'past' },
        { date: '03-28', state: 'past' },
        { date: '04-07', state: 'now' },
        { date: '04-15', state: 'locked' },
        { date: '04-22', state: 'locked' },
      ],
      events: [
        { date: '2025-04-02', text: '出场 601318.SH 中国平安  800 股  盈亏 +1,240.00  (止盈)', win: true },
        { date: '2025-04-03', text: '出场 000858.SZ 五粮液  200 股  盈亏 -860.50  (到期)', win: false },
      ],
      holdings: [
        { id: '600036.SH', ticker: '600036.SH', name: '招商银行', shares: 700, buy: '2025-03-21 @ 36.80', pnl: '+1,120.00' },
      ],
      opps: [
        { id: 1, ticker: '000001.SZ', name: '平安银行', price: 11.42, wr: '—', roi: '—' },
        { id: 2, ticker: '000002.SZ', name: '万科A', price: 7.18, wr: '50%', roi: '+1.2%' },
        { id: 3, ticker: '600519.SH', name: '贵州茅台', price: 1482.0, wr: '67%', roi: '+4.8%' },
        { id: 4, ticker: '601318.SH', name: '中国平安', price: 48.26, wr: '40%', roi: '-0.6%' },
        { id: 5, ticker: '000858.SZ', name: '五粮液', price: 128.4, wr: '—', roi: '—' },
        { id: 6, ticker: '600276.SH', name: '恒瑞医药', price: 42.15, wr: '75%', roi: '+6.1%' },
        { id: 7, ticker: '002415.SZ', name: '海康威视', price: 31.08, wr: '33%', roi: '-1.4%' },
        { id: 8, ticker: '601012.SH', name: '隆基绿能', price: 16.72, wr: '—', roi: '—' },
      ],
      note: '当日共 31 条机会，此处示意前 8 条。点行打开 info；K 线停在当前日。',
    },
    {
      date: '2025-04-15',
      cash: 968104.21,
      calendar: [
        { date: '03-21', state: 'past' },
        { date: '03-28', state: 'past' },
        { date: '04-07', state: 'past' },
        { date: '04-15', state: 'now' },
        { date: '04-22', state: 'locked' },
        { date: '05-06', state: 'locked' },
      ],
      events: [
        { date: '2025-04-11', text: '出场 600036.SH 招商银行  700 股  盈亏 +2,310.00  (止盈)', win: true },
      ],
      holdings: [],
      opps: [
        { id: 1, ticker: '600030.SH', name: '中信证券', price: 26.44, wr: '60%', roi: '+2.4%' },
        { id: 2, ticker: '000725.SZ', name: '京东方A', price: 4.12, wr: '—', roi: '—' },
        { id: 3, ticker: '601888.SH', name: '中国中免', price: 68.9, wr: '45%', roi: '+0.8%' },
        { id: 4, ticker: '002594.SZ', name: '比亚迪', price: 312.5, wr: '80%', roi: '+7.2%' },
      ],
      note: '推进后跳过了空日；event 区是这段路上的出场通报。',
    },
  ],
  2: [
    {
      date: '2025-03-12',
      cash: 1012440,
      calendar: [
        { date: '02-18', state: 'past' },
        { date: '03-03', state: 'past' },
        { date: '03-12', state: 'now' },
        { date: '03-21', state: 'locked' },
        { date: '03-28', state: 'locked' },
      ],
      events: [],
      holdings: [
        { id: '000333.SZ', ticker: '000333.SZ', name: '美的集团', shares: 400, buy: '2025-02-18 @ 72.10', pnl: '+640.00' },
        { id: '600900.SH', ticker: '600900.SH', name: '长江电力', shares: 1000, buy: '2025-03-03 @ 27.40', pnl: '-180.00' },
      ],
      opps: [
        { id: 1, ticker: '601166.SH', name: '兴业银行', price: 18.22, wr: '55%', roi: '+2.0%' },
        { id: 2, ticker: '000651.SZ', name: '格力电器', price: 41.08, wr: '—', roi: '—' },
        { id: 3, ticker: '600887.SH', name: '伊利股份', price: 28.76, wr: '62%', roi: '+3.4%' },
      ],
      note: '第 2 局较早的停顿点。继续入口在 ≥2 局时不会默认进第 1 局。',
    },
  ],
  3: [
    {
      date: '2025-06-30',
      cash: 1086210.4,
      calendar: [
        { date: '06-06', state: 'past' },
        { date: '06-16', state: 'past' },
        { date: '06-30', state: 'now' },
      ],
      events: [],
      holdings: [],
      opps: [],
      note: '本局已走完。终局报告与机器 portfolio 同结构，本页不画净值曲线。',
      completed: true,
    },
  ],
  4: [
    {
      date: '2024-01-08',
      cash: 1000000,
      calendar: [
        { date: '01-08', state: 'now' },
        { date: '01-16', state: 'locked' },
        { date: '01-24', state: 'locked' },
        { date: '02-05', state: 'locked' },
      ],
      events: [],
      holdings: [],
      opps: [
        { id: 1, ticker: '600000.SH', name: '浦发银行', price: 8.64, wr: '—', roi: '—' },
        { id: 2, ticker: '000001.SZ', name: '平安银行', price: 9.12, wr: '—', roi: '—' },
        { id: 3, ticker: '601318.SH', name: '中国平安', price: 40.18, wr: '—', roi: '—' },
        { id: 4, ticker: '600519.SH', name: '贵州茅台', price: 1688.0, wr: '—', roi: '—' },
      ],
      note: '新局：区间内尚无已实现样本，标的 as-of 胜率为 —。',
    },
  ],
};

export function formatMoney(value) {
  return Number(value).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function playPath(session) {
  const query = new URLSearchParams({ session: String(session.id) });
  if (session.status === 'completed') query.set('readonly', '1');
  return `/decision/play?${query.toString()}`;
}

export function newPlayPath() {
  return '/decision/play?new=1';
}

function toYyyymmdd(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}${m}${d}`;
}

/** 生成截至 asOf 的 mock K 线（yyyymmdd），不含未来。 */
export function buildMockCandles(asOf, lastClose, count = 48) {
  const end = new Date(`${asOf}T00:00:00`);
  const candles = [];
  let close = Number(lastClose) * 0.92;
  let i = 0;
  const cursor = new Date(end);
  while (candles.length < count) {
    const dow = cursor.getDay();
    if (dow !== 0 && dow !== 6) {
      const open = close;
      const change = (Math.sin((lastClose || 1) + i) * 0.012 + 0.0015) * open;
      close = +(open + change).toFixed(2);
      const high = +(Math.max(open, close) * 1.008).toFixed(2);
      const low = +(Math.min(open, close) * 0.992).toFixed(2);
      candles.push({
        date: toYyyymmdd(cursor),
        open: +open.toFixed(2),
        close,
        high,
        low,
      });
      i += 1;
    }
    cursor.setDate(cursor.getDate() - 1);
  }
  candles.reverse();
  const last = candles[candles.length - 1];
  last.date = toYyyymmdd(end);
  last.close = Number(lastClose);
  last.high = Math.max(last.high, last.close, last.open);
  last.low = Math.min(last.low, last.close, last.open);
  return candles;
}
