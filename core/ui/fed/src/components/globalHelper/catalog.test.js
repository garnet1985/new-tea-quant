import {
  findHelpForPath,
  findHelpsForPath,
  helpTrigger,
  isHelpDismissed,
  matchStrategyDesignDecision,
  matchStrategyDesignWorkbench,
  pickHelpForManualOpen,
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

describe('matchStrategyDesignDecision', () => {
  it('matches the decision step for any strategy name', () => {
    expect(matchStrategyDesignDecision('/strategy-design/bb_v1/decision')).toBe(true);
    expect(matchStrategyDesignDecision('/strategy-design/demo/decision')).toBe(true);
  });

  it('ignores workbench steps and the list page', () => {
    expect(matchStrategyDesignDecision('/strategy-design/demo/enum')).toBe(false);
    expect(matchStrategyDesignDecision('/strategy-design/demo/portfolio')).toBe(false);
    expect(matchStrategyDesignDecision('/strategy-design')).toBe(false);
  });
});

describe('findHelpForPath / isHelpDismissed', () => {
  it('returns the strategy-design help on workbench routes', () => {
    const help = findHelpForPath('/strategy-design/demo/enum');
    expect(help?.id).toBe('strategy-design');
    expect(findHelpForPath('/strategy-design')).toBeNull();
  });

  it('returns enter and appear helps for the same route class', () => {
    const helps = findHelpsForPath('/strategy-design/demo/enum');
    expect(helps.map((item) => item.id)).toEqual([
      'strategy-design',
      'strategy-version-and-report',
      'strategy-report-compare',
    ]);
    expect(helpTrigger(helps[0])).toBe('enter');
    expect(helpTrigger(helps[1])).toBe('appear');
    expect(helpTrigger(helps[2])).toBe('appear');
    expect(helps[1].steps.map((step) => step.target)).toEqual([
      'strategy-version',
      'strategy-history',
      'strategy-version-pin',
      'strategy-report',
    ]);
    expect(helps[2].steps[0].target).toBe('strategy-report-compare');
  });

  it('prefers enter help when opening from the button', () => {
    const helps = findHelpsForPath('/strategy-design/demo/price');
    expect(pickHelpForManualOpen(helps)?.id).toBe('strategy-design');
  });

  it('returns the decision help on the decision route', () => {
    const helps = findHelpsForPath('/strategy-design/bb_v1/decision');
    expect(helps.map((item) => item.id)).toEqual(['strategy-design-decision']);
    expect(helpTrigger(helps[0])).toBe('appear');
    expect(findHelpForPath('/strategy-design/bb_v1/decision')?.id).toBe('strategy-design-decision');
    expect(pickHelpForManualOpen(helps)?.id).toBe('strategy-design-decision');
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
