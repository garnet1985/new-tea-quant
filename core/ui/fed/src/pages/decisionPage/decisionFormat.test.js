import {
  calendarActionDetail,
  calendarActionLabel,
  calendarActionNote,
  mapStockStatusTags,
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
