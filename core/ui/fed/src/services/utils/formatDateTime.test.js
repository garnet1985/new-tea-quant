import {
  formatDateTime,
  formatVersionPickTime,
  parseDateTime,
} from './formatDateTime';

describe('parseDateTime', () => {
  it('parses ISO with T, space separator, and microseconds', () => {
    const a = parseDateTime('2024-01-02T15:30:45.123456');
    const b = parseDateTime('2024-01-02 15:30:45.123456');
    expect(a).toBeInstanceOf(Date);
    expect(b).toBeInstanceOf(Date);
    expect(a.getFullYear()).toBe(2024);
    expect(a.getMonth()).toBe(0);
    expect(a.getDate()).toBe(2);
    expect(a.getHours()).toBe(15);
    expect(a.getMinutes()).toBe(30);
    expect(b.getTime()).toBe(a.getTime());
  });

  it('parses YYYYMMDD as local calendar date', () => {
    const d = parseDateTime('20240902');
    expect(d.getFullYear()).toBe(2024);
    expect(d.getMonth()).toBe(8);
    expect(d.getDate()).toBe(2);
  });

  it('parses date-only ISO as local calendar date', () => {
    const d = parseDateTime('2024-09-02');
    expect(d.getFullYear()).toBe(2024);
    expect(d.getMonth()).toBe(8);
    expect(d.getDate()).toBe(2);
    expect(d.getHours()).toBe(0);
  });

  it('returns null for empty or invalid values', () => {
    expect(parseDateTime('')).toBeNull();
    expect(parseDateTime(null)).toBeNull();
    expect(parseDateTime('not-a-date')).toBeNull();
  });
});

describe('formatDateTime', () => {
  const now = new Date(2026, 8, 2, 22, 0, 0);

  it('uses 今天 / 昨天 / same-year / other-year for list style', () => {
    expect(formatDateTime(new Date(2026, 8, 2, 9, 5), { style: 'list', now }))
      .toBe('今天 09:05');
    expect(formatDateTime(new Date(2026, 8, 1, 18, 0), { style: 'list', now }))
      .toBe('昨天 18:00');
    expect(formatDateTime(new Date(2026, 0, 15, 8, 0), { style: 'list', now }))
      .toBe('1月15日 08:00');
    expect(formatDateTime(new Date(2024, 11, 31, 23, 59), { style: 'list', now }))
      .toBe('2024年12月31日 23:59');
  });

  it('formats absolute timestamps with seconds', () => {
    expect(formatDateTime(new Date(2024, 0, 2, 15, 30, 45), { style: 'absolute' }))
      .toBe('2024-01-02 15:30:45');
  });

  it('falls back to the original string when unparseable', () => {
    expect(formatDateTime('weird')).toBe('weird');
  });
});

describe('formatVersionPickTime', () => {
  it('labels created vs updated', () => {
    expect(formatVersionPickTime({
      createdAt: '2026-09-02T09:05:00',
      updatedAt: '2026-09-02T09:05:00',
    })).toMatch(/^创建于 /);
    expect(formatVersionPickTime({
      createdAt: '2026-09-01T09:05:00',
      updatedAt: '2026-09-02T09:05:00',
    })).toMatch(/^更新于 /);
  });
});
