import {
  findHelpForPath,
  isHelpDismissed,
  matchStrategyDesignWorkbench,
} from './catalog';

describe('matchStrategyDesignWorkbench', () => {
  it('matches enum/price/portfolio for any strategy name', () => {
    expect(matchStrategyDesignWorkbench('/strategy-design/demo/enum')).toBe(true);
    expect(matchStrategyDesignWorkbench('/strategy-design/foo/bar/price')).toBe(true);
    expect(matchStrategyDesignWorkbench('/strategy-design/x/portfolio')).toBe(true);
  });

  it('ignores list, missing step, and decision', () => {
    expect(matchStrategyDesignWorkbench('/strategy-design')).toBe(false);
    expect(matchStrategyDesignWorkbench('/strategy-design/demo')).toBe(false);
    expect(matchStrategyDesignWorkbench('/strategy-design/demo/decision')).toBe(false);
    expect(matchStrategyDesignWorkbench('/welcome')).toBe(false);
  });
});

describe('findHelpForPath / isHelpDismissed', () => {
  it('returns the strategy-design help on workbench routes', () => {
    const help = findHelpForPath('/strategy-design/demo/enum');
    expect(help?.id).toBe('strategy-design');
    expect(findHelpForPath('/strategy-design')).toBeNull();
  });

  it('treats same or newer stored version as dismissed', () => {
    const help = findHelpForPath('/strategy-design/demo/enum');
    expect(isHelpDismissed(help, {})).toBe(false);
    expect(isHelpDismissed(help, { 'strategy-design': { version: 1 } })).toBe(true);
    expect(isHelpDismissed(help, { 'strategy-design': { version: 0 } })).toBe(false);
  });

  it('honors legacyIds', () => {
    const help = {
      id: 'strategy-design',
      version: 1,
      legacyIds: ['old-design'],
    };
    expect(isHelpDismissed(help, { 'old-design': { version: 1 } })).toBe(true);
  });
});
