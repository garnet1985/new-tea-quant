function parseNumber(raw) {
  if (raw === '' || raw === null || raw === undefined) return '';
  const n = Number(raw);
  return Number.isNaN(n) ? '' : n;
}

const TEMPLATE_DEFAULT = 'deterministic';

const DEFAULT_SIMULATION_TEMPLATE_OPTIONS = [
  { label: '确定性（收盘信号 / 次日开盘买 / 收盘卖）', value: 'deterministic' },
  { label: '极值压力（盯盘与成交均用极值近似）', value: 'extreme' },
  { label: '自定义（逐项指定盯盘与买卖价模型）', value: 'custom' },
];

const MONITOR_PRICE_OPTIONS = [
  { label: '收盘价 (close)', value: 'close' },
  { label: '极值 (extreme)', value: 'extreme' },
];

const TRADE_PRICE_OPTIONS = [
  { label: '收盘价 (close)', value: 'close' },
  { label: '开盘价 (open)', value: 'open' },
  { label: '次日开盘 (next_open)', value: 'next_open' },
  { label: '极值 (extreme)', value: 'extreme' },
];

const NO_NEXT_BAR_OPTIONS = [
  { label: '用信号日收盘价代替 (use_last_close)', value: 'use_last_close' },
  { label: '放弃该笔 (skip_trade)', value: 'skip_trade' },
  { label: '保留为未完成 (unfinished)', value: 'unfinished' },
];

const EXTREME_SAME_BAR_ORDER_OPTIONS = [
  { label: '先止损 (stop_first)', value: 'stop_first' },
  { label: '先止盈 (take_profit_first)', value: 'take_profit_first' },
  { label: '随机 (random)', value: 'random' },
];

const isCustomTemplate = (values) => (values?.template || TEMPLATE_DEFAULT) === 'custom';

export function normalizeSimulationSettings(simulation) {
  const next = simulation && typeof simulation === 'object' ? { ...simulation } : {};
  if (!next.template) {
    next.template = TEMPLATE_DEFAULT;
  }
  return next;
}

/** 非 custom 模板仅保留 template，其余由后端按模板补默认。 */
export function cleanupSimulationByTemplate(simulation) {
  const next = normalizeSimulationSettings(simulation);
  if (isCustomTemplate(next)) {
    return ensureCustomDefaults(next);
  }
  return { template: next.template };
}

function ensureCustomDefaults(simulation) {
  const next = { ...simulation };
  if (!next.monitor_price_model) next.monitor_price_model = 'close';
  if (!next.buy_price_model) next.buy_price_model = 'next_open';
  if (!next.sell_price_model) next.sell_price_model = 'close';
  if (!next.slippage || typeof next.slippage !== 'object') {
    next.slippage = { buy_bps: 0, sell_bps: 0 };
  }
  if (!next.edges || typeof next.edges !== 'object') {
    next.edges = { no_next_bar: 'use_last_close' };
  }
  if (!next.extreme_same_bar_order) {
    next.extreme_same_bar_order = 'stop_first';
  }
  return next;
}

export function buildStrategySimulationSchema(simulationTemplateOptions = DEFAULT_SIMULATION_TEMPLATE_OPTIONS) {
  const templateOptions = Array.isArray(simulationTemplateOptions) && simulationTemplateOptions.length > 0
    ? simulationTemplateOptions
    : DEFAULT_SIMULATION_TEMPLATE_OPTIONS;

  return {
    name: 'strategySimulation',
    type: 'fieldGroup',
    label: '',
    children: [
      {
        name: 'template',
        type: 'select',
        label: '回测模板',
        options: templateOptions,
      },
      {
        name: 'monitor_price_model',
        type: 'select',
        label: '盯盘价模型 (monitor_price_model)',
        description: '持仓期间用于止盈/止损/到期比较的每日价格',
        options: MONITOR_PRICE_OPTIONS,
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'buy_price_model',
        type: 'select',
        label: '买入价模型 (buy_price_model)',
        options: TRADE_PRICE_OPTIONS,
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'sell_price_model',
        type: 'select',
        label: '卖出价模型 (sell_price_model)',
        options: TRADE_PRICE_OPTIONS,
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'slippage.buy_bps',
        type: 'number',
        label: '买入滑点 (bps)',
        description: '理论买入价 × (1 + bps/10000)',
        parse: parseNumber,
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'slippage.sell_bps',
        type: 'number',
        label: '卖出滑点 (bps)',
        description: '理论卖出价 × (1 - bps/10000)',
        parse: parseNumber,
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'edges.no_next_bar',
        type: 'select',
        label: '样本末日无下一根 K 线 (edges.no_next_bar)',
        options: NO_NEXT_BAR_OPTIONS,
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'extreme_same_bar_order',
        type: 'select',
        label: '同 bar 内止损/止盈顺序',
        options: EXTREME_SAME_BAR_ORDER_OPTIONS,
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'extreme_same_bar_random_seed',
        type: 'number',
        label: '随机顺序种子（random 时）',
        parse: parseNumber,
        visibleWhen: ({ values }) => (
          isCustomTemplate(values) && values?.extreme_same_bar_order === 'random'
        ),
      },
    ],
  };
}

const strategySimulationSchema = buildStrategySimulationSchema();

export default strategySimulationSchema;
