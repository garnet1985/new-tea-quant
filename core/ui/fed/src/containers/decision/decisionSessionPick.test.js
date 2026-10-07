import { pickRememberedSession, unfinishedSessions } from './decisionSessionPick';

describe('pickRememberedSession', () => {
  const rows = [
    { dmId: '1', status: 'completed', updatedAt: '2026-01-01' },
    { dmId: '2', status: 'in_progress', updatedAt: '2026-01-03' },
    { dmId: '3', status: 'completed', updatedAt: '2026-01-02' },
  ];

  it('prefers lastSessionId even when that game is completed', () => {
    expect(pickRememberedSession({ sessions: rows, lastSessionId: '1' })).toBe('1');
  });

  it('falls back to the most recently updated session', () => {
    expect(pickRememberedSession({ sessions: rows, lastSessionId: '' })).toBe('2');
  });

  it('returns empty when there are no sessions', () => {
    expect(pickRememberedSession({ sessions: [], lastSessionId: '9' })).toBe('');
  });
});

describe('unfinishedSessions', () => {
  it('keeps in_progress only', () => {
    expect(unfinishedSessions([
      { dmId: '1', status: 'completed' },
      { dmId: '2', status: 'in_progress' },
    ]).map((row) => row.dmId)).toEqual(['2']);
  });
});
