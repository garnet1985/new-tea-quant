import {
  calendarActionDetail,
  calendarActionLabel,
  calendarActionNote,
  mapStockStatusTags,
  plannedGoalLevelsForChart,
  statusChipClassName,
} from './decisionFormat';

describe('calendarActionDetail', () => {
  it('lists fill facts without the buy note', () => {
    const action = {
      side: 'buy',
      name: '浦发银行',
      ticker: '600000.SH',
      shares: 1000,
      amount: 10000,
      note: '看好放量',
    };
    expect(calendarActionLabel(action)).toContain('买入浦发银行');
    expect(calendarActionDetail(action)).toContain('花费');
    expect(calendarActionDetail(action)).not.toContain('看好放量');
    expect(calendarActionNote(action)).toBe('看好放量');
  });

  it('omits empty sell notes', () => {
    const action = {
      side: 'sell',
      name: '浦发银行',
      ticker: '600000.SH',
      shares: 1000,
      amount: 11000,
      note: '',
    };
    expect(calendarActionDetail(action)).not.toContain('笔记');
    expect(calendarActionNote(action)).toBe('');
  });
});

describe('mapStockStatusTags', () => {
  it('maps st / star_st / delisted labels', () => {
    expect(mapStockStatusTags(['st', 'star_st', 'delisted', 'st'])).toEqual([
      { tag: 'st', label: 'ST' },
      { tag: 'star_st', label: '*ST' },
      { tag: 'delisted', label: '退' },
    ]);
    expect(statusChipClassName('star_st')).toBe('is-star-st');
    expect(statusChipClassName('delisted')).toBe('is-delisted');
  });
});

describe('plannedGoalLevelsForChart', () => {
  const candles = [
    { date: '20230404', open: 5.0, high: 5.2, low: 4.8, close: 5.0 },
  ];
  const goals = [
    { text: '止盈 win20%: +20.0%', kind: 'take_profit', done: false },
    { text: '止损 loss20%: -20.0%', kind: 'stop_loss', done: false },
    { text: '到期 30 个交易日', kind: 'expiry', done: false },
  ];

  it('builds take-profit / stop-loss from buy-day close and goal ratios', () => {
    expect(plannedGoalLevelsForChart({
      candles,
      buyDate: '2023-04-04',
      goals,
    })).toEqual([
      { kind: 'take_profit', ratio: 0.2, price: 6, label: '止盈' },
      { kind: 'stop_loss', ratio: -0.2, price: 4, label: '止损' },
    ]);
  });

  it('falls back to buyPrice when buy bar is missing', () => {
    expect(plannedGoalLevelsForChart({
      candles,
      buyDate: '20230405',
      goals,
      buyPrice: 10,
    })).toEqual([
      { kind: 'take_profit', ratio: 0.2, price: 12, label: '止盈' },
      { kind: 'stop_loss', ratio: -0.2, price: 8, label: '止损' },
    ]);
  });

  it('returns null when buy bar or ratio goals are missing', () => {
    expect(plannedGoalLevelsForChart({ candles, buyDate: '20230405', goals })).toBeNull();
    expect(plannedGoalLevelsForChart({
      candles,
      buyDate: '20230404',
      goals: [{ text: '到期 30 个交易日', kind: 'expiry', done: false }],
    })).toBeNull();
  });
});
