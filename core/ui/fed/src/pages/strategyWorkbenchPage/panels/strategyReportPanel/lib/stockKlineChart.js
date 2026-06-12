import { formatReportChartDateLabel } from './reportDateFormat';
import {
  REPORT_CHART_AXIS_LABEL_SM,
  REPORT_CHART_AXIS_LINE,
  REPORT_CHART_SPLIT_LINE,
  REPORT_CHART_TOOLTIP,
} from './reportChartsTheme';

const MARKER_COLORS = {
  buy: '#00E8FF',
  sell: '#C62828',
  opportunity: '#00E8FF',
  target_win: '#FF4D67',
  target_loss: '#00D9A5',
};

/** A 股习惯：阳线红、阴线绿（close vs open） */
const CANDLE_UP_COLOR = '#FF4D67';
const CANDLE_DOWN_COLOR = '#00D9A5';

/** 自定义向上小箭头（内置 arrow 在 markPoint 上旋转不可靠） */
const UP_ARROW_SYMBOL = 'path://M0,10 L5,0 L10,10 Z';
const DOWN_ARROW_SYMBOL = 'path://M0,0 L5,10 L10,0 Z';
const UP_ARROW_SIZE = 7;
const UP_ARROW_OFFSET_Y = 6;
const DOWN_ARROW_SIZE = 7;
const DOWN_ARROW_OFFSET_Y = -6;

function buildCyanUpArrowStyle() {
  return {
    color: MARKER_COLORS.opportunity,
    borderColor: 'rgba(255, 255, 255, 0.85)',
    borderWidth: 1,
    shadowBlur: 4,
    shadowColor: 'rgba(0, 232, 255, 0.55)',
  };
}

function buildTargetArrowStyle(type) {
  const color = type === 'target_win' ? MARKER_COLORS.target_win : MARKER_COLORS.target_loss;
  const shadow = type === 'target_win'
    ? 'rgba(255, 77, 103, 0.55)'
    : 'rgba(0, 217, 165, 0.55)';
  return {
    color,
    borderColor: 'rgba(255, 255, 255, 0.85)',
    borderWidth: 1,
    shadowBlur: 4,
    shadowColor: shadow,
  };
}

/** 自下方向上指向 K 线最低价（机会 / 买入） */
function buildUpwardArrowMarkPoint(item, candleByDate) {
  const date = String(item?.date || '').trim();
  const bar = candleByDate?.get(date);
  const low = Number(bar?.low);
  if (!date || !Number.isFinite(low)) return null;

  return {
    name: item.label || item.type || '标记',
    coord: [date, low],
    symbol: UP_ARROW_SYMBOL,
    symbolSize: UP_ARROW_SIZE,
    symbolOffset: [0, UP_ARROW_OFFSET_Y],
    itemStyle: buildCyanUpArrowStyle(),
    _markerMeta: item,
  };
}

/** 自上方向下指向 K 线最高价（目标完成：红胜 / 绿负） */
function buildTargetMarkPoint(item, candleByDate) {
  const date = String(item?.date || '').trim();
  const bar = candleByDate?.get(date);
  const high = Number(bar?.high);
  if (!date || !Number.isFinite(high)) return null;

  return {
    name: item.label || item.type || '目标',
    coord: [date, high],
    symbol: DOWN_ARROW_SYMBOL,
    symbolSize: DOWN_ARROW_SIZE,
    symbolOffset: [0, DOWN_ARROW_OFFSET_Y],
    itemStyle: buildTargetArrowStyle(item.type),
    _markerMeta: item,
  };
}

const MARKER_LEGEND_DEFS = {
  opportunity: { label: '机会', symbol: UP_ARROW_SYMBOL, style: buildCyanUpArrowStyle },
  buy: { label: '买入', symbol: UP_ARROW_SYMBOL, style: buildCyanUpArrowStyle },
  target_win: { label: '目标胜', symbol: DOWN_ARROW_SYMBOL, style: () => buildTargetArrowStyle('target_win') },
  target_loss: { label: '目标负', symbol: DOWN_ARROW_SYMBOL, style: () => buildTargetArrowStyle('target_loss') },
};

function buildMarkerLegendSeries(markers) {
  const types = new Set(
    (markers || []).map((item) => String(item?.type || '').trim()).filter(Boolean),
  );
  return [...types]
    .filter((type) => MARKER_LEGEND_DEFS[type])
    .map((type) => {
      const def = MARKER_LEGEND_DEFS[type];
      return {
        name: def.label,
        type: 'scatter',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: [],
        symbol: def.symbol,
        symbolSize: type === 'target_win' || type === 'target_loss' ? DOWN_ARROW_SIZE : UP_ARROW_SIZE,
        itemStyle: def.style(),
        tooltip: { show: false },
      };
    });
}

const DEFAULT_ZOOM_WINDOW = 35;
/** 副图高度 ≈ 主图 K 线区域的 32%（落在 1/4–1/3 区间） */
const PANEL_DIVIDER_COLOR = 'rgba(255, 255, 255, 0.52)';
const DUAL_PANEL_LAYOUT = {
  priceTop: 8,
  priceHeight: 51,
  gap: 3.5,
  oscHeight: 17,
};

function buildDualPanelGrids() {
  const { priceTop, priceHeight, gap, oscHeight } = DUAL_PANEL_LAYOUT;
  const oscTop = priceTop + priceHeight + gap;
  return [
    { left: 44, right: 16, top: `${priceTop}%`, height: `${priceHeight}%` },
    {
      left: 44,
      right: 16,
      top: `${oscTop}%`,
      height: `${oscHeight}%`,
      borderWidth: 2,
      borderColor: PANEL_DIVIDER_COLOR,
      backgroundColor: 'rgba(255, 255, 255, 0.04)',
    },
  ];
}

function buildPanelDividerGraphic() {
  const { priceTop, priceHeight, gap } = DUAL_PANEL_LAYOUT;
  const dividerTop = priceTop + priceHeight + (gap / 2);
  return [{
    type: 'rect',
    left: 44,
    right: 16,
    top: `${dividerTop}%`,
    z: 4,
    shape: { x: 0, y: -1, width: 4000, height: 2 },
    style: { fill: PANEL_DIVIDER_COLOR },
  }];
}

function markerColor(type) {
  return MARKER_COLORS[type] || '#90CAF9';
}

function fmtPrice(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  return n.toFixed(2);
}

function fmtIndicator(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  return n.toFixed(2);
}

const MARKER_DETAIL_LABELS = {
  opportunity_id: '机会 ID',
  trigger_date: '触发日',
  chart_close: '图上收盘价',
  engine_trigger_price: '引擎记录价',
  buy_date: '买入日',
  buy_price: '买入价',
  sell_date: '卖出日',
  sell_price: '卖出价',
  status: '状态',
  sell_reason: '卖出原因',
  target_name: '目标',
  profit: '盈亏',
  profit_ratio: '收益率',
  target_type: '目标类型',
};

function formatMarkerTooltip(marker) {
  const lines = [marker.label || marker.type || '标记'];
  const detail = marker.detail && typeof marker.detail === 'object' ? marker.detail : {};
  Object.entries(detail).forEach(([k, v]) => {
    if (v == null || v === '') return;
    const label = MARKER_DETAIL_LABELS[k] || k;
    const text = typeof v === 'number' ? fmtPrice(v) : String(v);
    lines.push(`${label}: ${text}`);
  });
  if (marker.date) lines.unshift(formatReportChartDateLabel(marker.date));
  return lines.filter(Boolean).join('<br/>');
}

function initialZoomRange(length) {
  if (length <= DEFAULT_ZOOM_WINDOW) {
    return { start: 0, end: 100 };
  }
  const start = Math.max(0, 100 - Math.round((DEFAULT_ZOOM_WINDOW / length) * 100));
  return { start, end: 100 };
}

function buildMarkPointData(markers, candleByDate) {
  if (!Array.isArray(markers)) return [];
  return markers
    .map((item) => {
      const type = String(item?.type || '').trim();
      if (type === 'opportunity' || type === 'buy') {
        return buildUpwardArrowMarkPoint(item, candleByDate);
      }
      if (type === 'target_win' || type === 'target_loss') {
        return buildTargetMarkPoint(item, candleByDate);
      }
      if (!item?.date || item.price == null || !Number.isFinite(Number(item.price))) {
        return null;
      }
      return {
        name: item.label || item.type || '标记',
        coord: [item.date, Number(item.price)],
        symbol: 'circle',
        symbolSize: 9,
        symbolOffset: [0, -5],
        itemStyle: {
          color: markerColor(item.type),
          borderColor: 'rgba(255, 255, 255, 0.35)',
          borderWidth: 1,
        },
        _markerMeta: item,
      };
    })
    .filter(Boolean);
}

function buildCandleLookup(candles) {
  const byDate = new Map();
  (candles || []).forEach((row) => {
    const date = String(row?.date || '').trim();
    if (date) byDate.set(date, row);
  });
  return byDate;
}

/** 优先用业务 candles（按日期），避免 ECharts 把 dataIndex 塞进 data 首项。 */
function readCandlestickOHLC(param, candleByDate, candleData) {
  if (param?.seriesType !== 'candlestick') return null;

  const dateKey = String(param.axisValue ?? param.name ?? '').trim();
  if (dateKey && candleByDate?.has(dateKey)) {
    const row = candleByDate.get(dateKey);
    const open = Number(row.open);
    const close = Number(row.close);
    const low = Number(row.low);
    const high = Number(row.high);
    if ([open, close, low, high].every(Number.isFinite)) {
      return { open, close, low, high };
    }
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
  // 部分 ECharts 版本为 [dataIndex, open, close, low, high]
  const nums = (raw.length >= 5 && Number.isInteger(raw[0]) && raw[0] < 100000
    ? raw.slice(1, 5)
    : raw.slice(0, 4)
  ).map((v) => Number(v));
  if (nums.some((v) => !Number.isFinite(v))) return null;
  const [open, close, low, high] = nums;
  return { open, close, low, high };
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
  return [open, close, low, high];
}

/** 日期轴、K 线、指标必须同索引；不可单独 filter 蜡烛行否则 tooltip 会串日。 */
function prepareAlignedChartRows(candles, indicatorSeries) {
  const dates = [];
  const candleData = [];
  const validIndexes = [];
  (candles || []).forEach((item, index) => {
    const row = normalizeCandleRow(item);
    if (!row) return;
    validIndexes.push(index);
    dates.push(item.date);
    candleData.push(row);
  });
  const alignedIndicators = (indicatorSeries || []).map((row) => ({
    ...row,
    data: validIndexes.map((i) => {
      const values = Array.isArray(row.data) ? row.data : [];
      return i < values.length ? values[i] : null;
    }),
  }));
  return { dates, candleData, indicatorSeries: alignedIndicators };
}

export function buildStockKlineChartOptionFromPayload(payload) {
  if (!payload || !Array.isArray(payload.candles) || payload.candles.length === 0) return {};
  const {
    dates,
    candleData,
    indicatorSeries,
  } = prepareAlignedChartRows(payload.candles, payload.indicator_series);
  if (!candleData.length) return {};

  const candleByDate = buildCandleLookup(payload.candles);
  const markPointData = buildMarkPointData(payload.markers, candleByDate);
  const oscillatorRows = indicatorSeries.filter((row) => row.panel === 'oscillator');
  const overlayRows = indicatorSeries.filter((row) => row.panel !== 'oscillator');
  const hasOscillator = oscillatorRows.length > 0;
  const zoom = initialZoomRange(dates.length);
  const xZoomIndexes = hasOscillator ? [0, 1] : [0];

  const markerLegendSeries = buildMarkerLegendSeries(payload.markers);
  const legendItems = [
    'K线',
    ...overlayRows.map((row) => row.label || row.key),
    ...oscillatorRows.map((row) => row.label || row.key),
    ...markerLegendSeries.map((row) => row.name),
  ];

  const overlayLineSeries = overlayRows.map((row) => ({
    name: row.label || row.key,
    type: 'line',
    xAxisIndex: 0,
    yAxisIndex: 0,
    showSymbol: false,
    smooth: false,
    lineStyle: { width: 1.5, color: row.color || undefined },
    itemStyle: { color: row.color || undefined },
    data: Array.isArray(row.data) ? row.data : [],
    connectNulls: false,
  }));

  const oscillatorLineSeries = oscillatorRows.map((row) => ({
    name: row.label || row.key,
    type: 'line',
    xAxisIndex: 1,
    yAxisIndex: 1,
    showSymbol: false,
    smooth: false,
    lineStyle: { width: 1.5, color: row.color || undefined },
    itemStyle: { color: row.color || undefined },
    data: Array.isArray(row.data) ? row.data : [],
    connectNulls: false,
  }));

  const grid = hasOscillator
    ? buildDualPanelGrids()
    : [{ left: 44, right: 16, top: 28, height: '68%' }];

  const xAxis = hasOscillator
    ? [
      {
        type: 'category',
        gridIndex: 0,
        data: dates,
        scale: true,
        boundaryGap: true,
        axisLine: REPORT_CHART_AXIS_LINE,
        axisLabel: { show: false },
      },
      {
        type: 'category',
        gridIndex: 1,
        data: dates,
        scale: true,
        boundaryGap: true,
        axisLine: REPORT_CHART_AXIS_LINE,
        axisLabel: {
          ...REPORT_CHART_AXIS_LABEL_SM,
          formatter: (v) => formatReportChartDateLabel(v),
        },
      },
    ]
    : [{
      type: 'category',
      data: dates,
      scale: true,
      boundaryGap: true,
      axisLine: REPORT_CHART_AXIS_LINE,
      axisLabel: {
        ...REPORT_CHART_AXIS_LABEL_SM,
        formatter: (v) => formatReportChartDateLabel(v),
      },
    }];

  const yAxis = hasOscillator
    ? [
      {
        gridIndex: 0,
        scale: true,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          ...REPORT_CHART_AXIS_LABEL_SM,
          formatter: (v) => fmtPrice(v),
        },
        splitLine: REPORT_CHART_SPLIT_LINE,
      },
      {
        gridIndex: 1,
        scale: true,
        min: 0,
        max: 100,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          ...REPORT_CHART_AXIS_LABEL_SM,
          formatter: (v) => fmtIndicator(v),
        },
        splitLine: REPORT_CHART_SPLIT_LINE,
      },
    ]
    : [{
      scale: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        ...REPORT_CHART_AXIS_LABEL_SM,
        formatter: (v) => fmtPrice(v),
      },
      splitLine: REPORT_CHART_SPLIT_LINE,
    }];

  return {
    animation: false,
    legend: legendItems.length
      ? {
        data: legendItems,
        top: 0,
        textStyle: { color: 'rgba(255,255,255,0.72)', fontSize: 11 },
        itemWidth: 14,
        itemHeight: 8,
      }
      : undefined,
    axisPointer: {
      link: hasOscillator ? [{ xAxisIndex: [0, 1] }] : undefined,
    },
    grid,
    graphic: hasOscillator ? buildPanelDividerGraphic() : undefined,
    dataZoom: [
      {
        type: 'slider',
        xAxisIndex: xZoomIndexes,
        filterMode: 'filter',
        height: 22,
        bottom: 8,
        start: zoom.start,
        end: zoom.end,
        borderColor: 'rgba(255,255,255,0.12)',
        fillerColor: 'rgba(0, 188, 212, 0.15)',
        handleStyle: { color: '#4dd0e1' },
        textStyle: { color: 'rgba(255,255,255,0.55)', fontSize: 10 },
      },
    ],
    xAxis,
    yAxis,
    tooltip: {
      ...REPORT_CHART_TOOLTIP,
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params) => {
        const arr = Array.isArray(params) ? params : [params];
        if (!arr.length) return '';
        const lines = [formatReportChartDateLabel(arr[0].axisValue)];
        arr.forEach((p) => {
          const ohlc = readCandlestickOHLC(p, candleByDate, candleData);
          if (ohlc) {
            lines.push(
              `开盘 ${fmtPrice(ohlc.open)}　收盘 ${fmtPrice(ohlc.close)}　`
              + `最低 ${fmtPrice(ohlc.low)}　最高 ${fmtPrice(ohlc.high)}`,
            );
            return;
          }
          if (p.seriesType === 'line' && p.value != null && Number.isFinite(Number(p.value))) {
            lines.push(`${p.seriesName}：${fmtIndicator(p.value)}`);
          }
        });
        return lines.filter(Boolean).join('<br/>');
      },
    },
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        xAxisIndex: 0,
        yAxisIndex: 0,
        data: candleData,
        itemStyle: {
          color: CANDLE_UP_COLOR,
          color0: CANDLE_DOWN_COLOR,
          borderColor: CANDLE_UP_COLOR,
          borderColor0: CANDLE_DOWN_COLOR,
        },
        markPoint: markPointData.length
          ? {
            z: 6,
            data: markPointData,
            tooltip: {
              trigger: 'item',
              formatter: (params) => {
                const meta = params?.data?._markerMeta;
                if (!meta) return params?.name || '';
                return formatMarkerTooltip(meta);
              },
            },
          }
          : undefined,
      },
      ...overlayLineSeries,
      ...oscillatorLineSeries,
      ...markerLegendSeries,
    ],
  };
}
