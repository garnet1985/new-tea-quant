/** 执行面板 Accordion 与三层步骤说明 */

export const EXECUTION_PANEL_TITLE = '执行面板';

export const EXECUTION_PANEL_TOOLTIP =
  '使用左边的参数和设置来执行三层回测';

export const EXEC_STEP_ENUM_TOOLTIP =
  '枚举机会：在当前策略与样本范围内，列出历史上所有满足条件的交易机会，用于衡量策略发现机会的能力。';

export const EXEC_STEP_PRICE_TOOLTIP =
  '价格回测：对历史样本中的每笔机会按单股买卖规则回测，衡量价格波动带来的盈亏，用于初步评估策略对个股的整体盈利能力。';

export const EXEC_STEP_PORTFOLIO_TOOLTIP =
  '资金模拟：建立虚拟账户与仓位，按当前资金管理规则在历史样本中模拟成交，最接近实盘的一层，用于评估策略执行能力与收益率。';
