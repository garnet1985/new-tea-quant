export function normalizeMeta(rawMeta) {
  return {
    name: rawMeta?.name || '',
    description: rawMeta?.description || '',
    is_enabled: Boolean(rawMeta?.is_enabled),
  };
}

const DEFAULT_MARKET_PROFILE_OPTIONS = [
  { label: '中国A股市场规则', value: 'china_a_stock' },
];

export function buildStrategyMetaSchema(marketProfileOptions = DEFAULT_MARKET_PROFILE_OPTIONS) {
  const profileOptions = Array.isArray(marketProfileOptions) && marketProfileOptions.length > 0
    ? marketProfileOptions
    : DEFAULT_MARKET_PROFILE_OPTIONS;

  return {
    name: 'strategyMeta',
    label: '策略基本信息',
    description: '启用状态与基础数据约束',
    type: 'section',
    defaultExpanded: true,
    children: [
      {
        name: 'market_profile',
        label: '市场规则',
        description: '涨跌停、最小交易单位等由所选 market profile 决定',
        type: 'select',
        options: profileOptions,
      },
      {
        name: 'meta.is_enabled',
        label: '是否启用策略',
        description: '控制策略启用状态',
        type: 'switch',
      },
      {
        name: 'data.min_required_records',
        label: '最小K线记录数',
        description: '至少满足该历史记录条数才执行策略（默认 100）',
        type: 'number',
      },
    ],
  };
}

const strategyMetaSchema = buildStrategyMetaSchema();

export default strategyMetaSchema;
