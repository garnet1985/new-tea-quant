import {
  readCachedWorkbenchVersion,
  strategyDesignSessionStorageKey,
  writeCachedWorkbenchVersion,
} from './strategyDesignSessionState';

describe('writeCachedWorkbenchVersion', () => {
  const strategyName = 'demo/foo';

  beforeEach(() => {
    sessionStorage.clear();
  });

  it('stores a version id and can clear it', () => {
    writeCachedWorkbenchVersion(strategyName, 'v3');
    expect(readCachedWorkbenchVersion(strategyName)).toBe('v3');
    writeCachedWorkbenchVersion(strategyName, '');
    expect(readCachedWorkbenchVersion(strategyName)).toBe('');
    const raw = sessionStorage.getItem(strategyDesignSessionStorageKey(strategyName));
    expect(JSON.parse(raw).lastCompletedWorkbenchVersionId).toBe('');
  });
});
