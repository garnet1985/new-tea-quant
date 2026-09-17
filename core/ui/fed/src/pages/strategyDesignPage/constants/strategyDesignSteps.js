/** 制定策略四步。前三步对齐后端 WorkbenchStep；第四步决策模拟是交互对局，不走 simulate()。 */
export const STRATEGY_DESIGN_STEPS = [
  {
    key: 'enum',
    no: 1,
    label: '枚举机会',
    executionPanelTitle: '枚举所有机会',
    pathSegment: 'enum',
  },
  {
    key: 'price',
    no: 2,
    label: '价格回测',
    executionPanelTitle: '单股价格回测',
    pathSegment: 'price',
  },
  {
    key: 'portfolio',
    no: 3,
    label: '投资模拟',
    executionPanelTitle: '模拟投资组合',
    pathSegment: 'portfolio',
  },
  {
    key: 'decision',
    no: 4,
    label: '决策模拟',
    executionPanelTitle: '决策模拟',
    pathSegment: 'decision',
    interactive: true,
    requires: ['enum', 'portfolio'],
  },
];

/** Meta 顶栏：当前步说明（标题 + 一句摘要） */
export const STRATEGY_DESIGN_STEP_INTRO = {
  enum: {
    title: '枚举机会',
    summary: '测试股票池中发现交易机会的数量与分布',
  },
  price: {
    title: '价格回测',
    summary: '模拟股票样本中单只股票对当前策略的普遍表现',
  },
  portfolio: {
    title: '投资模拟',
    summary: '探索资金管理策略在实盘中的表现',
  },
  decision: {
    title: '决策模拟',
    summary: '模拟当前策略下的实盘做决策过程',
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
