import { formatMarketChartDateLabel } from '../dateFormat';
import {
  MARKET_MARKER_PIN_DOWN,
  MARKET_MARKER_PIN_OFFSET_DOWN,
  MARKET_MARKER_PIN_OFFSET_UP,
  MARKET_MARKER_PIN_SIZE,
  MARKET_MARKER_PIN_UP,
  marketMarkerPinStyle,
} from '../markers';
import { buildMarketChartOption } from '../buildMarketChartOption';

const MARKER_COLORS = {
  buy: '#00E5FF',
  sell: '#C62828',
  opportunity: '#00E5FF',
  target_win: '#FF9100',
  target_loss: '#B388FF',
};

const MARKER_BELOW = MARKET_MARKER_PIN_UP;
const MARKER_ABOVE = MARKET_MARKER_PIN_DOWN;

function buildCyanUpArrowStyle() {
  return marketMarkerPinStyle(MARKER_COLORS.opportunity, '0, 229, 255');
}

function buildTargetArrowStyle(type) {
  const color = type === 'target_win' ? MARKER_COLORS.target_win : MARKER_COLORS.target_loss;
  const shadow = type === 'target_win' ? '255, 145, 0' : '179, 136, 255';
  return marketMarkerPinStyle(color, shadow);
}

const MARKER_LEGEND_DEFS = {
  opportunity: {
    label: '机会',
    symbol: MARKER_BELOW,
    y: 'low',
    symbolOffset: [0, MARKET_MARKER_PIN_OFFSET_UP],
    style: buildCyanUpArrowStyle,
  },
  buy: {
    label: '买入',
    symbol: MARKER_BELOW,
    y: 'low',
    symbolOffset: [0, MARKET_MARKER_PIN_OFFSET_UP],
    style: buildCyanUpArrowStyle,
  },
  target_win: {
    label: '目标胜',
    symbol: MARKER_ABOVE,
    y: 'high',
    symbolOffset: [0, MARKET_MARKER_PIN_OFFSET_DOWN],
    style: () => buildTargetArrowStyle('target_win'),
  },
  target_loss: {
    label: '目标负',
    symbol: MARKER_ABOVE,
    y: 'high',
    symbolOffset: [0, MARKET_MARKER_PIN_OFFSET_DOWN],
    style: () => buildTargetArrowStyle('target_loss'),
  },
};

const MARKER_DETAIL_LABELS = {
  investment_id: '投资 ID',
  opportunity_id: '机会 ID',
  trigger_date: '触发日',
  chart_close: '图上收盘价',
  engine_trigger_price: '引擎记录价',
  entry_date: '入场日',
  entry_price: '入场价',
  exit_date: '出场日',
  exit_price: '出场价',
  lifecycle: '生命周期',
  result: '结果',
  exit_reason: '出场原因',
  goal_name: '目标',
  exit_ratio: '卖出比例',
  roi: '收益率',
};

/** pandas-ta 辅助列：方向/长短轨副本、加速因子、反转标记 — 不进图 */
function shouldSkipChartIndicatorSeries(row) {
  const blob = `${row?.key || ''}|${row?.label || ''}`.toLowerCase();
  if (/supertd|supertl|superts/.test(blob)) return true;
  if (/psaraf|(^|[^a-z])psarr([^a-z]|$)/.test(blob)) return true;
  return false;
}

const MARKER_DETAIL_DATE_KEYS = new Set([
  'trigger_date',
  'entry_date',
  'exit_date',
]);

function fmtPrice(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  return n.toFixed(2);
}

function uniqueDetailParts(values) {
  const out = [];
  values.forEach((value) => {
    if (value == null || value === '') return;
    const text = String(value).trim();
    if (text && !out.includes(text)) out.push(text);
  });
  return out;
}

function mergeMarkerDetail(base, extra) {
  const a = base && typeof base === 'object' ? { ...base } : {};
  const b = extra && typeof extra === 'object' ? extra : {};
  const names = uniqueDetailParts([a.goal_name, b.goal_name]);
  if (names.length) a.goal_name = names.join('、');
  const ra = Number(a.exit_ratio);
  const rb = Number(b.exit_ratio);
  if (Number.isFinite(ra) && ra > 0 && Number.isFinite(rb) && rb > 0) {
    a.exit_ratio = Math.min(1, ra + rb);
  } else if (!(Number.isFinite(ra) && ra > 0) && Number.isFinite(rb) && rb > 0) {
    a.exit_ratio = rb;
  }
  const rois = uniqueDetailParts([
    typeof a.roi === 'number' ? fmtPrice(a.roi) : a.roi,
    typeof b.roi === 'number' ? fmtPrice(b.roi) : b.roi,
  ]);
  if (rois.length) a.roi = rois.join('、');
  if (b.exit_price != null && b.exit_price !== '') a.exit_price = b.exit_price;
  const reasons = uniqueDetailParts([a.exit_reason, b.exit_reason]);
  if (reasons.length) a.exit_reason = reasons.join('、');
  return a;
}

/** 同日同类型只留一个点（两档同日止盈会叠在一起）。 */
function collapseOverlappingMarkers(markers) {
  const kept = new Map();
  const order = [];
  (markers || []).forEach((item) => {
    const type = String(item?.type || '').trim();
    const date = String(item?.date || '').trim();
    if (!type || !date) return;
    const key = `${type}|${date}`;
    if (!kept.has(key)) {
      const copy = {
        ...item,
        detail: item.detail && typeof item.detail === 'object' ? { ...item.detail } : {},
      };
      kept.set(key, copy);
      order.push(copy);
      return;
    }
    const existing = kept.get(key);
    existing.detail = mergeMarkerDetail(existing.detail, item.detail);
  });
  return order;
}

function formatMarkerDetailValue(key, value) {
  if (MARKER_DETAIL_DATE_KEYS.has(key)) {
    return formatMarketChartDateLabel(String(value));
  }
  if (key === 'exit_ratio') {
    const n = Number(value);
    if (!Number.isFinite(n)) return String(value);
    return `${(n * 100).toFixed(n * 100 % 1 === 0 ? 0 : 1)}%`;
  }
  if (typeof value === 'number') return fmtPrice(value);
  return String(value);
}

function formatMarkerTooltipHtml(marker) {
  const lines = [marker.label || marker.type || '标记'];
  const detail = marker.detail && typeof marker.detail === 'object' ? marker.detail : {};
  Object.entries(detail).forEach(([k, v]) => {
    if (v == null || v === '') return;
    const label = MARKER_DETAIL_LABELS[k] || k;
    lines.push(`${label}: ${formatMarkerDetailValue(k, v)}`);
  });
  if (marker.date) lines.unshift(formatMarketChartDateLabel(marker.date));
  return lines.filter(Boolean).join('<br/>');
}

function normalizeCandleRow(item) {
  const open = Number(item.open);
  const close = Number(item.close);
  let low = Number(item.low);
  let high = Number(item.high);
  if (![open, close, low, high].every(Number.isFinite)) return null;
  if (high < low) {
    const tmp = high;
    high = low;
    low = tmp;
  }
  const volumeRaw = item.volume;
  const volume = volumeRaw == null || volumeRaw === ''
    ? null
    : Number(volumeRaw);
  return {
    date: item.date,
    ohlc: [open, close, low, high],
    volume: Number.isFinite(volume) ? volume : null,
  };
}

/** 日期轴、K 线、指标必须同索引。 */
export function prepareAlignedChartRows(candles, indicatorSeries) {
  const dates = [];
  const candleData = [];
  const volumes = [];
  const validIndexes = [];
  (candles || []).forEach((item, index) => {
    const row = normalizeCandleRow(item);
    if (!row) return;
    validIndexes.push(index);
    dates.push(row.date);
    candleData.push(row.ohlc);
    volumes.push(row.volume);
  });
  const alignedIndicators = (indicatorSeries || []).map((row) => ({
    ...row,
    data: validIndexes.map((i) => {
      const values = Array.isArray(row.data) ? row.data : [];
      return i < values.length ? values[i] : null;
    }),
  }));
  return { dates, candleData, volumes, indicatorSeries: alignedIndicators };
}

function paneIdForIndicator(row) {
  const panel = String(row?.panel || 'overlay');
  if (panel === 'overlay') return 'price';
  if (panel === 'volume') return 'volume';
  if (panel === 'macd') {
    return row.pane_group || row.paneGroup || `macd:${row.key || 'macd'}`;
  }
  // oscillator / other sub-panes
  return row.pane_group || row.paneGroup || 'oscillator';
}

function mergeYAxis(into, from) {
  if (!from || typeof from !== 'object') return into;
  const next = { ...(into || {}) };
  if (from.min != null && next.min == null) next.min = from.min;
  if (from.max != null && next.max == null) next.max = from.max;
  if (from.scale != null && next.scale == null) next.scale = from.scale;
  return next;
}

function defaultYAxisForPane(paneId, sampleRows) {
  if (paneId === 'price' || paneId === 'volume') {
    return { scale: true };
  }
  let yAxis = { scale: true };
  (sampleRows || []).forEach((row) => {
    const conf = row.y_axis || row.yAxis;
    yAxis = mergeYAxis(yAxis, conf);
  });
  // 经典 0–100 振荡器：同 pane 内若无人声明，且全是 oscillator 无 macd，保持旧行为
  if (
    paneId === 'oscillator'
    && yAxis.min == null
    && yAxis.max == null
    && (sampleRows || []).every((row) => String(row.panel) === 'oscillator')
  ) {
    const wantsFixed = (sampleRows || []).some((row) => {
      const key = String(row.key || row.label || '').toLowerCase();
      return /^(rsi|stoch|mfi|cmo|uo|aroon)/.test(key);
    });
    if (wantsFixed || !(sampleRows || []).length) {
      yAxis.min = 0;
      yAxis.max = 100;
    }
  }
  return yAxis;
}

function heightRatiosForPanes(paneIds) {
  const ratios = new Map();
  const subs = paneIds.filter((id) => id !== 'price');
  if (subs.length === 0) {
    ratios.set('price', 0.78);
    return ratios;
  }
  // 主图至少 4× 附图，再抬高约 30% → 约 5.2×；附图等高均分
  const mainToSub = 4 * 1.3;
  const priceRatio = mainToSub / (mainToSub + subs.length);
  const subEach = 1 / (mainToSub + subs.length);
  ratios.set('price', priceRatio);
  subs.forEach((id) => ratios.set(id, subEach));
  return ratios;
}

function titleForPane(paneId, rows) {
  const id = String(paneId || '');
  if (id === 'price') return '';
  if (id === 'volume') return '成交量';
  if (id.startsWith('macd')) return 'MACD';
  if (id === 'osc:bbp') return 'BB %B';
  if (id === 'osc:bbb') return 'BB 带宽';
  if (id.startsWith('volind:')) return id.slice('volind:'.length).toUpperCase();
  if (id.startsWith('osc:')) return id.slice('osc:'.length).toUpperCase();
  const labels = [...new Set(
    (rows || []).map((row) => String(row.label || row.key || '').trim()).filter(Boolean),
  )];
  if (labels.length === 1) return labels[0];
  if (labels.length > 1) {
    const roots = [...new Set(labels.map((label) => label.split(/[\s(]/)[0]).filter(Boolean))];
    if (roots.length === 1) return roots[0];
    return labels.slice(0, 3).join(' · ');
  }
  return '副图';
}

function businessMarkersToSpecs(markers) {
  const out = [];
  collapseOverlappingMarkers(markers).forEach((item) => {
    const type = String(item?.type || '').trim();
    const def = MARKER_LEGEND_DEFS[type];
    const date = String(item?.date || '').trim();
    if (!def || !date) return;
    let y = def.y;
    if (type !== 'buy' && type !== 'opportunity' && type !== 'target_win' && type !== 'target_loss') {
      const px = Number(item?.price);
      if (Number.isFinite(px)) y = px;
    }
    out.push({
      key: type,
      label: def.label,
      date,
      paneId: 'price',
      y,
      symbol: def.symbol,
      symbolSize: MARKET_MARKER_PIN_SIZE,
      symbolOffset: def.symbolOffset,
      itemStyle: def.style(),
      tooltipHtml: formatMarkerTooltipHtml({ ...item, label: item.label || def.label }),
      tooltipKey: item.opportunity_id || `${type}|${date}`,
    });
  });
  return out;
}

/**
 * 报告 / 决策 K 线 payload → 中性 MarketChartModel。
 */
export function stockKlinePayloadToMarketChartModel(payload) {
  if (!payload || !Array.isArray(payload.candles) || payload.candles.length === 0) {
    return null;
  }
  const {
    dates,
    candleData,
    volumes,
    indicatorSeries,
  } = prepareAlignedChartRows(payload.candles, payload.indicator_series);
  if (!candleData.length) return null;

  const chartIndicators = indicatorSeries.filter((row) => !shouldSkipChartIndicatorSeries(row));
  const overlayRows = chartIndicators.filter((row) => String(row.panel || 'overlay') === 'overlay');
  const subRows = chartIndicators.filter((row) => String(row.panel || 'overlay') !== 'overlay');

  const paneOrder = ['price'];
  const hasVolume = volumes.some((v) => v != null && Number.isFinite(Number(v)));
  if (hasVolume) paneOrder.push('volume');

  const rowsByPane = new Map();
  subRows.forEach((row) => {
    const paneId = paneIdForIndicator(row);
    if (!rowsByPane.has(paneId)) rowsByPane.set(paneId, []);
    rowsByPane.get(paneId).push(row);
    if (!paneOrder.includes(paneId)) paneOrder.push(paneId);
  });

  const ratios = heightRatiosForPanes(paneOrder);
  const panes = paneOrder.map((id) => ({
    id,
    title: titleForPane(id, rowsByPane.get(id) || []),
    heightRatio: ratios.get(id) || 0.2,
    yAxis: defaultYAxisForPane(id, rowsByPane.get(id) || []),
  }));

  const series = [
    {
      type: 'candlestick',
      paneId: 'price',
      key: 'kline',
      label: 'K线',
      data: candleData,
    },
  ];

  overlayRows.forEach((row) => {
    series.push({
      type: row.kind === 'bar' ? 'bar' : 'line',
      paneId: 'price',
      key: row.key,
      label: row.label || row.key,
      color: row.kind === 'bar' && (row.color === 'signed' || row.signed) ? 'signed' : (row.color || undefined),
      data: Array.isArray(row.data) ? row.data : [],
    });
  });

  if (hasVolume) {
    series.push({
      type: 'bar',
      paneId: 'volume',
      key: 'volume',
      label: '成交量',
      color: 'candle',
      data: volumes,
    });
  }

  subRows.forEach((row) => {
    const paneId = paneIdForIndicator(row);
    const isBar = row.kind === 'bar';
    let color = row.color || undefined;
    if (isBar && (row.color === 'signed' || row.signed || !row.color)) {
      color = 'signed';
    }
    series.push({
      type: isBar ? 'bar' : 'line',
      paneId,
      key: row.key,
      label: row.label || row.key,
      color,
      data: Array.isArray(row.data) ? row.data : [],
    });
  });

  return {
    categories: dates,
    panes,
    series,
    markers: businessMarkersToSpecs(payload.markers),
    interaction: { dataZoom: true },
  };
}

/** 报告 / 决策 K 线 payload → ECharts option。 */
export function buildMarketChartOptionFromStockPayload(payload) {
  const model = stockKlinePayloadToMarketChartModel(payload);
  if (!model) return {};
  return buildMarketChartOption(model);
}
