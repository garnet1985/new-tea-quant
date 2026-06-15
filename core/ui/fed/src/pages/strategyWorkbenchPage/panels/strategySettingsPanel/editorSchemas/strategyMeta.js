import { coerceMetaDescription } from '../../../../../utils/formatStrategyDescription';

export function normalizeMeta(rawMeta, rootSettings = {}) {
  const meta = rawMeta && typeof rawMeta === 'object' ? rawMeta : {};
  const root = rootSettings && typeof rootSettings === 'object' ? rootSettings : {};
  return {
    display_name: meta.display_name || '',
    description: coerceMetaDescription(meta.description),
    keywords: Array.isArray(meta.keywords) ? meta.keywords : [],
    details: meta.details && typeof meta.details === 'object' ? meta.details : { entry: [] },
    is_enabled: Boolean(root.is_enabled),
  };
}

/** 从 V2-01 settings 中取出策略说明（``meta.description``）。 */
export function extractStrategyDescription(settings) {
  if (!settings || typeof settings !== 'object') return '';
  const meta = settings.meta && typeof settings.meta === 'object' ? settings.meta : {};
  return coerceMetaDescription(meta.description);
}

/** 从 settings 中取出 ``meta.details.entry``（入场条件文案列表）。 */
export function extractStrategyEntryConditions(settings) {
  if (!settings || typeof settings !== 'object') return [];
  const meta = settings.meta && typeof settings.meta === 'object' ? settings.meta : {};
  const details = meta.details && typeof meta.details === 'object' ? meta.details : {};
  const entry = Array.isArray(details.entry) ? details.entry : [];
  return entry
    .map((item) => String(item || '').trim())
    .filter(Boolean);
}

export function extractStrategyDisplayName(settings) {
  if (!settings || typeof settings !== 'object') return '';
  const meta = settings.meta && typeof settings.meta === 'object' ? settings.meta : {};
  return String(meta.display_name || '').trim();
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
        name: 'is_enabled',
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
