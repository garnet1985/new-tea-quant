import { formatReportChartDateLabel } from './reportDateFormat';
import {
  REPORT_CHART_AXIS_LABEL_SM,
  REPORT_CHART_AXIS_LINE,
  REPORT_CHART_SPLIT_LINE,
  REPORT_CHART_TOOLTIP,
} from './reportChartsTheme';

const MARKER_COLORS = {
  buy: '#2E7D32',
  sell: '#C62828',
  opportunity: '#FFB74D',
};

const DEFAULT_ZOOM_WINDOW = 35;
const PRICE_GRID = { left: 44, right: 16, top: 32, height: '42%' };
const OSC_GRID = { left: 44, right: 16, top: '52%', height: '36%' };

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
  sell_date: '卖出日',
  status: '状态',
  sell_reason: '卖出原因',
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

function buildMarkPointData(markers) {
  if (!Array.isArray(markers)) return [];
  return markers
    .filter((item) => item?.date && item.price != null && Number.isFinite(Number(item.price)))
    .map((item) => ({
      name: item.label || item.type || '标记',
      coord: [item.date, Number(item.price)],
      symbol: 'triangle',
      symbolRotate: 0,
      symbolSize: 14,
      symbolOffset: [0, -6],
      itemStyle: { color: markerColor(item.type) },
      _markerMeta: item,
    }));
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
  const markPointData = buildMarkPointData(payload.markers);
  const oscillatorRows = indicatorSeries.filter((row) => row.panel === 'oscillator');
  const overlayRows = indicatorSeries.filter((row) => row.panel !== 'oscillator');
  const hasOscillator = oscillatorRows.length > 0;
  const zoom = initialZoomRange(dates.length);
  const xZoomIndexes = hasOscillator ? [0, 1] : [0];

  const legendItems = [
    'K线',
    ...overlayRows.map((row) => row.label || row.key),
    ...oscillatorRows.map((row) => row.label || row.key),
    ...(markPointData.length ? ['机会'] : []),
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
    ? [PRICE_GRID, OSC_GRID]
    : [{ ...PRICE_GRID, height: '68%', top: 32 }];

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
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: xZoomIndexes,
        filterMode: 'filter',
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
        moveOnMouseWheel: true,
        start: zoom.start,
        end: zoom.end,
      },
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
          color: '#ef5350',
          color0: '#26a69a',
          borderColor: '#ef5350',
          borderColor0: '#26a69a',
        },
        markPoint: markPointData.length
          ? {
            symbol: 'triangle',
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
      ...(markPointData.length
        ? [{
          name: '机会',
          type: 'scatter',
          xAxisIndex: 0,
          yAxisIndex: 0,
          data: [],
          symbolSize: 0,
          tooltip: { show: false },
        }]
        : []),
    ],
  };
}
