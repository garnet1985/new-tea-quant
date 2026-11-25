import {
  findHelpForPath,
  findHelpsForPath,
  helpTrigger,
  isHelpDismissed,
  matchDataContractList,
  matchDataSourceList,
  matchScan,
  matchPostProcess,
  matchSeriesRelationDetail,
  matchSeriesRelationList,
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

describe('matchDataSourceList', () => {
  it('matches only /advanced/data-sources', () => {
    expect(matchDataSourceList('/advanced/data-sources')).toBe(true);
    expect(matchDataSourceList('/advanced/data-sources/')).toBe(true);
    expect(matchDataSourceList('/advanced/tags')).toBe(false);
    expect(matchDataSourceList('/scan')).toBe(false);
  });
});

describe('matchDataContractList', () => {
  it('matches only /advanced/data-contracts', () => {
    expect(matchDataContractList('/advanced/data-contracts')).toBe(true);
    expect(matchDataContractList('/advanced/data-contracts/')).toBe(true);
    expect(matchDataContractList('/advanced/data-sources')).toBe(false);
    expect(matchDataContractList('/scan')).toBe(false);
  });
});

describe('matchSeriesRelationList', () => {
  it('matches only the series-relation index', () => {
    expect(matchSeriesRelationList('/advanced/series-relation')).toBe(true);
    expect(matchSeriesRelationList('/advanced/series-relation/')).toBe(true);
    expect(matchSeriesRelationList('/advanced/series-relation/demo')).toBe(false);
    expect(matchSeriesRelationList('/advanced/data-contracts')).toBe(false);
  });
});

describe('matchSeriesRelationDetail', () => {
  it('matches series-relation detail routes only', () => {
    expect(matchSeriesRelationDetail('/advanced/series-relation/demo')).toBe(true);
    expect(matchSeriesRelationDetail('/advanced/series-relation/a/b')).toBe(true);
    expect(matchSeriesRelationDetail('/advanced/series-relation')).toBe(false);
    expect(matchSeriesRelationDetail('/advanced/series-relation/')).toBe(false);
  });
});

describe('matchPostProcess', () => {
  it('matches only /advanced/post-process', () => {
    expect(matchPostProcess('/advanced/post-process')).toBe(true);
    expect(matchPostProcess('/advanced/post-process/')).toBe(true);
    expect(matchPostProcess('/advanced/tags')).toBe(false);
    expect(matchPostProcess('/scan')).toBe(false);
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
    expect(String(helps[0].steps[0].target || '')).toBe('');
    expect(helps[0].steps.slice(1).map((step) => step.target)).toEqual([
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

  it('returns the data-source-list help on /advanced/data-sources', () => {
    const helps = findHelpsForPath('/advanced/data-sources');
    expect(helps.map((item) => item.id)).toEqual(['data-source-list']);
    expect(helpTrigger(helps[0])).toBe('enter');
    expect(String(helps[0].steps[0].target || '')).toBe('');
    expect(helps[0].steps.slice(1).map((step) => step.target)).toEqual([
      'data-source-list-providers',
      'data-source-list-status',
      'data-source-list-origin',
      'data-source-list-renew-type',
      'data-source-list-rate-limit',
      'data-source-list-auth',
    ]);
  });

  it('returns the data-contract-list help on /advanced/data-contracts', () => {
    const helps = findHelpsForPath('/advanced/data-contracts');
    expect(helps.map((item) => item.id)).toEqual(['data-contract-list']);
    expect(helpTrigger(helps[0])).toBe('enter');
    expect(String(helps[0].steps[0].target || '')).toBe('');
    expect(helps[0].steps.slice(1).map((step) => step.target)).toEqual([
      'data-contract-list-rediscover',
      'data-contract-list-key',
      'data-contract-list-origin',
      'data-contract-list-time-series',
      'data-contract-list-per-entity',
    ]);
  });

  it('returns the series-relation-list help on /advanced/series-relation', () => {
    const helps = findHelpsForPath('/advanced/series-relation');
    expect(helps.map((item) => item.id)).toEqual(['series-relation-list']);
    expect(helpTrigger(helps[0])).toBe('enter');
    expect(String(helps[0].steps[0].target || '')).toBe('');
    expect(helps[0].steps.slice(1).map((step) => step.target)).toEqual([
      'series-relation-list-refresh',
      'series-relation-list-create',
    ]);
  });

  it('returns the series-relation-detail help on detail routes', () => {
    const helps = findHelpsForPath('/advanced/series-relation/demo');
    expect(helps.map((item) => item.id)).toEqual(['series-relation-detail']);
    expect(helpTrigger(helps[0])).toBe('enter');
    expect(helps[0].steps.map((step) => step.target)).toEqual([
      'series-relation-detail-globals',
      'series-relation-detail-series',
      'series-relation-detail-run',
    ]);
  });

  it('returns the post-process help on /advanced/post-process', () => {
    const helps = findHelpsForPath('/advanced/post-process');
    expect(helps.map((item) => item.id)).toEqual(['post-process']);
    expect(helpTrigger(helps[0])).toBe('enter');
    expect(String(helps[0].steps[0].target || '')).toBe('');
    expect(helps[0].steps.slice(1).map((step) => step.target)).toEqual([
      'post-process-schemes',
      'post-process-enabled',
      'post-process-steps',
      'post-process-adapters',
    ]);
  });

  it('returns per-step enter help on workbench routes with a shared dismiss id', () => {
    expect(findHelpForPath('/strategy-design/demo/enum')?.id).toBe('strategy-design');
    expect(findHelpForPath('/strategy-design/demo/price')?.id).toBe('strategy-design');
    expect(findHelpForPath('/strategy-design/demo/portfolio')?.id).toBe('strategy-design');
    expect(findHelpForPath('/strategy-design')?.id).toBe('strategy-list');
  });

  it('returns enter and appear helps for the same route class', () => {
    const helps = findHelpsForPath('/strategy-design/demo/enum');
    expect(helps.map((item) => item.id)).toEqual([
      'strategy-design',
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
      'strategy-design',
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
    expect(pickHelpForManualOpen(helps)?.id).toBe('strategy-design');
  });

  it('keeps workbench enter help dismissed across enum/price/portfolio', () => {
    const dismissed = { 'strategy-design': { version: 1 } };
    expect(isHelpDismissed(findHelpForPath('/strategy-design/demo/enum'), dismissed)).toBe(true);
    expect(isHelpDismissed(findHelpForPath('/strategy-design/demo/price'), dismissed)).toBe(true);
    expect(isHelpDismissed(findHelpForPath('/strategy-design/demo/portfolio'), dismissed)).toBe(true);
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
    expect(isHelpDismissed(help, { 'strategy-design': { version: 1 } })).toBe(true);
    expect(isHelpDismissed(help, { 'strategy-design': { version: 0 } })).toBe(false);
  });
});
