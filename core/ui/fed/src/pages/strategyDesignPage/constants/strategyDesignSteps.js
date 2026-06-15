/** 制定策略三步（与后端 step key / 路由 segment 对齐） */
export const STRATEGY_DESIGN_STEPS = [
  { key: 'enum', no: 1, label: '枚举机会', pathSegment: 'enum' },
  { key: 'price', no: 2, label: '价格回测', pathSegment: 'price' },
  { key: 'capital', no: 3, label: '资金模拟', pathSegment: 'capital' },
];

/** Meta 顶栏：当前步说明（标题 + 一句摘要） */
export const STRATEGY_DESIGN_STEP_INTRO = {
  enum: {
    title: '枚举机会',
    summary: '测试股票池中发现交易机会的能力',
  },
  price: {
    title: '价格回测',
    summary: '单股模拟，初步验证策略盈利表现',
  },
  capital: {
    title: '资金模拟',
    summary: '给定资金下的组合交易与收益评估',
  },
};

export const STRATEGY_DESIGN_STEP_KEYS = new Set(
  STRATEGY_DESIGN_STEPS.map((s) => s.key),
);

export const STRATEGY_DESIGN_DEFAULT_STEP = 'enum';
