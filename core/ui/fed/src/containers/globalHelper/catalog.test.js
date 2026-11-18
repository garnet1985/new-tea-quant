import {
  findHelpForPath,
  findHelpsForPath,
  helpTrigger,
  isHelpDismissed,
  matchScan,
  matchStrategyDesignDecision,
  matchStrategyDesignWorkbench,
  matchStrategyList,
  matchTagList,
  matchWelcome,
  pickHelpForManualOpen,
} from './catalog';

describe('matchWelcome', () => {
  it('matches only /welcome', () => {
    expect(matchWelcome('/welcome')).toBe(true);
    expect(matchWelcome('/welcome/')).toBe(false);
    expect(matchWelcome('/strategy-design')).toBe(false);
  });
});

describe('matchStrategyList', () => {
  it('matches the strategy list index only', () => {
    expect(matchStrategyList('/strategy-design')).toBe(true);
    expect(matchStrategyList('/strategy-design/')).toBe(true);
    expect(matchStrategyList('/strategy-design/demo/enum')).toBe(false);
    expect(matchStrategyList('/strategy-design/demo')).toBe(false);
  });
});

describe('matchScan', () => {
  it('matches only /scan', () => {
    expect(matchScan('/scan')).toBe(true);
    expect(matchScan('/scan/')).toBe(true);
    expect(matchScan('/strategy-design')).toBe(false);
  });
});

describe('matchTagList', () => {
  it('matches only /advanced/tags', () => {
    expect(matchTagList('/advanced/tags')).toBe(true);
    expect(matchTagList('/advanced/tags/')).toBe(true);
    expect(matchTagList('/advanced')).toBe(false);
    expect(matchTagList('/scan')).toBe(false);
  });
});

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
  it('returns the welcome help on /welcome', () => {
    const helps = findHelpsForPath('/welcome');
    expect(helps.map((item) => item.id)).toEqual(['welcome']);
    expect(helpTrigger(helps[0])).toBe('enter');
    expect(findHelpForPath('/welcome')?.id).toBe('welcome');
    expect(pickHelpForManualOpen(helps)?.id).toBe('welcome');
    expect(helps[0].steps).toHaveLength(1);
    expect(String(helps[0].steps[0].target || '')).toBe('');
  });

  it('returns the strategy-list help on the list route', () => {
    const helps = findHelpsForPath('/strategy-design');
    expect(helps.map((item) => item.id)).toEqual(['strategy-list']);
    expect(helpTrigger(helps[0])).toBe('enter');
    expect(helps[0].steps.map((step) => step.target)).toEqual([
      'strategy-list-table',
      'strategy-list-filter',
      'strategy-list-refresh-import',
      'strategy-list-enter',
    ]);
  });

  it('returns the scan help on /scan', () => {
    const helps = findHelpsForPath('/scan');
    expect(helps.map((item) => item.id)).toEqual(['scan']);
    expect(helpTrigger(helps[0])).toBe('enter');
    expect(helps[0].steps.map((step) => step.target)).toEqual([
      'scan-mode',
      'scan-post-process',
      'scan-strategy-list',
      'scan-start',
    ]);
  });

  it('returns the tag-list help on /advanced/tags', () => {
    const helps = findHelpsForPath('/advanced/tags');
    expect(helps.map((item) => item.id)).toEqual(['tag-list']);
    expect(helpTrigger(helps[0])).toBe('enter');
    expect(String(helps[0].steps[0].target || '')).toBe('');
    expect(helps[0].steps.slice(1).map((step) => step.target)).toEqual([
      'tag-list-filter',
      'tag-list-data-key',
      'tag-list-status',
      'tag-list-run',
      'tag-list-update-mode',
      'tag-list-definitions',
      'tag-list-visualize',
    ]);
  });

  it('returns per-step enter help on workbench routes', () => {
    expect(findHelpForPath('/strategy-design/demo/enum')?.id).toBe('strategy-design-enum');
    expect(findHelpForPath('/strategy-design/demo/price')?.id).toBe('strategy-design-price');
    expect(findHelpForPath('/strategy-design/demo/portfolio')?.id).toBe('strategy-design-portfolio');
    expect(findHelpForPath('/strategy-design')?.id).toBe('strategy-list');
  });

  it('returns enter and appear helps for the same route class', () => {
    const helps = findHelpsForPath('/strategy-design/demo/enum');
    expect(helps.map((item) => item.id)).toEqual([
      'strategy-design-enum',
      'strategy-version-and-report',
      'strategy-report-stock',
      'strategy-report-compare',
    ]);
    expect(helpTrigger(helps[0])).toBe('enter');
    expect(String(helps[0].steps[0].target || '')).toBe('');
    expect(helpTrigger(helps[1])).toBe('appear');
    expect(helpTrigger(helps[2])).toBe('appear');
    expect(helpTrigger(helps[3])).toBe('appear');
    expect(helps[1].steps.map((step) => step.target)).toEqual([
      'strategy-version',
      'strategy-history',
      'strategy-report',
    ]);
    expect(helps[2].steps[0].target).toBe('strategy-report-stock');
    expect(helps[3].steps[0].target).toBe('strategy-report-compare');
  });

  it('includes portfolio chart help only on the portfolio step', () => {
    const portfolioHelps = findHelpsForPath('/strategy-design/demo/portfolio');
    expect(portfolioHelps.map((item) => item.id)).toEqual([
      'strategy-design-portfolio',
      'strategy-version-and-report',
      'strategy-report-stock',
      'strategy-report-compare',
      'strategy-report-portfolio-chart',
    ]);
    expect(findHelpsForPath('/strategy-design/demo/enum').map((item) => item.id))
      .not.toContain('strategy-report-portfolio-chart');
  });

  it('prefers enter help when opening from the button', () => {
    const helps = findHelpsForPath('/strategy-design/demo/price');
    expect(pickHelpForManualOpen(helps)?.id).toBe('strategy-design-price');
  });

  it('returns decision intro + appear helps on the decision route', () => {
    const helps = findHelpsForPath('/strategy-design/bb_v1/decision');
    expect(helps.map((item) => item.id)).toEqual([
      'strategy-design-decision-intro',
      'strategy-design-decision',
    ]);
    expect(helpTrigger(helps[0])).toBe('enter');
    expect(String(helps[0].steps[0].target || '')).toBe('');
    expect(helpTrigger(helps[1])).toBe('appear');
    expect(pickHelpForManualOpen(helps)?.id).toBe('strategy-design-decision-intro');
  });

  it('treats same or newer stored version as dismissed', () => {
    const help = findHelpForPath('/strategy-design/demo/enum');
    expect(isHelpDismissed(help, {})).toBe(false);
    expect(isHelpDismissed(help, { 'strategy-design-enum': { version: 1 } })).toBe(true);
    expect(isHelpDismissed(help, { 'strategy-design-enum': { version: 0 } })).toBe(false);
  });
});
