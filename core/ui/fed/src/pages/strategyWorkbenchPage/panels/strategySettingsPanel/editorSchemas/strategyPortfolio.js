function parseNumber(raw) {
  if (raw === '' || raw === null || raw === undefined) return '';
  const n = Number(raw);
  return Number.isNaN(n) ? '' : n;
}

function parseIntNumber(raw) {
  if (raw === '' || raw === null || raw === undefined) return '';
  const n = Number(raw);
  if (Number.isNaN(n)) return '';
  return Math.trunc(n);
}

const ALLOCATION_MODE_META = {
  equal_capital: {
    label: '等额资金',
    tooltip: '每个新开仓机会分配相近的现金额度（总资金 ÷ 最大持股数），股数随价格浮动。',
  },
  equal_shares: {
    label: '等额股数',
    tooltip: '每个机会买入相同手数（由「每次买入手数」与市场最小交易单位决定）。',
  },
  kelly: {
    label: '凯莉公式',
    tooltip: '按凯莉公式估算建议仓位，再乘以「凯莉折扣系数」做保守缩放；需策略提供胜率/赔率等输入。',
  },
  custom: {
    label: '自定义',
    tooltip: '使用策略或引擎扩展的自定义分配逻辑（高级用法）。',
  },
};

const DEFAULT_ALLOCATION_MODE_OPTIONS = Object.entries(ALLOCATION_MODE_META).map(
  ([value, meta]) => ({ value, ...meta }),
);

function resolveAllocationModeOptions(allocationModeOptions) {
  const raw = Array.isArray(allocationModeOptions) && allocationModeOptions.length > 0
    ? allocationModeOptions
    : DEFAULT_ALLOCATION_MODE_OPTIONS;
  return raw.map((row) => {
    const meta = ALLOCATION_MODE_META[row.value];
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

export function buildStrategyPortfolioSchema(allocationModeOptions = DEFAULT_ALLOCATION_MODE_OPTIONS) {
  const modeOptions = resolveAllocationModeOptions(allocationModeOptions);

  return {
    name: 'strategyPortfolio',
    type: 'fieldGroup',
    label: '',
    children: [
      {
        name: 'initial_capital',
        type: 'number',
        label: '初始资金',
        tooltip: '资金组合账户的起始可用资金（元），用于计算仓位规模与净值曲线。',
        parse: parseNumber,
      },
      {
        name: 'allocation.max_portfolio_size',
        type: 'number',
        label: '最大同时持股数',
        tooltip: '同一时刻最多持有的股票只数；与分配模式共同决定每笔新开仓的可用额度。',
        parse: parseIntNumber,
      },
      {
        name: 'allocation.mode',
        type: 'select',
        label: '资金分配策略',
        tooltip: '有新信号开仓时，如何把账户可用资金分配到该笔交易。',
        options: modeOptions,
      },
      {
        name: 'allocation.max_weight_per_stock',
        type: 'number',
        label: '单票最大权重',
        tooltip: '单只股票市值占账户净值的上限比例（0～1），用于限制过度集中持仓。',
        parse: parseNumber,
      },
      {
        name: 'allocation.lots_per_trade',
        type: 'number',
        label: '每次买入手数',
        tooltip: '仅在「等额股数」下生效：买入手数 = 市场最小交易单位 × 本值（手数由市场规则 profile 决定）。',
        parse: parseIntNumber,
        visibleWhen: ({ values }) => values?.allocation?.mode === 'equal_shares',
      },
      {
        name: 'allocation.skip_trade_when_insufficient',
        type: 'switch',
        label: '资金不足整手时跳过开仓',
        tooltip: '开启：按计划资金买不起一整手则跳过该笔；关闭：在可用额度内尽量买满整手。',
      },
      {
        name: 'allocation.kelly_fraction',
        type: 'number',
        label: '凯莉折扣系数',
        tooltip: '仅在「凯莉公式」下生效：在理论凯莉仓位上乘以该系数（0～1），默认偏保守。',
        parse: parseNumber,
        visibleWhen: ({ values }) => values?.allocation?.mode === 'kelly',
      },
    ],
  };
}

const strategyPortfolioSchema = buildStrategyPortfolioSchema();

export default strategyPortfolioSchema;
