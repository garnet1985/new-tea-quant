function parseNumber(raw) {
  if (raw === '' || raw === null || raw === undefined) return '';
  const n = Number(raw);
  return Number.isNaN(n) ? '' : n;
}

const TEMPLATE_DEFAULT = 'deterministic';

const SIMULATION_TEMPLATE_META = {
  deterministic: {
    label: '确定性',
    tooltip:
      '收盘确认信号，次日开盘买入、收盘卖出；盯盘用收盘价。系统默认预设，偏乐观。',
  },
  extreme: {
    label: '极值压力',
    tooltip:
      '盯盘与成交均按当日最高/最低价等极值近似，用于压力测试，结果通常更保守。',
  },
  custom: {
    label: '自定义',
    tooltip:
      '逐项指定盯盘价、买卖价、滑点与涨跌停等规则；仅在此模式下可改细项。',
  },
};

const DEFAULT_SIMULATION_TEMPLATE_OPTIONS = Object.entries(SIMULATION_TEMPLATE_META).map(
  ([value, meta]) => ({ value, ...meta }),
);

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
    next.edges = {
      no_next_bar: 'use_last_close',
      allow_buy_at_limit_up: true,
      allow_sell_at_limit_down: true,
    };
  } else {
    if (next.edges.allow_buy_at_limit_up === undefined) {
      next.edges.allow_buy_at_limit_up = true;
    }
    if (next.edges.allow_sell_at_limit_down === undefined) {
      next.edges.allow_sell_at_limit_down = true;
    }
  }
  if (!next.extreme_same_bar_order) {
    next.extreme_same_bar_order = 'stop_first';
  }
  return next;
}

export function buildStrategySimulationSchema(simulationTemplateOptions = DEFAULT_SIMULATION_TEMPLATE_OPTIONS) {
  const templateOptions = resolveTemplateOptions(simulationTemplateOptions);

  return {
    name: 'strategySimulation',
    type: 'fieldGroup',
    label: '',
    children: [
      {
        name: 'template',
        type: 'select',
        label: '回测模板',
        tooltip: '选择回测如何取价、成交与边角处理；除「自定义」外，细项由预设锁定。',
        options: templateOptions,
      },
      {
        name: 'monitor_price_model',
        type: 'select',
        label: '盯盘价模型',
        tooltip: '持仓期间用于止盈、止损、到期等目标比较的每日价格口径。',
        options: MONITOR_PRICE_OPTIONS,
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'buy_price_model',
        type: 'select',
        label: '买入价模型',
        tooltip: '执行买入时，从 K 线按何种价格语义取理论成交价。',
        options: TRADE_PRICE_OPTIONS,
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'sell_price_model',
        type: 'select',
        label: '卖出价模型',
        tooltip: '执行卖出时，从 K 线按何种价格语义取理论成交价。',
        options: TRADE_PRICE_OPTIONS,
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'slippage.buy_bps',
        type: 'number',
        label: '买入滑点',
        tooltip: '在理论买入价上叠加滑点，单位为基点（bps）；实际价 ≈ 理论价 × (1 + bps/10000)。',
        parse: parseNumber,
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'slippage.sell_bps',
        type: 'number',
        label: '卖出滑点',
        tooltip: '在理论卖出价上叠加滑点，单位为基点（bps）；实际价 ≈ 理论价 × (1 - bps/10000)。',
        parse: parseNumber,
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'edges.no_next_bar',
        type: 'select',
        label: '样本末日无下一根 K 线',
        tooltip: '采样区间最后一根 K 线无法取得「次日」价格时的处理方式。',
        options: NO_NEXT_BAR_OPTIONS,
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'edges.allow_buy_at_limit_up',
        type: 'switch',
        label: '涨停日允许买入',
        tooltip: '关闭后，遇到涨停且无法按规则买入时将跳过该笔买入。',
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'edges.allow_sell_at_limit_down',
        type: 'switch',
        label: '跌停日允许卖出',
        tooltip: '关闭后，遇到跌停且无法按规则卖出时将跳过该笔卖出。',
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'extreme_same_bar_order',
        type: 'select',
        label: '同 bar 内止损/止盈顺序',
        tooltip: '使用极值盯盘且同一交易日内可能同时触发止损与止盈时的优先顺序。',
        options: EXTREME_SAME_BAR_ORDER_OPTIONS,
        visibleWhen: ({ values }) => isCustomTemplate(values),
      },
      {
        name: 'extreme_same_bar_random_seed',
        type: 'number',
        label: '随机顺序种子',
        tooltip: '当顺序选「随机」时填写，用于固定随机结果以便复现回测。',
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
