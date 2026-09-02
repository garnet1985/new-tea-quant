import {
  VERSION_MARK_EXPIRES_SOON,
  VERSION_MARK_READONLY,
  lookupVersionById,
  versionPickMarks,
  versionPickSearchText,
} from './versionPickMarks';

describe('versionPickMarks', () => {
  it('returns empty marks for a plain version', () => {
    expect(versionPickMarks({ id: 'v3' })).toEqual([]);
  });

  it('marks env-invalid versions as read-only artifacts', () => {
    const marks = versionPickMarks({ id: 'v2', envInvalid: true });
    expect(marks.map((m) => m.label)).toEqual([VERSION_MARK_READONLY]);
  });

  it('marks keep-N risk versions as soon to expire', () => {
    const marks = versionPickMarks({ id: 'v1', expiresSoon: true });
    expect(marks.map((m) => m.label)).toEqual([VERSION_MARK_EXPIRES_SOON]);
  });

  it('can show both marks', () => {
    const marks = versionPickMarks({
      id: 'v1',
      envInvalid: true,
      expiresSoon: true,
    });
    expect(marks.map((m) => m.key)).toEqual(['readonly', 'expires']);
  });

  it('looks up a row by id and falls back to a stub', () => {
    const rows = [{ id: 'v2', envInvalid: true }];
    expect(lookupVersionById(rows, 'v2').envInvalid).toBe(true);
    expect(lookupVersionById(rows, 'v9')).toEqual({ id: 'v9' });
  });

  it('includes mark labels in search text', () => {
    const haystack = versionPickSearchText({
      id: 'v1',
      updatedAt: '2024-01-01',
      envInvalid: true,
      expiresSoon: true,
    });
    expect(haystack).toContain('v1');
    expect(haystack).toContain(VERSION_MARK_READONLY);
    expect(haystack).toContain(VERSION_MARK_EXPIRES_SOON);
  });
});
