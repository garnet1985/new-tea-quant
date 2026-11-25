/** 制定策略四步。前三步对齐后端 WorkbenchStep；第四步决策模拟是交互式模拟回测，不走 simulate()。 */
export const STRATEGY_DESIGN_STEPS = [
  {
    key: 'enum',
    no: 1,
    label: '机会盘点',
    executionPanelTitle: '盘点所有机会，并统计他们的数量和分布',
    pathSegment: 'enum',
  },
  {
    key: 'price',
    no: 2,
    label: '价格回测',
    executionPanelTitle: '合并相似的机会，并统计合并后机会的收益和分布',
    pathSegment: 'price',
  },
  {
    key: 'portfolio',
    no: 3,
    label: '投资模拟',
    executionPanelTitle: '使用给定的资金和交易策略，模拟实盘投资',
    pathSegment: 'portfolio',
  },
  {
    key: 'decision',
    no: 4,
    label: '决策模拟',
    executionPanelTitle: '使用给定的资金，由我自己决策投资。',
    pathSegment: 'decision',
    interactive: true,
    requires: ['enum', 'portfolio'],
  },
];

/** Meta 顶栏：当前步说明（标题 + 一句摘要） */
export const STRATEGY_DESIGN_STEP_INTRO = {
  enum: {
    title: '机会盘点',
    summary: '当前策略能找到机会吗？',
  },
  price: {
    title: '价格回测',
    summary: '当前策略能盈利吗？',
  },
  portfolio: {
    title: '投资模拟',
    summary: '资金管理是否合理？',
  },
  decision: {
    title: '决策模拟',
    summary: '我在使用策略的时候能做出更好的决策吗？',
  },
};

export const STRATEGY_DESIGN_RUN_STEP_KEYS = new Set(
  STRATEGY_DESIGN_STEPS.filter((step) => !step.interactive).map((step) => step.key),
);

export function isDecisionStepReady(stepStatus = {}) {
  return stepStatus.enum === 'done' && stepStatus.portfolio === 'done';
}

export const STRATEGY_DESIGN_STEP_KEYS = new Set(
  STRATEGY_DESIGN_STEPS.map((s) => s.key),
);

export const STRATEGY_DESIGN_DEFAULT_STEP = 'enum';
