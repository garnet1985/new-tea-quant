function splitStockIds(text) {
  return String(text || '')
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function joinStockIds(list) {
  return Array.isArray(list) ? list.join('\n') : '';
}

function parseNumber(raw) {
  if (raw === '' || raw === null || raw === undefined) return '';
  const n = Number(raw);
  return Number.isNaN(n) ? '' : n;
}

const STRATEGY_DEFAULT = 'continuous';
const STRATEGY_KEYS = ['continuous', 'uniform', 'stratified', 'random', 'pool', 'blacklist'];
const DEFAULT_SAMPLING_STRATEGY_OPTIONS = [
  { label: '连续采样（默认）', value: 'continuous' },
  { label: '均匀采样', value: 'uniform' },
  { label: '分层采样', value: 'stratified' },
  { label: '随机采样', value: 'random' },
  { label: '指定股票池采样', value: 'pool' },
  { label: '排除黑名单采样', value: 'blacklist' },
];

export function normalizeSamplingSettings(sampling) {
  const next = sampling && typeof sampling === 'object' ? { ...sampling } : {};
  if (!next.strategy) next.strategy = STRATEGY_DEFAULT;
  if (typeof next.use_sampling !== 'boolean') {
    next.use_sampling = Boolean(next.use_sampling);
  }
  return next;
}

export function cleanupSamplingByStrategy(sampling) {
  const next = normalizeSamplingSettings(sampling);
  STRATEGY_KEYS.forEach((key) => {
    if (key !== next.strategy && Object.prototype.hasOwnProperty.call(next, key)) {
      delete next[key];
    }
  });
  if (!Object.prototype.hasOwnProperty.call(next, next.strategy)) {
    next[next.strategy] = {};
  }
  return next;
}

export function buildStrategySamplingSchema(samplingStrategyOptions = DEFAULT_SAMPLING_STRATEGY_OPTIONS) {
  return {
    name: 'strategySampling',
    type: 'fieldGroup',
    label: '',
    children: [
    {
      name: 'use_sampling',
      type: 'switch',
      label: '是否使用采样',
    },
    {
      name: 'sampling.dateRange',
      label: '时间段',
      tooltip: '不填写开始或结束日期时，表示使用默认的全部时间区间。',
      type: 'dateRange',
      startName: 'start_date',
      endName: 'end_date',
      startLabel: '开始日期',
      endLabel: '结束日期',
    },
    {
      name: 'strategy',
      type: 'select',
      label: '采样策略',
      options: Array.isArray(samplingStrategyOptions) && samplingStrategyOptions.length > 0
        ? samplingStrategyOptions
        : DEFAULT_SAMPLING_STRATEGY_OPTIONS,
    },
    {
      name: 'sampling_amount',
      type: 'number',
      label: '采样数量',
      parse: parseNumber,
    },
    {
      name: 'continuous.start_idx',
      type: 'number',
      label: '连续采样起始索引',
      description: '仅在“连续采样”模式生效',
      parse: parseNumber,
      visibleWhen: ({ values }) => values?.strategy === 'continuous',
    },
    {
      name: 'stratified.seed',
      type: 'number',
      label: '分层采样随机种子',
      parse: parseNumber,
      visibleWhen: ({ values }) => values?.strategy === 'stratified',
    },
    {
      name: 'random.seed',
      type: 'number',
      label: '随机采样随机种子',
      parse: parseNumber,
      visibleWhen: ({ values }) => values?.strategy === 'random',
    },
    {
      name: 'pool.stock_ids',
      type: 'text',
      multiline: true,
      minRows: 4,
      label: '股票池列表（每行一个，或逗号分隔）',
      visibleWhen: ({ values }) => values?.strategy === 'pool',
      format: (value) => joinStockIds(value),
      parse: (raw) => splitStockIds(raw),
    },
    {
      name: 'pool.file',
      type: 'text',
      label: '股票池文件路径（可选）',
      visibleWhen: ({ values }) => values?.strategy === 'pool',
    },
    {
      name: 'blacklist.stock_ids',
      type: 'text',
      multiline: true,
      minRows: 4,
      label: '黑名单列表（每行一个，或逗号分隔）',
      visibleWhen: ({ values }) => values?.strategy === 'blacklist',
      format: (value) => joinStockIds(value),
      parse: (raw) => splitStockIds(raw),
    },
    {
      name: 'blacklist.file',
      type: 'text',
      label: '黑名单文件路径（可选）',
      visibleWhen: ({ values }) => values?.strategy === 'blacklist',
    },
    ],
  };
}

const strategySamplingSchema = buildStrategySamplingSchema();

export default strategySamplingSchema;
