export const MAX_SERIES = 6;

/** 展示：中文（英文值） */
export function zhEnLabel(zh, en) {
  const name = String(zh || '').trim();
  const code = String(en || '').trim();
  if (name && code) return `${name} (${code})`;
  return name || code || '';
}

/** 数据契约选项：显示名 (data_key) */
export function formatDataContractLabel(contractOrKey, displayName = '') {
  if (contractOrKey && typeof contractOrKey === 'object') {
    const key = String(contractOrKey.key || '').trim();
    const name = String(contractOrKey.display_name || '').trim();
    return zhEnLabel(name || key, name && name !== key ? key : '');
  }
  const key = String(contractOrKey || '').trim();
  const name = String(displayName || '').trim();
  return zhEnLabel(name || key, name && name !== key ? key : '');
}

export function findDataContractOption(ref, dataKeyOptions = []) {
  const key = String(ref || '').trim();
  if (!key || !Array.isArray(dataKeyOptions)) return null;
  return dataKeyOptions.find((o) => o.key === key) || null;
}

export const NORMALIZE_OPTIONS = [
  { value: 'zscore', label: zhEnLabel('标准化', 'zscore') },
  { value: 'minmax', label: zhEnLabel('最大最小归一化', 'minmax') },
  { value: 'index_100', label: zhEnLabel('指数基准 100', 'index_100') },
  { value: 'none', label: zhEnLabel('不归一', 'none') },
];

export const FILL_OPTIONS = [
  { value: 'none', label: zhEnLabel('不填充', 'none') },
  { value: 'ffill', label: zhEnLabel('向前填充', 'ffill') },
];

export const TRANSFORM_OPTIONS = [
  { value: 'none', label: zhEnLabel('无变换', 'none') },
  { value: 'returns', label: zhEnLabel('收益率', 'returns') },
];

export const LAYER_OPTIONS = [
  { value: 'portfolio', label: zhEnLabel('组合', 'portfolio') },
  { value: 'price', label: zhEnLabel('单票', 'price') },
];

/** layer → 允许的 metric（与后端 STRATEGY_SIM_LAYER_METRICS 对齐） */
export const LAYER_METRICS = {
  portfolio: [{ value: 'equity', label: zhEnLabel('净值', 'equity') }],
  price: [{ value: 'cum_exit_roi', label: zhEnLabel('累计出场收益', 'cum_exit_roi') }],
};

function labelFromOptions(options, value, fallback = '') {
  const key = String(value || '').trim();
  const hit = (options || []).find((o) => o.value === key);
  if (hit?.label) return hit.label;
  return fallback || key || '—';
}

export function getNormalizeLabel(value) {
  return labelFromOptions(NORMALIZE_OPTIONS, value);
}

export function getFillLabel(value) {
  return labelFromOptions(FILL_OPTIONS, value);
}

export const COMMON_FIELDS = ['close', 'open', 'high', 'low', 'volume', 'amount'];

export function emptyDataKeySeries() {
  return {
    source: 'data_key',
    data_key: '',
    field: 'close',
    entity_id: '',
    label: '',
    transform: 'none',
  };
}

export function emptyStrategySimSeries() {
  return {
    source: 'strategy_sim',
    strategy_key: '',
    version: 'latest',
    layer: 'portfolio',
    metric: 'equity',
    entity_id: '',
    label: '',
    transform: 'returns',
  };
}

export function emptySettings(key = '') {
  return {
    meta: {
      key: String(key || '').trim(),
      display_name: String(key || '').trim(),
    },
    series: [emptyDataKeySeries()],
    range: { start_date: '', end_date: '' },
    normalize: 'zscore',
    fill: 'none',
    analyze: true,
  };
}

export function normalizeSeriesItem(raw) {
  const item = raw && typeof raw === 'object' ? raw : {};
  const source = String(item.source || '').trim()
    || (item.strategy_key || item.strategy || item.layer ? 'strategy_sim' : 'data_key');
  if (source === 'strategy_sim') {
    const layer = String(item.layer || 'portfolio').trim() || 'portfolio';
    const metrics = LAYER_METRICS[layer] || LAYER_METRICS.portfolio;
    const metricRaw = String(item.metric || '').trim();
    const metric = metrics.some((m) => m.value === metricRaw)
      ? metricRaw
      : metrics[0].value;
    return {
      source: 'strategy_sim',
      strategy_key: String(item.strategy_key || item.strategy || '').trim(),
      version: String(item.version || 'latest').trim() || 'latest',
      layer,
      metric,
      entity_id: layer === 'portfolio' ? '' : String(item.entity_id || '').trim(),
      label: String(item.label || '').trim(),
      transform: String(item.transform || 'returns').trim() || 'returns',
    };
  }
  return {
    source: 'data_key',
    data_key: String(item.data_key || '').trim(),
    field: String(item.field || 'close').trim() || 'close',
    entity_id: String(item.entity_id || '').trim(),
    label: String(item.label || '').trim(),
    transform: String(item.transform || 'none').trim() || 'none',
  };
}

export function normalizeSettings(raw, fallbackKey = '') {
  const settings = raw && typeof raw === 'object' ? raw : {};
  const meta = settings.meta && typeof settings.meta === 'object' ? settings.meta : {};
  const key = String(meta.key || fallbackKey || '').trim();
  const seriesRaw = Array.isArray(settings.series) ? settings.series : [];
  const range = settings.range && typeof settings.range === 'object' ? settings.range : {};
  return {
    meta: {
      key,
      display_name: String(meta.display_name || '').trim() || key,
    },
    series: (seriesRaw.length ? seriesRaw : [emptyDataKeySeries()]).map(normalizeSeriesItem),
    range: {
      start_date: String(range.start_date || '').trim(),
      end_date: String(range.end_date || '').trim(),
    },
    normalize: String(settings.normalize || 'zscore').trim() || 'zscore',
    fill: String(settings.fill || 'none').trim() || 'none',
    analyze: settings.analyze !== false,
  };
}

/** 用 key / path 在策略目录里找一项。 */
export function findStrategyOption(ref, strategyOptions = []) {
  const r = String(ref || '').trim();
  if (!r || !Array.isArray(strategyOptions)) return null;
  return strategyOptions.find((o) => (
    o.key === r || o.path === r || o.id === r
  )) || null;
}

/**
 * 摘要卡片上的策略身份：优先 display_name（短且可读）；
 * 否则短 key；再否则 path 末段。settings 里常写 path。
 */
export function resolveStrategyLabelForDisplay(ref, strategyOptions = []) {
  const raw = String(ref || '').trim();
  if (!raw) return '';
  const hit = findStrategyOption(raw, strategyOptions);
  const displayName = String(hit?.display_name || '').trim();
  if (displayName) return displayName;
  const key = String(hit?.key || '').trim();
  // key 若仍是 path（含 /），取末段
  if (key && !key.includes('/')) return key;
  if (key && key.includes('/')) {
    const parts = key.split('/').filter(Boolean);
    return parts[parts.length - 1] || key;
  }
  if (raw.includes('/')) {
    const parts = raw.split('/').filter(Boolean);
    return parts[parts.length - 1] || raw;
  }
  return raw;
}

/**
 * 摘要副行：与契约源同 pattern——``身份 · 细节``。
 * 契约：``显示名 (data_key) · entity.field``；策略：``display_name · layer.metric``。
 */
export function previewWho(item, strategyOptions = [], dataKeyOptions = []) {
  if (!item || typeof item !== 'object') return '（未配置）';
  if (item.source === 'strategy_sim') {
    const label = resolveStrategyLabelForDisplay(
      item.strategy_key || item.strategy,
      strategyOptions,
    );
    const layer = String(item.layer || '').trim() || '?';
    const metric = String(item.metric || '').trim() || '?';
    const layerLabel = labelFromOptions(LAYER_OPTIONS, layer, layer);
    const metrics = LAYER_METRICS[layer] || [];
    const metricLabel = labelFromOptions(metrics, metric, metric);
    const detail = item.entity_id
      ? `${layerLabel} · ${metricLabel} · ${item.entity_id}`
      : `${layerLabel} · ${metricLabel}`;
    if (label && detail) return `${label} · ${detail}`;
    return label || detail || '（未配置）';
  }
  const dataKey = String(item.data_key || '').trim();
  const contract = findDataContractOption(dataKey, dataKeyOptions);
  const contractLabel = formatDataContractLabel(contract || dataKey);
  const field = String(item.field || '').trim();
  const entityId = String(item.entity_id || '').trim();
  if (contractLabel && entityId && field) return `${contractLabel} · ${entityId}.${field}`;
  if (contractLabel && field) return `${contractLabel} · ${field}`;
  return contractLabel || field || '（未配置）';
}

const CHART_LEGEND_TEXT = {
  color: 'rgba(255, 255, 255, 0.78)',
  fontSize: 12,
};

const CHART_AXIS_LABEL = {
  color: 'rgba(255, 255, 255, 0.58)',
  fontSize: 11,
};

const CHART_SPLIT_LINE = {
  lineStyle: { color: 'rgba(255, 255, 255, 0.08)', width: 1 },
};

const CHART_TOOLTIP = {
  backgroundColor: 'rgba(14, 14, 22, 0.94)',
  borderColor: 'rgba(255, 255, 255, 0.12)',
  borderWidth: 1,
  textStyle: {
    color: 'rgba(255, 255, 255, 0.84)',
    fontSize: 12,
  },
};

const NORMALIZE_AXIS_NAME = {
  zscore: '标准化值 (z-score)',
  minmax: '归一化值 (0–1)',
  index_100: '指数基准 (=100)',
  none: '原始值',
};

export function buildChartOption(chart, { normalize = 'zscore' } = {}) {
  const seriesList = Array.isArray(chart?.series) ? chart.series : [];
  if (!seriesList.length) return null;
  const dates = Array.isArray(chart?.calendar) && chart.calendar.length
    ? chart.calendar
    : (seriesList[0]?.points || []).map((p) => p.date);
  const yName = NORMALIZE_AXIS_NAME[normalize] || '归一化值';
  return {
    tooltip: { trigger: 'axis', ...CHART_TOOLTIP },
    legend: {
      type: 'scroll',
      top: 0,
      textStyle: CHART_LEGEND_TEXT,
      pageTextStyle: { color: 'rgba(255, 255, 255, 0.55)' },
      data: seriesList.map((s) => String(s.label || s.id || '')),
    },
    grid: { left: 56, right: 16, top: 44, bottom: 36 },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false,
      axisLabel: CHART_AXIS_LABEL,
      axisLine: { lineStyle: { color: 'rgba(255, 255, 255, 0.14)' } },
    },
    yAxis: {
      type: 'value',
      scale: true,
      name: yName,
      nameTextStyle: {
        color: 'rgba(255, 255, 255, 0.62)',
        fontSize: 11,
        padding: [0, 0, 0, 8],
      },
      axisLabel: CHART_AXIS_LABEL,
      splitLine: CHART_SPLIT_LINE,
      axisLine: { show: false },
    },
    series: seriesList.map((s) => {
      const byDate = new Map(
        (s.points || []).map((p) => [String(p.date || ''), p.norm]),
      );
      const data = dates.map((d) => {
        const v = byDate.get(String(d));
        return v == null || v === '' ? null : Number(v);
      });
      const nonNull = data.filter((v) => v != null && Number.isFinite(v)).length;
      // LPR 等低频序列：日历上大多是空洞；不连线、不画点时图例有色但看不见曲线
      const sparse = nonNull > 0 && nonNull / Math.max(dates.length, 1) < 0.35;
      return {
        name: String(s.label || s.id || ''),
        type: 'line',
        showSymbol: sparse,
        symbolSize: sparse ? 5 : 0,
        connectNulls: sparse,
        step: sparse ? 'end' : false,
        data,
      };
    }),
  };
}
