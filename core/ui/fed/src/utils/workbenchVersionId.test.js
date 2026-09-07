import {
  normalizeWorkbenchVersionId,
  parseWorkbenchVersionNumber,
} from './workbenchVersionId';

describe('workbenchVersionId', () => {
  it('normalizes string and numeric forms', () => {
    expect(normalizeWorkbenchVersionId('v4')).toBe('v4');
    expect(normalizeWorkbenchVersionId('4')).toBe('v4');
    expect(normalizeWorkbenchVersionId(4)).toBe('v4');
    expect(normalizeWorkbenchVersionId(0)).toBe('');
    expect(normalizeWorkbenchVersionId('')).toBe('');
  });

  it('parses version numbers for stale-snapshot comparison', () => {
    expect(parseWorkbenchVersionNumber('v4')).toBe(4);
    expect(parseWorkbenchVersionNumber('v1')).toBe(1);
    expect(parseWorkbenchVersionNumber(1)).toBe(1);
  });
});
