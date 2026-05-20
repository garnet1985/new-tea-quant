/** ``result_report.*.backtest_period`` 展示（与后端 ``backtest_date_resolve`` 同源）。 */

const SOURCE_LABELS_ZH = {
  settings: '策略配置',
  sample_earliest_kline: '样本池最早 K 线',
  default: '系统默认起点',
  latest_trading_day: '最新已完成交易日',
  flow: '本次运行',
  missing: '未解析',
};

export function formatBacktestDateYmd(ymd) {
  const s = String(ymd || '').trim();
  if (/^\d{8}$/.test(s)) {
    return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
  }
  return s;
}

export function readBacktestPeriodFromSlot(slot) {
  if (!slot || typeof slot !== 'object') return null;
  const bp = slot.backtest_period;
  if (bp && typeof bp === 'object') {
    const start = String(bp.start_date || '').trim();
    const end = String(bp.end_date || '').trim();
    if (start && end) {
      return {
        start_date: start,
        end_date: end,
        start_source: String(bp.start_source || '').trim(),
        end_source: String(bp.end_source || '').trim(),
      };
    }
  }
  const legacyStart = String(slot.start_date || '').trim();
  const legacyEnd = String(slot.end_date || '').trim();
  if (legacyStart && legacyEnd) {
    return {
      start_date: legacyStart,
      end_date: legacyEnd,
      start_source: '',
      end_source: '',
    };
  }
  return null;
}

function sourceHint(source) {
  const key = String(source || '').trim();
  if (!key) return '';
  return SOURCE_LABELS_ZH[key] || key;
}

/** 单行说明：区间 + 起止来源（有则展示）。 */
export function formatBacktestPeriodLine(period) {
  if (!period?.start_date || !period?.end_date) return '';
  const range = `${formatBacktestDateYmd(period.start_date)} — ${formatBacktestDateYmd(period.end_date)}`;
  const startHint = sourceHint(period.start_source);
  const endHint = sourceHint(period.end_source);
  const parts = [`回测区间：${range}`];
  if (startHint || endHint) {
    const detail = [];
    if (startHint) detail.push(`开始：${startHint}`);
    if (endHint) detail.push(`结束：${endHint}`);
    parts.push(`（${detail.join('；')}）`);
  }
  return parts.join('');
}

export const BACKTEST_PERIOD_TOOLTIP =
  '本次回测实际使用的起止交易日。未在策略中填写时，开始日可能取自样本池最早 K 线或系统默认起点，结束日通常为最新已完成交易日。';
