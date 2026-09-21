import {
  calendarActionDetail,
  calendarActionLabel,
  calendarActionNote,
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
