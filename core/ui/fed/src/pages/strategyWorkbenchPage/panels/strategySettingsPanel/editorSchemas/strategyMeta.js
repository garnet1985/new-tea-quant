export function normalizeMeta(rawMeta) {
  return {
    name: rawMeta?.name || '',
    description: rawMeta?.description || '',
    is_enabled: Boolean(rawMeta?.is_enabled),
  };
}

/** 从 V2-01 settings / 列表项中取出策略说明（``meta.description`` 或根级 ``description``）。 */
export function extractStrategyDescription(settings) {
  if (!settings || typeof settings !== 'object') return '';
  const meta = settings.meta && typeof settings.meta === 'object'
    ? settings.meta
    : {
      name: settings.name,
      description: settings.description,
      is_enabled: settings.is_enabled,
    };
  return normalizeMeta(meta).description.trim();
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
    label: '基本设定',
    type: 'section',
    defaultExpanded: true,
    children: [
      {
        name: 'meta.is_enabled',
        label: '策略启用开关',
        tooltip: '是否启用该策略：启用的策略可以在扫描中使用',
        type: 'switch',
      },
      {
        name: 'market_profile',
        label: '市场规则',
        tooltip: '选择使用哪种市场的交易规则进行回测',
        type: 'select',
        options: profileOptions,
      },
    ],
  };
}

const strategyMetaSchema = buildStrategyMetaSchema();

export default strategyMetaSchema;
