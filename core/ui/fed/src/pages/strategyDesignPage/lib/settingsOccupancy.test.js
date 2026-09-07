import {
  isDraftDirty,
  persistComparable,
} from './settingsOccupancy';

describe('settingsOccupancy', () => {
  it('treats identical persist payloads as clean regardless of key order', () => {
    const loaded = { core: { n: 1 }, meta: { key: 'a' } };
    const draft = { meta: { key: 'a' }, core: { n: 1 } };
    expect(isDraftDirty(draft, loaded)).toBe(false);
  });

  it('flags dirty when a persist field changes', () => {
    const loaded = persistComparable({ core: { n: 1 }, meta: { name: 'a' } });
    const draft = persistComparable({ core: { n: 1 }, meta: { name: 'b' } });
    expect(isDraftDirty(draft, loaded)).toBe(true);
  });

  it('flags dirty when analysis.enabled changes (persisted, not fingerprint)', () => {
    const loaded = persistComparable({ core: { n: 1 }, analysis: { enabled: false } });
    const draft = persistComparable({ core: { n: 1 }, analysis: { enabled: true } });
    expect(isDraftDirty(draft, loaded)).toBe(true);
  });
});
