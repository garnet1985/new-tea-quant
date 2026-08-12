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

const STRATEGY_DEFAULT = 'uniform';
const STRATEGY_KEYS = ['continuous', 'uniform', 'stratified', 'random', 'weighted', 'pool', 'blacklist'];

const SAMPLING_STRATEGY_META = {
  continuous: {
    label: '连续采样',
    tooltip: '按股票排序从某一位置起连续截取指定数量，适合固定窗口遍历。',
  },
  uniform: {
    label: '均匀采样',
    tooltip: '在候选股票中均匀间隔抽取，覆盖更广但可能跳过局部簇。',
  },
  stratified: {
    label: '分层采样',
    tooltip: '按分层规则抽样（如行业、市值桶），需配置随机种子以便复现。',
  },
  random: {
    label: '随机采样',
    tooltip: '在候选池中随机抽取指定数量；可设种子固定随机结果。',
  },
  weighted: {
    label: '加权采样',
    tooltip: '按权重抽取样本；需提供权重配置。',
  },
  pool: {
    label: '股票池',
    tooltip: '仅在您指定的股票列表（或文件）内回测。',
  },
  blacklist: {
    label: '黑名单',
    tooltip: '从默认候选池中排除列表中的股票后再抽样。',
  },
};

const DEFAULT_SAMPLING_STRATEGY_OPTIONS = Object.entries(SAMPLING_STRATEGY_META).map(
  ([value, meta]) => ({ value, ...meta }),
);

function resolveSamplingStrategyOptions(samplingStrategyOptions) {
  const raw = Array.isArray(samplingStrategyOptions) && samplingStrategyOptions.length > 0
    ? samplingStrategyOptions
    : DEFAULT_SAMPLING_STRATEGY_OPTIONS;
  return raw.map((row) => {
    const meta = SAMPLING_STRATEGY_META[row.value];
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

const whenSamplingEnabled = ({ values }) => Boolean(values?.use_sampling);

const whenSamplingEnabledAnd = (predicate) => (ctx) => (
  whenSamplingEnabled(ctx) && predicate(ctx)
);

export function normalizeSamplingSettings(sampling) {
  const next = sampling && typeof sampling === 'object' ? { ...sampling } : {};
  if (!next.strategy) next.strategy = STRATEGY_DEFAULT;
  if (typeof next.use_sampling !== 'boolean') {
    next.use_sampling = Boolean(next.use_sampling);
  }
  // 时间窗已迁至 simulation；编辑时丢掉 sampling 下遗留日期字段
  delete next.start_date;
  delete next.end_date;
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
  const strategyOptions = resolveSamplingStrategyOptions(samplingStrategyOptions);

  return {
    name: 'strategySampling',
    type: 'fieldGroup',
    label: '',
    children: [
      {
        name: 'use_sampling',
        type: 'switch',
        label: '是否使用采样',
        tooltip: '开启后按下方规则缩小回测股票池；关闭时使用全市场（或策略默认）候选池。回测时间窗在「回测设置 → 回测时间设置」中配置。',
      },
      {
        name: 'strategy',
        type: 'select',
        label: '采样策略',
        tooltip: '选择如何从候选股票中抽取本轮回测的样本。',
        options: strategyOptions,
        visibleWhen: whenSamplingEnabled,
      },
      {
        name: 'sampling_amount',
        type: 'number',
        label: '采样数量',
        tooltip: '本轮回测纳入的股票数量上限；具体截取方式由「采样策略」决定。',
        parse: parseNumber,
        visibleWhen: whenSamplingEnabled,
      },
      {
        name: 'continuous.start_idx',
        type: 'number',
        label: '连续采样起始索引',
        tooltip: '仅在「连续采样」下生效：从排序列表的第 N 只股票开始截取（从 0 起计）。',
        parse: parseNumber,
        visibleWhen: whenSamplingEnabledAnd(({ values }) => values?.strategy === 'continuous'),
      },
      {
        name: 'stratified.seed',
        type: 'number',
        label: '分层采样随机种子',
        tooltip: '仅在「分层采样」下生效：固定种子可复现分层抽样结果。',
        parse: parseNumber,
        visibleWhen: whenSamplingEnabledAnd(({ values }) => values?.strategy === 'stratified'),
      },
      {
        name: 'random.seed',
        type: 'number',
        label: '随机采样随机种子',
        tooltip: '仅在「随机采样」下生效：固定种子可复现随机抽样结果。',
        parse: parseNumber,
        visibleWhen: whenSamplingEnabledAnd(({ values }) => values?.strategy === 'random'),
      },
      {
        name: 'pool.stock_ids',
        type: 'text',
        multiline: true,
        minRows: 4,
        label: '股票池列表',
        tooltip: '每行一个股票代码，或用英文逗号分隔；与下方文件路径可配合使用。',
        visibleWhen: whenSamplingEnabledAnd(({ values }) => values?.strategy === 'pool'),
        format: (value) => joinStockIds(value),
        parse: (raw) => splitStockIds(raw),
      },
      {
        name: 'pool.file',
        type: 'text',
        label: '股票池文件路径',
        tooltip: '可选：从文本文件加载股票列表（相对 userspace 或绝对路径，依部署而定）。',
        visibleWhen: whenSamplingEnabledAnd(({ values }) => values?.strategy === 'pool'),
      },
      {
        name: 'blacklist.stock_ids',
        type: 'text',
        multiline: true,
        minRows: 4,
        label: '黑名单列表',
        tooltip: '每行一个股票代码，或用英文逗号分隔；这些股票将不参与抽样。',
        visibleWhen: whenSamplingEnabledAnd(({ values }) => values?.strategy === 'blacklist'),
        format: (value) => joinStockIds(value),
        parse: (raw) => splitStockIds(raw),
      },
      {
        name: 'blacklist.file',
        type: 'text',
        label: '黑名单文件路径',
        tooltip: '可选：从文件加载黑名单列表。',
        visibleWhen: whenSamplingEnabledAnd(({ values }) => values?.strategy === 'blacklist'),
      },
    ],
  };
}

const strategySamplingSchema = buildStrategySamplingSchema();

export default strategySamplingSchema;
