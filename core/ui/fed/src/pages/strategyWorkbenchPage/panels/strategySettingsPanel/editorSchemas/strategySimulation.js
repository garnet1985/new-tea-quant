function parseNumber(raw) {
  if (raw === '' || raw === null || raw === undefined) return '';
  const n = Number(raw);
  return Number.isNaN(n) ? '' : n;
}

const TEMPLATE_DEFAULT = 'standard';

const SIMULATION_TEMPLATE_META = {
  standard: {
    label: '标准',
    tooltip: '日常回测默认；常见成交节奏，涨跌停不成交。不知道选什么就用这个。',
  },
  strict: {
    label: '严格',
    tooltip: '更贴近 A 股现实；在标准基础上，触发日 ST/*ST 不参与 price/capital 模拟。',
  },
  ideal: {
    label: '理想',
    tooltip: '少市场摩擦的对照组；与「标准」对比，看策略信号本身好不好。',
  },
  extreme: {
    label: '极值压力',
    tooltip: '压力测试；盯盘与成交按极值取价，结果通常更差。',
  },
  custom: {
    label: '自定义',
    tooltip: '自行配置价模型、涨跌停、ST 跳过等；熟悉执行假设时使用。',
  },
};

const DEFAULT_SIMULATION_TEMPLATE_OPTIONS = Object.entries(SIMULATION_TEMPLATE_META).map(
  ([value, meta]) => ({ value, ...meta }),
);

const DEFAULT_SKIP_INVESTMENT_WHEN_OPTIONS = [
  {
    value: 'st',
    label: 'ST',
    tooltip: '触发日处于 ST（含 SST）时，价格/资金回测跳过该笔投资；枚举机会仍保留。',
  },
  {
    value: 'star_st',
    label: '*ST',
    tooltip: '触发日处于 *ST（含 S*ST）时，价格/资金回测跳过该笔投资；枚举机会仍保留。',
  },
];

const KNOWN_SKIP_INVESTMENT_TAGS = new Set(['st', 'star_st']);

function resolveTemplateOptions(simulationTemplateOptions) {
  const raw = Array.isArray(simulationTemplateOptions) && simulationTemplateOptions.length > 0
    ? simulationTemplateOptions
    : DEFAULT_SIMULATION_TEMPLATE_OPTIONS;
  return raw.map((row) => {
    const meta = SIMULATION_TEMPLATE_META[row.value];
    if (meta) {
      return {
        value: row.value,
        label: meta.label,
        tooltip: row.tooltip || meta.tooltip,
      };
    }
    return {
      value: row.value,
      label: row.label,
      tooltip: row.tooltip || '',
    };
  });
}

const MONITOR_PRICE_OPTIONS = [
  {
    label: '收盘价',
    value: 'close',
    tooltip: '持仓期间用当日收盘价判断止盈、止损与到期等目标。',
  },
  {
    label: '极值',
    value: 'extreme',
    tooltip: '用当日最高/最低价做最不利方向的盯盘判断（压力情景）。',
  },
];

const TRADE_PRICE_OPTIONS = [
  { label: '收盘价', value: 'close', tooltip: '按信号对应 K 线的收盘价作为理论成交价。' },
  { label: '开盘价', value: 'open', tooltip: '按信号对应 K 线的开盘价作为理论成交价。' },
  {
    label: '次日开盘',
    value: 'next_open',
    tooltip: '信号确认后，在下一根 K 线开盘价成交（常见于 T+1 买入）。',
  },
  {
    label: '极值',
    value: 'extreme',
    tooltip: '按当日最高/最低价等极值近似成交，用于压力测试。',
  },
];

const NO_NEXT_BAR_OPTIONS = [
  {
    label: '用信号日收盘价代替',
    value: 'use_last_close',
    tooltip: '样本最后一根 K 线无法取得次日价时，用当日收盘价完成记账。',
  },
  {
    label: '放弃该笔',
    value: 'skip_trade',
    tooltip: '无法取得下一根 K 线时，跳过该笔买入或卖出，不记入成交。',
  },
  {
    label: '保留为未完成',
    value: 'unfinished',
    tooltip: '无法取得下一根 K 线时，将该笔标记为未完成，不强制平仓。',
  },
];

const EXTREME_SAME_BAR_ORDER_OPTIONS = [
  {
    label: '先止损',
    value: 'stop_first',
    tooltip: '同一交易日内若同时触发止损与止盈条件，优先按止损处理。',
  },
  {
    label: '先止盈',
    value: 'take_profit_first',
    tooltip: '同一交易日内若同时触发止损与止盈条件，优先按止盈处理。',
  },
  {
    label: '随机',
    value: 'random',
    tooltip: '同一交易日内同时触发时，按随机顺序处理；可配合下方种子复现结果。',
  },
];

export const isCustomSimulationTemplate = (values) => (
  (values?.template || TEMPLATE_DEFAULT) === 'custom'
);

export function normalizeSkipInvestmentWhen(raw) {
  if (!Array.isArray(raw)) return [];
  const out = [];
  raw.forEach((item) => {
    const tag = String(item || '').trim().toLowerCase();
    if (!KNOWN_SKIP_INVESTMENT_TAGS.has(tag) || out.includes(tag)) return;
    out.push(tag);
  });
  return out;
}

function resolveSkipInvestmentWhenOptions(skipInvestmentWhenOptions) {
  const raw = Array.isArray(skipInvestmentWhenOptions) && skipInvestmentWhenOptions.length > 0
    ? skipInvestmentWhenOptions
    : DEFAULT_SKIP_INVESTMENT_WHEN_OPTIONS;
  return raw.map((row) => ({
    value: row.value,
    label: row.label || row.value,
    tooltip: row.tooltip || '',
  }));
}

function mergeNestedDefaults(target, defaults) {
  const next = { ...(target && typeof target === 'object' ? target : {}) };
  if (!defaults || typeof defaults !== 'object') return next;
  if (defaults.slippage && typeof defaults.slippage === 'object') {
    next.slippage = { ...defaults.slippage, ...(next.slippage || {}) };
  }
  if (defaults.edges && typeof defaults.edges === 'object') {
    next.edges = { ...defaults.edges, ...(next.edges || {}) };
  }
  if (defaults.liquidity && typeof defaults.liquidity === 'object') {
    next.liquidity = { ...defaults.liquidity, ...(next.liquidity || {}) };
  }
  Object.keys(defaults).forEach((key) => {
    if (key === 'slippage' || key === 'edges' || key === 'liquidity') return;
    if (next[key] === undefined || next[key] === null || next[key] === '') {
      next[key] = defaults[key];
    }
  });
  return next;
}

function resolveTemplateDefaults(template, simulationTemplateProfiles) {
  const tpl = template || TEMPLATE_DEFAULT;
  const profiles = simulationTemplateProfiles && typeof simulationTemplateProfiles === 'object'
    ? simulationTemplateProfiles
    : {};
  return profiles[tpl] || profiles.standard || {};
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
    next.edges = {
      no_next_bar: 'use_last_close',
      allow_buy_at_limit_up: false,
      allow_sell_at_limit_down: false,
    };
  } else {
    if (next.edges.allow_buy_at_limit_up === undefined) {
      next.edges.allow_buy_at_limit_up = false;
    }
    if (next.edges.allow_sell_at_limit_down === undefined) {
      next.edges.allow_sell_at_limit_down = false;
    }
  }
  if (!next.extreme_same_bar_order) {
    next.extreme_same_bar_order = 'stop_first';
  }
  next.skip_investment_when = normalizeSkipInvestmentWhen(next.skip_investment_when);
  if (!next.liquidity || typeof next.liquidity !== 'object') {
    next.liquidity = { max_participation_rate: 0.1, participation_on_exceed: 'clip' };
  } else {
    if (next.liquidity.max_participation_rate === undefined
      || next.liquidity.max_participation_rate === null
      || next.liquidity.max_participation_rate === '') {
      next.liquidity.max_participation_rate = 0.1;
    }
    if (!next.liquidity.participation_on_exceed) {
      next.liquidity.participation_on_exceed = 'clip';
    }
  }
  return next;
}

const PARTICIPATION_ON_EXCEED_OPTIONS = [
  {
    label: '缩量成交',
    value: 'clip',
    tooltip: '计划股数超过当日成交量×参与率时，按上限向下取整到最小交易单位后成交。',
  },
  {
    label: '跳过',
    value: 'skip',
    tooltip: '计划股数超过参与率上限时，整笔买卖跳过。',
  },
];

export function normalizeSimulationSettings(simulation, simulationTemplateProfiles = {}) {
  const next = simulation && typeof simulation === 'object' ? { ...simulation } : {};
  if (!next.template) {
    next.template = TEMPLATE_DEFAULT;
  }
  if (isCustomSimulationTemplate(next)) {
    return ensureCustomDefaults(next);
  }
  const defaults = resolveTemplateDefaults(next.template, simulationTemplateProfiles);
  return mergeNestedDefaults(
    {
      ...next,
      skip_investment_when: normalizeSkipInvestmentWhen(defaults.skip_investment_when),
    },
    defaults,
  );
}

/** preset 展示值：合并后端 defaults；custom 用用户配置。 */
export function resolveSimulationDisplayValue(
  simulation,
  simulationTemplateProfiles = {},
) {
  return normalizeSimulationSettings(simulation, simulationTemplateProfiles);
}

/** preset 仅持久化 template + 时间窗/执行模式等块外字段；custom 保留完整细项。 */
export function cleanupSimulationByTemplate(simulation) {
  const next = simulation && typeof simulation === 'object' ? { ...simulation } : {};
  if (!next.template) {
    next.template = TEMPLATE_DEFAULT;
  }
  if (isCustomSimulationTemplate(next)) {
    return ensureCustomDefaults(next);
  }
  const out = { template: next.template };
  if (next.start_date !== undefined && next.start_date !== null && next.start_date !== '') {
    out.start_date = next.start_date;
  }
  if (next.end_date !== undefined && next.end_date !== null && next.end_date !== '') {
    out.end_date = next.end_date;
  }
  if (next.execution_mode) {
    out.execution_mode = next.execution_mode;
  }
  if (Array.isArray(next.execute_steps) && next.execute_steps.length > 0) {
    out.execute_steps = [...next.execute_steps];
  }
  if (next.retention && typeof next.retention === 'object') {
    out.retention = { ...next.retention };
  }
  return out;
}

export function buildStrategySimulationSchema(
  simulationTemplateOptions = DEFAULT_SIMULATION_TEMPLATE_OPTIONS,
  skipInvestmentWhenOptions = DEFAULT_SKIP_INVESTMENT_WHEN_OPTIONS,
) {
  const templateOptions = resolveTemplateOptions(simulationTemplateOptions);
  const skipOptions = resolveSkipInvestmentWhenOptions(skipInvestmentWhenOptions);
  const readonlyUnlessCustom = ({ values }) => !isCustomSimulationTemplate(values);

  return {
    name: 'strategySimulation',
    type: 'fieldGroup',
    label: '',
    children: [
      {
        name: 'simulation.dateRange',
        label: '回测时间窗',
        tooltip: 'enum / price / portfolio 共用的行情区间（YYYYMMDD）。开始或结束留空表示由系统按 data.json 边界推断。',
        type: 'dateRange',
        layout: 'vertical',
        startName: 'start_date',
        endName: 'end_date',
        startLabel: '开始日期',
        endLabel: '结束日期',
      },
      {
        name: 'template',
        type: 'select',
        label: '回测模板',
        tooltip: '快捷选择回测假设；除「自定义」外，下方参数只读展示模板默认值。',
        options: templateOptions,
      },
      {
        name: 'monitor_price_model',
        type: 'select',
        label: '盯盘价模型',
        tooltip: '持仓期间用于止盈、止损、到期等目标比较的每日价格口径。',
        options: MONITOR_PRICE_OPTIONS,
        readonlyWhen: readonlyUnlessCustom,
      },
      {
        name: 'buy_price_model',
        type: 'select',
        label: '买入价模型',
        tooltip: '执行买入时，从 K 线按何种价格语义取理论成交价。',
        options: TRADE_PRICE_OPTIONS,
        readonlyWhen: readonlyUnlessCustom,
      },
      {
        name: 'sell_price_model',
        type: 'select',
        label: '卖出价模型',
        tooltip: '执行卖出时，从 K 线按何种价格语义取理论成交价。',
        options: TRADE_PRICE_OPTIONS,
        readonlyWhen: readonlyUnlessCustom,
      },
      {
        name: 'slippage.buy_bps',
        type: 'number',
        label: '买入滑点',
        tooltip: '在理论买入价上叠加滑点，单位为基点（bps）；实际价 ≈ 理论价 × (1 + bps/10000)。',
        parse: parseNumber,
        readonlyWhen: readonlyUnlessCustom,
      },
      {
        name: 'slippage.sell_bps',
        type: 'number',
        label: '卖出滑点',
        tooltip: '在理论卖出价上叠加滑点，单位为基点（bps）；实际价 ≈ 理论价 × (1 - bps/10000)。',
        parse: parseNumber,
        readonlyWhen: readonlyUnlessCustom,
      },
      {
        name: 'edges.no_next_bar',
        type: 'select',
        label: '样本末日无下一根 K 线',
        tooltip: '采样区间最后一根 K 线无法取得「次日」价格时的处理方式。',
        options: NO_NEXT_BAR_OPTIONS,
        readonlyWhen: readonlyUnlessCustom,
      },
      {
        name: 'edges.allow_buy_at_limit_up',
        type: 'switch',
        label: '涨停日允许买入',
        tooltip: '关闭后，遇到涨停且无法按规则买入时将跳过该笔买入。',
        readonlyWhen: readonlyUnlessCustom,
      },
      {
        name: 'edges.allow_sell_at_limit_down',
        type: 'switch',
        label: '跌停日允许卖出',
        tooltip: '关闭后，遇到跌停且无法按规则卖出时将跳过该笔卖出。',
        readonlyWhen: readonlyUnlessCustom,
      },
      {
        name: 'liquidity.max_participation_rate',
        type: 'number',
        label: '最大参与率',
        tooltip: '单笔成交不超过买入/卖出当日 K 线成交量（股）的该比例；默认 0.1 即 10%。',
        parse: parseNumber,
        readonlyWhen: readonlyUnlessCustom,
      },
      {
        name: 'liquidity.participation_on_exceed',
        type: 'select',
        label: '超参与率时',
        tooltip: '计划股数超过当日成交量×参与率时的处理方式。',
        options: PARTICIPATION_ON_EXCEED_OPTIONS,
        readonlyWhen: readonlyUnlessCustom,
      },
      {
        name: 'skip_investment_when',
        type: 'checkboxGroup',
        label: '跳过投资机会如果股票是：',
        tooltip:
          '勾选后，价格/资金回测在触发日处于对应股票状态时跳过该笔投资；枚举机会仍会保留。退市不可勾选（无新 K 线机会）。',
        options: skipOptions,
        readonlyWhen: readonlyUnlessCustom,
      },
      {
        name: 'extreme_same_bar_order',
        type: 'select',
        label: '同 bar 内止损/止盈顺序',
        tooltip: '使用极值盯盘且同一交易日内可能同时触发止损与止盈时的优先顺序。',
        options: EXTREME_SAME_BAR_ORDER_OPTIONS,
        readonlyWhen: readonlyUnlessCustom,
      },
      {
        name: 'extreme_same_bar_random_seed',
        type: 'number',
        label: '随机顺序种子',
        tooltip: '当顺序选「随机」时填写，用于固定随机结果以便复现回测。',
        parse: parseNumber,
        readonlyWhen: ({ values }) => (
          !isCustomSimulationTemplate(values) || values?.extreme_same_bar_order !== 'random'
        ),
      },
    ],
  };
}

const strategySimulationSchema = buildStrategySimulationSchema();

export default strategySimulationSchema;
