import {
  formatMarketChartDateLabel,
  normalizeMarketChartDateToken,
  resolveAxisPointerDate,
} from './dateFormat';
import { pickFinanceSnapshot } from './adapters/stockKlinePayload';

describe('marketChart date helpers', () => {
  it('normalizes YYYYMMDD and dashed dates', () => {
    expect(normalizeMarketChartDateToken('20241023')).toBe('20241023');
    expect(normalizeMarketChartDateToken('2024-10-23')).toBe('20241023');
    expect(normalizeMarketChartDateToken(434)).toBe('');
    expect(formatMarketChartDateLabel('20241023')).toBe('2024-10-23');
  });

  it('maps axis-pointer category index to date', () => {
    const cats = ['20241022', '20241023', '20241106'];
    expect(resolveAxisPointerDate({
      axesInfo: [{ value: 1 }],
    }, cats)).toBe('20241023');
    expect(resolveAxisPointerDate({
      axesInfo: [{ value: '2024-11-06' }],
    }, cats)).toBe('20241106');
    expect(resolveAxisPointerDate({
      axesInfo: [{ value: 434 }],
    }, cats)).toBe('');
  });

  it('rejects non-date asOf for finance PIT', () => {
    const events = [
      { date: '20241023', quarter: '2024Q3', snapshot: { roe: 1 } },
      { date: '20251029', quarter: '2025Q3', snapshot: { roe: 2 } },
    ];
    expect(pickFinanceSnapshot(events, '434')).toBeNull();
    expect(pickFinanceSnapshot(events, '20241022')).toBeNull();
    expect(pickFinanceSnapshot(events, '20241023')?.quarter).toBe('2024Q3');
    expect(pickFinanceSnapshot(events, '20241106')?.quarter).toBe('2024Q3');
    expect(pickFinanceSnapshot(events, '20251029')?.quarter).toBe('2025Q3');
  });
});
