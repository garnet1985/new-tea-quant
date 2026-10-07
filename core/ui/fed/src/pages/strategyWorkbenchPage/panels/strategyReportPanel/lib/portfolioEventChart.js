import { formatReportMoney } from './formatReportMoney';
import { formatReportChartDateLabel } from './reportDateFormat';
import {
  MARKET_MARKER_PIN_DOWN,
  MARKET_MARKER_PIN_OFFSET_DOWN,
  MARKET_MARKER_PIN_OFFSET_UP,
  MARKET_MARKER_PIN_SIZE,
  MARKET_MARKER_PIN_UP,
  marketMarkerPinStyle,
} from 'components/marketChart';
import {
  REPORT_CHART_AXIS_LABEL,
  REPORT_CHART_AXIS_LINE,
  REPORT_CHART_SPLIT_LINE,
  REPORT_CHART_TOOLTIP,
} from './reportChartsTheme';
import { resolveMarketPnlPalette } from 'styles/marketPnlColors';

const DRAWDOWN_LINE = '#EF5350';
const DRAWDOWN_AREA = 'rgba(239, 83, 80, 0.10)';

function equityPalette(metrics) {
  return resolveMarketPnlPalette(metrics?.marketProfile || metrics?.market_profile);
}

export function equityResultIsPositive(metrics) {
  const initial = Number(metrics?.initialCapital);
  const final = Number(metrics?.finalEquity);
  if (Number.isFinite(initial) && Number.isFinite(final)) {
    return final >= initial;
  }
  const ret = Number(metrics?.totalReturnPct);
  if (Number.isFinite(ret)) return ret >= 0;
  const profit = Number(metrics?.totalProfit);
  if (Number.isFinite(profit)) return profit >= 0;
  return true;
}

export function equityAxisMinMax(equityCurveValues) {
  const nums = (equityCurveValues || [])
    .map((v) => Number(v))
    .filter((v) => Number.isFinite(v));
  if (nums.length === 0) return {};
  const minV = Math.min(...nums);
  const maxV = Math.max(...nums);
  const span = Math.max(maxV - minV, Math.abs(minV) * 0.02, Math.abs(maxV) * 0.02, 1);
  const pad = span * 0.12;
  return {
    min: minV - pad,
    max: maxV + pad,
  };
}

export function formatEquityAxisWan(value, yMin, yMax) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '';
  const span = (
    Number.isFinite(yMin) && Number.isFinite(yMax)
      ? Math.abs(yMax - yMin)
      : Math.abs(n)
  );
  const wan = n / 10000;
  if (span < 10000) return `${wan.toFixed(2)}w`;
  if (span < 80000) return `${wan.toFixed(1)}w`;
  return `${Math.round(wan)}w`;
}

function pickCurve(metrics) {
  const eventLabels = Array.isArray(metrics?.eventCurveLabels) ? metrics.eventCurveLabels : [];
  const eventValues = Array.isArray(metrics?.eventCurveValues) ? metrics.eventCurveValues : [];
  const eventDrawdown = Array.isArray(metrics?.eventDrawdownValues)
    ? metrics.eventDrawdownValues
    : [];
  if (
    eventLabels.length >= 2
    && eventValues.length === eventLabels.length
    && eventDrawdown.length === eventLabels.length
  ) {
    return {
      labels: eventLabels,
      values: eventValues,
      drawdown: eventDrawdown,
    };
  }
  return {
    labels: metrics?.equityCurveLabels || [],
    values: metrics?.equityCurveValues || [],
    drawdown: metrics?.drawdownCurveValues || [],
  };
}

export function groupTradeEventsByDate(tradeEvents) {
  const byDate = new Map();
  (tradeEvents || []).forEach((row) => {
    const date = String(row?.date || '').trim();
    const side = String(row?.side || '').trim().toLowerCase();
    if (!date || (side !== 'buy' && side !== 'sell')) return;
    let bucket = byDate.get(date);
    if (!bucket) {
      bucket = { buys: [], sells: [] };
      byDate.set(date, bucket);
    }
    if (side === 'buy') bucket.buys.push(row);
    else bucket.sells.push(row);
  });
  return byDate;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function stockLabel(row) {
  const code = String(row?.entityId || '').trim();
  const name = String(row?.stockName || '').trim();
  if (name && code && name !== code) return `${name}(${code})`;
  return name || code || '未知';
}

function tooltipPinSvg(isSell, palette) {
  const p = palette || resolveMarketPnlPalette();
  const color = isSell ? p.sell : p.buy;
  const d = isSell
    ? 'M6,15 L1,6 C1,2 3.5,0 6,0 C8.5,0 11,2 11,6 L6,15 Z'
    : 'M6,0 L1,9 C1,13 3.5,15 6,15 C8.5,15 11,13 11,9 L6,0 Z';
  return (
    `<svg width="10" height="12" viewBox="0 0 12 15"`
    + ` style="display:inline-block;vertical-align:-2px;margin-right:4px" aria-hidden="true">`
    + `<path d="${d}" fill="${color}" stroke="#ffffff" stroke-width="1"/></svg>`
  );
}

function formatEventLine(row, palette) {
  const isSell = String(row?.side || '').toLowerCase() === 'sell';
  const shares = Number(row?.shares);
  const shareText = Number.isFinite(shares) ? `${shares.toLocaleString()}股` : '—股';
  const action = isSell ? '卖出' : '买入';
  const head = `${action} ${stockLabel(row)} ${shareText}`;
  const parts = [head];
  if (isSell) {
    const entry = Number.isFinite(Number(row?.buyPrice))
      ? formatReportMoney(row.buyPrice)
      : '--';
    const exitPx = formatReportMoney(Math.max(0, Number(row?.price) || 0));
    parts.push(`入价: ${entry} 出价:${exitPx}`);
    const profit = Number(row?.profit);
    if (Number.isFinite(profit)) {
      parts.push(`盈利: ${formatReportMoney(profit)}`);
    }
  } else {
    parts.push(`价格: ${formatReportMoney(row?.price)}`);
    const cost = Number(row?.cost);
    if (Number.isFinite(cost)) {
      parts.push(`成本: ${formatReportMoney(cost)}`);
    }
  }
  return (
    `<span style="white-space:nowrap">${tooltipPinSvg(isSell, palette)}${escapeHtml(parts.join(' | '))}</span>`
  );
}

const EVENT_ROW_DIVIDER = (
  '<div style="height:1px;background:rgba(255,255,255,0.16);margin:6px 0"></div>'
);

function scatterPoints(labels, values, byDate, sideKey) {
  return labels.map((date, i) => {
    const events = byDate.get(date)?.[sideKey] || [];
    if (!events.length) return null;
    return {
      value: values[i],
      events,
    };
  });
}

const EQUAL_PANEL_HEIGHT = '38%';

/**
 * 净值图默认不画买卖钉（太密也易卡）。买卖生命周期见单独事件图。
 * 见 CORPORATE_ACTION_CASH_ACCOUNTS.md
 */
export const PORTFOLIO_CHART_SHOW_TRADE_EVENTS = false;

function sharedCategoryAxis(labels, { showLabels }) {
  return {
    type: 'category',
    data: labels,
    axisTick: { show: false },
    axisLine: REPORT_CHART_AXIS_LINE,
    axisLabel: showLabels
      ? {
        ...REPORT_CHART_AXIS_LABEL,
        formatter: (v) => formatReportChartDateLabel(v),
      }
      : { show: false },
    axisPointer: { show: true, label: { show: false } },
  };
}

export function buildPortfolioEventChartOption(metrics) {
  const { labels, values, drawdown } = pickCurve(metrics);
  if (!labels.length || values.length !== labels.length) return null;

  const palette = equityPalette(metrics);
  const positive = equityResultIsPositive(metrics);
  const lineColor = positive ? palette.profit : palette.loss;
  const areaColor = positive
    ? (palette.polarity === 'cn' ? 'rgba(255, 77, 103, 0.16)' : 'rgba(0, 217, 165, 0.16)')
    : (palette.polarity === 'cn' ? 'rgba(0, 217, 165, 0.16)' : 'rgba(255, 77, 103, 0.16)');
  const buyColor = palette.buy;
  const sellColor = palette.sell;
  const { min: yMin, max: yMax } = equityAxisMinMax(values);
  const byDate = PORTFOLIO_CHART_SHOW_TRADE_EVENTS
    ? groupTradeEventsByDate(metrics?.tradeEvents)
    : new Map();
  const buyData = scatterPoints(labels, values, byDate, 'buys');
  const sellData = scatterPoints(labels, values, byDate, 'sells');
  const hasBuys = buyData.some((cell) => cell != null);
  const hasSells = sellData.some((cell) => cell != null);

  const legendData = ['总资产'];
  if (hasBuys) legendData.push('买入');
  if (hasSells) legendData.push('卖出');

  const series = [
    {
      name: '总资产',
      type: 'line',
      data: values,
      smooth: true,
      symbol: 'none',
      xAxisIndex: 0,
      yAxisIndex: 0,
      color: lineColor,
      lineStyle: { width: 2, color: lineColor },
      areaStyle: { color: areaColor },
    },
    {
      name: '回撤',
      type: 'line',
      data: drawdown,
      smooth: true,
      symbol: 'none',
      xAxisIndex: 1,
      yAxisIndex: 1,
      color: DRAWDOWN_LINE,
      lineStyle: { width: 1.5, color: DRAWDOWN_LINE },
      areaStyle: { color: DRAWDOWN_AREA },
    },
  ];
  if (hasBuys) {
    series.push({
      name: '买入',
      type: 'scatter',
      data: buyData,
      xAxisIndex: 0,
      yAxisIndex: 0,
      color: buyColor,
      symbol: MARKET_MARKER_PIN_UP,
      symbolSize: (val) => {
        const n = val?.events?.length || 1;
        return Math.min(18, MARKET_MARKER_PIN_SIZE + Math.max(0, n - 1) * 2);
      },
      symbolOffset: [0, MARKET_MARKER_PIN_OFFSET_UP],
      itemStyle: marketMarkerPinStyle(buyColor, palette.shadow.buy),
      tooltip: { show: false },
      z: 5,
    });
  }
  if (hasSells) {
    series.push({
      name: '卖出',
      type: 'scatter',
      data: sellData,
      xAxisIndex: 0,
      yAxisIndex: 0,
      color: sellColor,
      symbol: MARKET_MARKER_PIN_DOWN,
      symbolSize: (val) => {
        const n = val?.events?.length || 1;
        return Math.min(18, MARKET_MARKER_PIN_SIZE + Math.max(0, n - 1) * 2);
      },
      symbolOffset: [0, MARKET_MARKER_PIN_OFFSET_DOWN],
      itemStyle: marketMarkerPinStyle(sellColor, palette.shadow.sell),
      tooltip: { show: false },
      z: 5,
    });
  }

  return {
    animation: false,
    legend: {
      data: legendData,
      top: 0,
      left: 0,
      itemWidth: 14,
      itemHeight: 14,
      textStyle: { color: 'rgba(255, 255, 255, 0.72)', fontSize: 11 },
    },
    toolbox: {
      right: 4,
      top: 0,
      itemSize: 14,
      iconStyle: {
        borderColor: 'rgba(255, 255, 255, 0.72)',
      },
      emphasis: {
        iconStyle: {
          borderColor: 'rgba(255, 255, 255, 0.92)',
        },
      },
      feature: {
        restore: {
          title: '还原缩放',
        },
      },
    },
    axisPointer: {
      link: [{ xAxisIndex: 'all' }],
    },
    grid: [
      {
        left: 44,
        right: 16,
        top: 32,
        height: EQUAL_PANEL_HEIGHT,
      },
      {
        left: 44,
        right: 16,
        bottom: 38,
        height: EQUAL_PANEL_HEIGHT,
      },
    ],
    xAxis: [
      { ...sharedCategoryAxis(labels, { showLabels: false }), gridIndex: 0 },
      { ...sharedCategoryAxis(labels, { showLabels: true }), gridIndex: 1 },
    ],
    yAxis: [
      {
        type: 'value',
        gridIndex: 0,
        ...((yMin !== undefined && yMax !== undefined) ? { min: yMin, max: yMax } : {}),
        splitNumber: 4,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          ...REPORT_CHART_AXIS_LABEL,
          formatter: (value) => formatEquityAxisWan(value, yMin, yMax),
        },
        splitLine: REPORT_CHART_SPLIT_LINE,
      },
      {
        type: 'value',
        gridIndex: 1,
        min: 0,
        splitNumber: 2,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { ...REPORT_CHART_AXIS_LABEL, formatter: '{value}%' },
        splitLine: REPORT_CHART_SPLIT_LINE,
      },
    ],
    dataZoom: [
      {
        type: 'slider',
        xAxisIndex: [0, 1],
        height: 16,
        bottom: 6,
        brushSelect: false,
        filterMode: 'none',
        borderColor: 'rgba(255, 255, 255, 0.14)',
        fillerColor: 'rgba(255, 255, 255, 0.14)',
        handleStyle: { color: 'rgba(255, 255, 255, 0.72)' },
        moveHandleStyle: { color: 'rgba(255, 255, 255, 0.35)' },
        textStyle: { color: 'rgba(255, 255, 255, 0.58)', fontSize: 10 },
        dataBackground: {
          lineStyle: { color: 'rgba(255, 255, 255, 0.25)' },
          areaStyle: { color: 'rgba(255, 255, 255, 0.08)' },
        },
        selectedDataBackground: {
          lineStyle: { color: 'rgba(255, 255, 255, 0.45)' },
          areaStyle: { color: 'rgba(255, 255, 255, 0.16)' },
        },
      },
    ],
    series,
    tooltip: {
      ...REPORT_CHART_TOOLTIP,
      trigger: 'axis',
      confine: false,
      extraCssText: 'max-width:none;white-space:nowrap;',
      formatter: (params) => {
        const list = Array.isArray(params) ? params : [params];
        const date = list[0]?.axisValue;
        if (date == null || date === '') return '';
        const idx = labels.indexOf(String(date));
        const lines = [formatReportChartDateLabel(date)];
        const equity = idx >= 0 ? Number(values[idx]) : NaN;
        const dd = idx >= 0 ? Number(drawdown[idx]) : NaN;
        if (Number.isFinite(equity)) {
          lines.push(`总资产：${equity.toLocaleString()}`);
        }
        if (Number.isFinite(dd)) {
          lines.push(`回撤：${dd.toFixed(2)}%`);
        }
        const day = byDate.get(String(date));
        const events = [...(day?.buys || []), ...(day?.sells || [])];
        if (events.length) {
          lines.push('');
          lines.push(events.map((row) => formatEventLine(row, palette)).join(EVENT_ROW_DIVIDER));
        }
        return lines.join('<br/>');
      },
    },
  };
}
