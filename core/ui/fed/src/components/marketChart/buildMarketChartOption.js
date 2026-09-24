import { formatMarketChartDateLabel } from './dateFormat';
import {
  MARKET_CANDLE_DOWN_COLOR,
  MARKET_CANDLE_UP_COLOR,
  MARKET_CHART_AXIS_LABEL_SM,
  MARKET_CHART_AXIS_LINE,
  MARKET_CHART_BAR_NEG,
  MARKET_CHART_BAR_POS,
  MARKET_CHART_GRID_LEFT,
  MARKET_CHART_GRID_RIGHT,
  MARKET_CHART_LEGEND_TEXT,
  MARKET_CHART_PANEL_DIVIDER,
  MARKET_CHART_SPLIT_LINE,
  MARKET_CHART_SUB_PANE_BG,
  MARKET_CHART_TOOLTIP,
} from './theme';

const DEFAULT_ZOOM_WINDOW = 180;
const GRID_LEFT = MARKET_CHART_GRID_LEFT;
const GRID_RIGHT = MARKET_CHART_GRID_RIGHT;
/** 图例占位；附图紧挨排列，只用 grid 细边框分隔，不再画黑色缝 */
const LEGEND_TOP_PAD = 12;
const BOTTOM_PAD = 11;
const PANE_GAP = 2;

function fmtNum(value, digits = 2) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  return n.toFixed(digits);
}

/** 成交量等大数：3.2k / 1.2万，避免 3000.00 挤烂左轴 */
function fmtCompactAxis(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  const abs = Math.abs(n);
  if (abs >= 1e8) return `${(n / 1e8).toFixed(abs >= 1e9 ? 1 : 2)}亿`;
  if (abs >= 1e4) return `${(n / 1e4).toFixed(abs >= 1e5 ? 1 : 2)}万`;
  if (abs >= 1000) return `${(n / 1000).toFixed(1)}k`;
  if (Number.isInteger(n) || Math.abs(n - Math.round(n)) < 1e-6) return String(Math.round(n));
  return n.toFixed(2);
}

function initialZoomRange(length) {
  if (length <= DEFAULT_ZOOM_WINDOW) {
    return { start: 0, end: 100 };
  }
  const start = Math.max(0, 100 - Math.round((DEFAULT_ZOOM_WINDOW / length) * 100));
  return { start, end: 100 };
}

function buildGrids(panes) {
  const totalRatio = panes.reduce((sum, p) => sum + (Number(p.heightRatio) || 0), 0) || 1;
  const gap = panes.length > 1 ? PANE_GAP : 0;
  const usable = 100 - LEGEND_TOP_PAD - BOTTOM_PAD - gap * Math.max(0, panes.length - 1);
  let cursor = LEGEND_TOP_PAD;
  return panes.map((pane, index) => {
    const ratio = (Number(pane.heightRatio) || 0) / totalRatio;
    const height = usable * ratio;
    const grid = {
      left: GRID_LEFT,
      right: GRID_RIGHT,
      top: `${cursor}%`,
      height: `${height}%`,
      containLabel: false,
    };
    if (index > 0) {
      // 仅顶边作分隔线，避免整框四边 + 邻接顶边叠出「双线 / 粗黑缝」观感
      grid.show = true;
      grid.borderWidth = 0;
      grid.backgroundColor = MARKET_CHART_SUB_PANE_BG;
      grid.borderColor = 'transparent';
    }
    cursor += height + gap;
    return grid;
  });
}

/** 主图顶边 + 每格底边（相邻只画一条，不叠双线）。 */
function buildPanelDividers(panes, grids) {
  if (!grids.length) return undefined;
  const graphics = [];
  const pushHLine = (topPct) => {
    if (!Number.isFinite(topPct)) return;
    graphics.push({
      type: 'rect',
      left: GRID_LEFT,
      right: GRID_RIGHT,
      top: `${topPct}%`,
      z: 4,
      silent: true,
      shape: { x: 0, y: 0, width: 4000, height: 1 },
      style: { fill: MARKET_CHART_PANEL_DIVIDER },
    });
  };

  const firstTop = parseFloat(String(grids[0].top));
  pushHLine(firstTop);

  grids.forEach((grid) => {
    const top = parseFloat(String(grid.top));
    const height = parseFloat(String(grid.height));
    if (!Number.isFinite(top) || !Number.isFinite(height)) return;
    pushHLine(top + height);
  });

  return graphics.length ? graphics : undefined;
}

function buildPaneTitleGraphics(panes, grids) {
  const graphics = [];
  panes.forEach((pane, index) => {
    const title = String(pane?.title || '').trim();
    if (!title || index === 0) return;
    const top = parseFloat(String(grids[index]?.top));
    if (!Number.isFinite(top)) return;
    graphics.push({
      type: 'text',
      left: GRID_LEFT + 6,
      top: `${top + 0.6}%`,
      z: 10,
      silent: true,
      style: {
        text: title,
        fill: 'rgba(255,255,255,0.72)',
        fontSize: 11,
        fontWeight: 600,
        textAlign: 'left',
        textVerticalAlign: 'top',
      },
    });
  });
  return graphics;
}

function resolveYAxisOption(pane) {
  const conf = pane?.yAxis && typeof pane.yAxis === 'object' ? pane.yAxis : {};
  const paneId = String(pane?.id || '');
  const isVolume = paneId === 'volume';
  const isPrice = paneId === 'price';
  const axis = {
    scale: conf.scale !== false,
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: {
      ...MARKET_CHART_AXIS_LABEL_SM,
      formatter: isVolume ? (v) => fmtCompactAxis(v) : (v) => fmtNum(v),
    },
    splitLine: {
      ...MARKET_CHART_SPLIT_LINE,
      show: isPrice || paneId.startsWith('macd') || paneId === 'oscillator' || paneId.startsWith('osc:'),
    },
    splitNumber: isVolume ? 2 : 3,
  };

  const fixedMin = conf.min != null && conf.min !== 'data' ? Number(conf.min) : null;
  const fixedMax = conf.max != null && conf.max !== 'data' ? Number(conf.max) : null;
  const hasFixed = Number.isFinite(fixedMin) && Number.isFinite(fixedMax);

  if (hasFixed) {
    // 固定量程（如 RSI 0–100）留一点边，避免贴顶
    const pad = Math.max((fixedMax - fixedMin) * 0.04, 1);
    axis.min = fixedMin - pad;
    axis.max = fixedMax + pad;
    return axis;
  }

  if (!isPrice && !isVolume) {
    // 数据自适应轴：按可见区间留 8% 边距，避免 %B / ATR 等顶穿边框
    axis.min = (extent) => {
      const span = extent.max - extent.min;
      const pad = span > 1e-9 ? span * 0.08 : Math.max(Math.abs(extent.max) * 0.08, 0.05);
      return extent.min - pad;
    };
    axis.max = (extent) => {
      const span = extent.max - extent.min;
      const pad = span > 1e-9 ? span * 0.08 : Math.max(Math.abs(extent.max) * 0.08, 0.05);
      return extent.max + pad;
    };
    return axis;
  }

  if (conf.min != null && conf.min !== 'data') axis.min = conf.min;
  if (conf.max != null && conf.max !== 'data') axis.max = conf.max;
  return axis;
}

function buildCandleLookupFromSeries(categories, candleData) {
  const byDate = new Map();
  (categories || []).forEach((date, index) => {
    const row = candleData?.[index];
    if (!Array.isArray(row) || row.length < 4) return;
    const [open, close, low, high] = row.map((v) => Number(v));
    if (![open, close, low, high].every(Number.isFinite)) return;
    byDate.set(String(date), { open, close, low, high });
  });
  return byDate;
}

function resolveMarkerY(marker, candleByDate) {
  const date = String(marker?.date || '').trim();
  const y = marker?.y;
  if (typeof y === 'number' && Number.isFinite(y)) return y;
  const bar = candleByDate.get(date);
  if (!bar) return null;
  if (y === 'low') return bar.low;
  if (y === 'high') return bar.high;
  return null;
}

function buildMarkerScatterSeries(markers, categories, candleByDate, paneIndexById) {
  const byKey = new Map();
  (markers || []).forEach((item) => {
    const key = String(item?.key || '').trim();
    const date = String(item?.date || '').trim();
    const paneId = String(item?.paneId || 'price');
    const paneIndex = paneIndexById.get(paneId);
    if (!key || !date || paneIndex == null) return;
    const y = resolveMarkerY(item, candleByDate);
    if (y == null) return;
    if (!byKey.has(key)) {
      byKey.set(key, {
        key,
        label: item.label || key,
        symbol: item.symbol,
        symbolSize: item.symbolSize,
        itemStyle: item.itemStyle,
        paneIndex,
        data: [],
      });
    }
    byKey.get(key).data.push({
      value: [date, y],
      symbolOffset: item.symbolOffset || [0, 0],
      _markerMeta: item,
    });
  });

  return [...byKey.values()]
    .filter((row) => row.data.length > 0)
    .map((row) => ({
      name: row.label,
      type: 'scatter',
      xAxisIndex: row.paneIndex,
      yAxisIndex: row.paneIndex,
      data: row.data,
      symbol: row.symbol,
      symbolSize: row.symbolSize,
      itemStyle: row.itemStyle,
      tooltip: { show: false },
      legendHoverLink: false,
      clip: false,
      z: 12,
      encode: { x: 0, y: 1 },
    }));
}

function colorizeVolumeBars(values, candleData) {
  return (values || []).map((raw, index) => {
    const n = Number(raw);
    if (!Number.isFinite(n)) return null;
    const ohlc = candleData?.[index];
    const open = Number(ohlc?.[0]);
    const close = Number(ohlc?.[1]);
    const up = Number.isFinite(open) && Number.isFinite(close) ? close >= open : true;
    return {
      value: n,
      itemStyle: {
        color: up ? MARKET_CANDLE_UP_COLOR : MARKET_CANDLE_DOWN_COLOR,
        opacity: 0.72,
      },
    };
  });
}

function colorizeSignedBars(values) {
  return (values || []).map((raw) => {
    const n = Number(raw);
    if (!Number.isFinite(n)) return null;
    return {
      value: n,
      itemStyle: {
        color: n < 0 ? MARKET_CHART_BAR_NEG : MARKET_CHART_BAR_POS,
        opacity: 0.85,
      },
    };
  });
}

function readCandlestickOHLC(param, candleByDate, candleData) {
  if (param?.seriesType !== 'candlestick') return null;

  const dateKey = String(param.axisValue ?? param.name ?? '').trim();
  if (dateKey && candleByDate?.has(dateKey)) {
    return candleByDate.get(dateKey);
  }

  const idx = Number(param.dataIndex);
  if (Number.isInteger(idx) && idx >= 0 && Array.isArray(candleData?.[idx])) {
    const [open, close, low, high] = candleData[idx].map((v) => Number(v));
    if ([open, close, low, high].every(Number.isFinite)) {
      return { open, close, low, high };
    }
  }

  let raw = param.value;
  if (!Array.isArray(raw)) raw = param.data;
  if (!Array.isArray(raw) || raw.length < 4) return null;
  const nums = (raw.length >= 5 && Number.isInteger(raw[0]) && raw[0] < 100000
    ? raw.slice(1, 5)
    : raw.slice(0, 4)
  ).map((v) => Number(v));
  if (nums.some((v) => !Number.isFinite(v))) return null;
  const [open, close, low, high] = nums;
  return { open, close, low, high };
}

function buildSeriesFromSpec(spec, paneIndexById, candleData) {
  const paneId = String(spec?.paneId || '');
  const paneIndex = paneIndexById.get(paneId);
  if (paneIndex == null) return null;
  const name = spec.label || spec.key || paneId;

  if (spec.type === 'candlestick') {
    return {
      name: name || 'K线',
      type: 'candlestick',
      xAxisIndex: paneIndex,
      yAxisIndex: paneIndex,
      data: Array.isArray(spec.data) ? spec.data : [],
      // 用类目占比，不设 barMaxWidth（否则宽屏/少根数时会被钉死成细棍）
      barWidth: '78%',
      barMinWidth: 4,
      barCategoryGap: '18%',
      itemStyle: {
        color: MARKET_CANDLE_UP_COLOR,
        color0: MARKET_CANDLE_DOWN_COLOR,
        borderColor: MARKET_CANDLE_UP_COLOR,
        borderColor0: MARKET_CANDLE_DOWN_COLOR,
        borderWidth: 1,
      },
    };
  }

  if (spec.type === 'line') {
    const lineStyle = {
      width: spec.lineWidth != null ? Number(spec.lineWidth) : 1.5,
      color: spec.color || undefined,
    };
    if (spec.lineDash) {
      lineStyle.type = Array.isArray(spec.lineDash) ? spec.lineDash : 'dashed';
    }
    return {
      name,
      type: 'line',
      xAxisIndex: paneIndex,
      yAxisIndex: paneIndex,
      showSymbol: Boolean(spec.showSymbol),
      symbol: spec.symbol || 'circle',
      symbolSize: spec.symbolSize != null ? Number(spec.symbolSize) : 6,
      smooth: false,
      step: spec.step || false,
      lineStyle,
      itemStyle: { color: spec.color || undefined },
      areaStyle: spec.areaStyle || undefined,
      data: Array.isArray(spec.data) ? spec.data : [],
      connectNulls: Boolean(spec.connectNulls),
    };
  }

  if (spec.type === 'bar') {
    let data = Array.isArray(spec.data) ? spec.data : [];
    if (spec.color === 'candle') {
      data = colorizeVolumeBars(data, candleData);
    } else if (spec.color === 'signed') {
      data = colorizeSignedBars(data);
    } else if (spec.color) {
      data = data.map((raw) => {
        const n = Number(raw);
        if (!Number.isFinite(n)) return null;
        return { value: n, itemStyle: { color: spec.color, opacity: 0.8 } };
      });
    }
    const isVolume = paneId === 'volume';
    return {
      name,
      type: 'bar',
      xAxisIndex: paneIndex,
      yAxisIndex: paneIndex,
      data,
      barWidth: isVolume ? '78%' : '55%',
      barMinWidth: 2,
      barCategoryGap: '18%',
      itemStyle: spec.color && spec.color !== 'candle' && spec.color !== 'signed'
        ? { color: spec.color }
        : undefined,
    };
  }

  if (spec.type === 'scatter') {
    return {
      name,
      type: 'scatter',
      xAxisIndex: paneIndex,
      yAxisIndex: paneIndex,
      data: Array.isArray(spec.data) ? spec.data : [],
      symbol: spec.symbol,
      symbolSize: spec.symbolSize,
      itemStyle: spec.itemStyle,
      tooltip: { show: false },
      legendHoverLink: false,
      clip: false,
      z: 12,
    };
  }

  return null;
}

/**
 * 业务无关：MarketChartModel → ECharts option。
 *
 * @param {{
 *   categories: string[],
 *   panes: Array<{ id: string, heightRatio: number, yAxis?: object }>,
 *   series: Array<object>,
 *   markers?: Array<object>,
 *   interaction?: { dataZoom?: boolean },
 * }} model
 */
export function buildMarketChartOption(model) {
  if (!model || !Array.isArray(model.categories) || model.categories.length === 0) {
    return {};
  }
  if (!Array.isArray(model.panes) || model.panes.length === 0) return {};

  const categories = model.categories;
  const panes = model.panes;
  const paneIndexById = new Map(panes.map((pane, index) => [String(pane.id), index]));

  const candleSpec = (model.series || []).find((row) => row?.type === 'candlestick');
  const candleData = Array.isArray(candleSpec?.data) ? candleSpec.data : [];
  const candleByDate = buildCandleLookupFromSeries(categories, candleData);

  const series = [];
  (model.series || []).forEach((spec) => {
    const built = buildSeriesFromSpec(spec, paneIndexById, candleData);
    if (built) series.push(built);
  });

  const markerSeries = buildMarkerScatterSeries(
    model.markers,
    categories,
    candleByDate,
    paneIndexById,
  );
  series.push(...markerSeries);

  const grids = buildGrids(panes);
  const zoom = initialZoomRange(categories.length);
  const xZoomIndexes = panes.map((_, index) => index);
  const showZoom = model.interaction?.dataZoom !== false;

  const legendItems = series.map((row) => row.name).filter(Boolean);
  const paneTitleBySeriesName = new Map();
  (model.series || []).forEach((spec) => {
    const pane = panes.find((p) => String(p.id) === String(spec.paneId));
    const name = spec.label || spec.key;
    if (pane?.title && name) paneTitleBySeriesName.set(name, pane.title);
  });

  const xAxis = panes.map((_, index) => ({
    type: 'category',
    gridIndex: index,
    data: categories,
    scale: true,
    boundaryGap: true,
    axisLine: MARKET_CHART_AXIS_LINE,
    axisPointer: {
      label: { show: index === panes.length - 1 },
    },
    axisLabel: index === panes.length - 1
      ? {
        ...MARKET_CHART_AXIS_LABEL_SM,
        formatter: (v) => formatMarketChartDateLabel(v),
      }
      : { show: false },
  }));

  const yAxis = panes.map((pane) => ({
    gridIndex: paneIndexById.get(String(pane.id)),
    ...resolveYAxisOption(pane),
  }));

  const graphics = [
    ...(buildPanelDividers(panes, grids) || []),
    ...buildPaneTitleGraphics(panes, grids),
  ];

  return {
    animation: false,
    legend: legendItems.length
      ? {
        type: 'scroll',
        data: legendItems,
        top: 2,
        left: GRID_LEFT,
        right: GRID_RIGHT,
        height: 22,
        textStyle: MARKET_CHART_LEGEND_TEXT,
        pageTextStyle: { color: 'rgba(255,255,255,0.55)' },
        itemWidth: 12,
        itemHeight: 8,
        itemGap: 10,
      }
      : undefined,
    axisPointer: {
      link: panes.length > 1 ? [{ xAxisIndex: xZoomIndexes }] : undefined,
    },
    grid: grids,
    graphic: graphics.length ? graphics : undefined,
    dataZoom: showZoom
      ? [
        {
          type: 'slider',
          xAxisIndex: xZoomIndexes,
          filterMode: 'filter',
          height: 22,
          bottom: 6,
          start: zoom.start,
          end: zoom.end,
          borderColor: 'rgba(255,255,255,0.12)',
          fillerColor: 'rgba(0, 188, 212, 0.15)',
          handleStyle: { color: '#4dd0e1' },
          textStyle: { color: 'rgba(255,255,255,0.55)', fontSize: 10 },
        },
      ]
      : undefined,
    xAxis,
    yAxis,
    tooltip: {
      ...MARKET_CHART_TOOLTIP,
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params) => {
        const arr = Array.isArray(params) ? params : [params];
        if (!arr.length) return '';
        const lines = [formatMarketChartDateLabel(arr[0].axisValue)];
        const seenMarker = new Set();
        const seenPaneTitle = new Set();
        arr.forEach((p) => {
          const ohlc = readCandlestickOHLC(p, candleByDate, candleData);
          if (ohlc) {
            lines.push(
              `开盘 ${fmtNum(ohlc.open)}　收盘 ${fmtNum(ohlc.close)}　`
              + `最低 ${fmtNum(ohlc.low)}　最高 ${fmtNum(ohlc.high)}`,
            );
            return;
          }
          if (p.seriesType === 'scatter') {
            const meta = p.data?._markerMeta;
            const tipKey = meta?.tooltipKey || meta?.key || meta?.date || p.seriesName;
            if (meta && !seenMarker.has(tipKey)) {
              seenMarker.add(tipKey);
              if (meta.tooltipHtml) {
                lines.push(meta.tooltipHtml);
              } else if (meta.label) {
                lines.push(meta.label);
              }
            }
            return;
          }
          if (
            (p.seriesType === 'line' || p.seriesType === 'bar')
            && p.value != null
          ) {
            const paneTitle = paneTitleBySeriesName.get(p.seriesName);
            if (paneTitle && !seenPaneTitle.has(paneTitle)) {
              seenPaneTitle.add(paneTitle);
              lines.push(`【${paneTitle}】`);
            }
            const raw = typeof p.value === 'object' && p.value != null && 'value' in p.value
              ? p.value.value
              : p.value;
            if (Number.isFinite(Number(raw))) {
              const text = p.seriesName === '成交量'
                ? fmtCompactAxis(raw)
                : fmtNum(raw, 2);
              lines.push(`${p.seriesName}：${text}`);
            }
          }
        });
        return lines.filter(Boolean).join('<br/>');
      },
    },
    series,
  };
}
