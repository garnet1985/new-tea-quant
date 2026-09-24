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
import { resolveMarketPnlPalette } from 'theme/marketPnlColors';
import {
  equityAxisMinMax,
  equityResultIsPositive,
  formatEquityAxisWan,
} from './portfolioEventChart';

/** 默认开仓点：小圆点，避免 pin 墙 */
const START_DOT_SIZE = 7;
const START_DOT_SIZE_DIM = 5;

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

function newLifecycle(buy, key) {
  return {
    id: key,
    investmentId: buy.investmentId || null,
    entityId: buy.entityId || '',
    stockName: buy.stockName || buy.entityId || '',
    buy,
    sells: [],
    endDate: null,
    profit: null,
    outcome: 'open',
  };
}

function finalizeLifecycle(life) {
  if (!life.sells.length) {
    life.endDate = null;
    life.profit = null;
    life.outcome = 'open';
    return life;
  }
  life.endDate = life.sells[life.sells.length - 1].date;
  let sum = 0;
  let hasProfit = false;
  life.sells.forEach((sell) => {
    const p = Number(sell?.profit);
    if (Number.isFinite(p)) {
      sum += p;
      hasProfit = true;
    }
  });
  life.profit = hasProfit ? sum : null;
  life.outcome = hasProfit && sum < 0 ? 'loss' : 'profit';
  return life;
}

/**
 * 把买卖事件收成「开仓 → 终点」生命周期。
 * 配对键：``entityId + investmentId``（investment_id 仅在单票内递增，全局会撞号）；
 * 缺 investmentId 时同标的 FIFO。
 */
export function pairTradeLifecycles(tradeEvents) {
  const byLot = new Map(); // `${entityId}|${invId}` → open queue
  const fifo = new Map(); // entityId → open queue
  const order = [];

  (tradeEvents || []).forEach((row, index) => {
    const side = String(row?.side || '').trim().toLowerCase();
    const date = String(row?.date || '').trim();
    if (!date || (side !== 'buy' && side !== 'sell')) return;
    const entityId = String(row?.entityId || '').trim();
    const invId = String(row?.investmentId || '').trim();
    const lotKey = entityId && invId ? `${entityId}|${invId}` : '';

    if (side === 'buy') {
      // DataGrid 行 id 必须全局唯一；不可只用 investmentId
      const key = `t:${index}:${entityId || 'x'}:${invId || 'x'}:${date}`;
      const life = newLifecycle(row, key);
      if (lotKey) {
        let q = byLot.get(lotKey);
        if (!q) {
          q = [];
          byLot.set(lotKey, q);
        }
        q.push(life);
      } else if (entityId) {
        let q = fifo.get(entityId);
        if (!q) {
          q = [];
          fifo.set(entityId, q);
        }
        q.push(life);
      }
      order.push(life);
      return;
    }

    let life = null;
    if (lotKey) {
      const q = byLot.get(lotKey);
      if (q?.length) life = q[0];
    }
    if (!life && entityId) {
      const q = fifo.get(entityId);
      if (q?.length) life = q[0];
    }
    if (!life) return;
    life.sells.push(row);
    const buyShares = Number(life.buy?.shares);
    const sold = life.sells.reduce((acc, s) => acc + (Number(s?.shares) || 0), 0);
    if (Number.isFinite(buyShares) && buyShares > 0 && sold >= buyShares) {
      if (lotKey) {
        const q = byLot.get(lotKey);
        if (q?.length && q[0] === life) q.shift();
      } else if (entityId) {
        const q = fifo.get(entityId);
        if (q?.length && q[0] === life) q.shift();
      }
    }
  });

  return order.map(finalizeLifecycle);
}

function outcomeColor(outcome, palette) {
  if (outcome === 'loss') return palette.loss;
  if (outcome === 'profit') return palette.profit;
  return palette.buy;
}

function outcomeShadow(outcome, palette) {
  if (outcome === 'loss') return palette.shadow.loss;
  if (outcome === 'profit') return palette.shadow.profit;
  return palette.shadow.buy;
}

function sellPointColor(sell, life, palette) {
  const p = Number(sell?.profit);
  if (Number.isFinite(p)) return p < 0 ? palette.loss : palette.profit;
  return outcomeColor(life.outcome, palette);
}

function pickCurve(metrics) {
  const eventLabels = Array.isArray(metrics?.eventCurveLabels) ? metrics.eventCurveLabels : [];
  const eventValues = Array.isArray(metrics?.eventCurveValues) ? metrics.eventCurveValues : [];
  if (eventLabels.length >= 2 && eventValues.length === eventLabels.length) {
    return { labels: eventLabels, values: eventValues };
  }
  const labels = Array.isArray(metrics?.equityCurveLabels) ? metrics.equityCurveLabels : [];
  const values = Array.isArray(metrics?.equityCurveValues) ? metrics.equityCurveValues : [];
  if (labels.length >= 2 && values.length === labels.length) {
    return { labels, values };
  }
  return { labels: [], values: [] };
}

function valueAt(labels, values, date) {
  const idx = labels.indexOf(String(date));
  if (idx < 0) return null;
  const n = Number(values[idx]);
  return Number.isFinite(n) ? n : null;
}

function formatLifecycleTooltip(life, palette) {
  if (!life) return '';
  const lines = [
    escapeHtml(stockLabel(life)),
    `开仓：${formatReportChartDateLabel(life.buy?.date)} · ${formatReportMoney(life.buy?.price)}`,
  ];
  const shares = Number(life.buy?.shares);
  if (Number.isFinite(shares)) {
    lines[1] += ` · ${shares.toLocaleString()}股`;
  }
  if (life.outcome === 'open' || !life.endDate) {
    lines.push('终点：未平仓');
  } else {
    const endSell = life.sells[life.sells.length - 1];
    lines.push(
      `终点：${formatReportChartDateLabel(life.endDate)} · ${formatReportMoney(endSell?.price)}`,
    );
    if (Number.isFinite(Number(life.profit))) {
      const sign = life.profit >= 0 ? '+' : '';
      const color = outcomeColor(life.outcome, palette);
      lines.push(
        `盈亏：<span style="color:${color}">${sign}${formatReportMoney(life.profit)}</span>`,
      );
    }
    if (life.sells.length > 1) {
      lines.push(`分批卖出 ${life.sells.length} 次（悬停已画出各次）`);
    }
  }
  return lines.join('<br/>');
}

function formatSellTooltip(sell, life, palette) {
  const p = Number(sell?.profit);
  const color = sellPointColor(sell, life, palette);
  const lines = [
    escapeHtml(stockLabel(life)),
    `卖出：${formatReportChartDateLabel(sell?.date)} · ${formatReportMoney(sell?.price)}`,
  ];
  const shares = Number(sell?.shares);
  if (Number.isFinite(shares)) {
    lines[1] += ` · ${shares.toLocaleString()}股`;
  }
  if (Number.isFinite(p)) {
    const sign = p >= 0 ? '+' : '';
    lines.push(`本笔盈亏：<span style="color:${color}">${sign}${formatReportMoney(p)}</span>`);
  }
  return lines.join('<br/>');
}

function startDotStyle(color, shadowRgb, { active, dim }) {
  if (active) {
    return marketMarkerPinStyle(color, shadowRgb);
  }
  return {
    color,
    borderColor: 'rgba(255,255,255,0.85)',
    borderWidth: 1,
    opacity: dim ? 0.22 : 0.92,
    shadowBlur: 0,
  };
}

function investmentBasis(life) {
  const cost = Number(life?.buy?.cost);
  if (Number.isFinite(cost) && cost > 0) return cost;
  const px = Number(life?.buy?.price);
  const shares = Number(life?.buy?.shares);
  if (Number.isFinite(px) && px > 0 && Number.isFinite(shares) && shares > 0) {
    return px * shares;
  }
  return null;
}

function parseYmd(value) {
  const s = String(value || '').trim();
  if (!/^\d{8}$/.test(s)) return null;
  const y = Number(s.slice(0, 4));
  const m = Number(s.slice(4, 6));
  const d = Number(s.slice(6, 8));
  const dt = new Date(y, m - 1, d);
  if (dt.getFullYear() !== y || dt.getMonth() !== m - 1 || dt.getDate() !== d) return null;
  return dt;
}

/** 含首尾的日历持有天数；缺一端返回 null */
export function holdingCalendarDays(startDate, endDate) {
  const a = parseYmd(startDate);
  const b = parseYmd(endDate);
  if (!a || !b) return null;
  const diff = Math.round((b.getTime() - a.getTime()) / 86400000);
  if (diff < 0) return null;
  return diff + 1;
}

/** `{start} - {end}：共N天`；未平仓为 `{start} - 未平仓` */
export function formatHoldingPeriodLabel(startDate, endDate, { open = false } = {}) {
  const start = formatReportChartDateLabel(startDate);
  if (!start) return '—';
  if (open || !endDate) return `${start} - 未平仓`;
  const end = formatReportChartDateLabel(endDate);
  const days = holdingCalendarDays(startDate, endDate);
  if (!end) return start;
  if (!Number.isFinite(days)) return `${start} - ${end}`;
  return `${start} - ${end}：共${days}天`;
}

/**
 * DataGrid 行：一笔投资生命周期。
 */
export function buildTradeLifecycleTableRows(tradeEvents) {
  return pairTradeLifecycles(tradeEvents).map((life) => {
    const buyPx = Number(life.buy?.price);
    const shares = Number(life.buy?.shares);
    const basis = investmentBasis(life);
    const exitPrice = life.sells.length
      ? Number(life.sells[life.sells.length - 1]?.price)
      : null;
    let returnPct = null;
    if (life.outcome !== 'open' && Number.isFinite(Number(life.profit)) && Number.isFinite(basis) && basis > 0) {
      returnPct = (Number(life.profit) / basis) * 100;
    } else if (
      life.outcome !== 'open'
      && Number.isFinite(buyPx)
      && buyPx > 0
      && Number.isFinite(exitPrice)
    ) {
      returnPct = ((exitPrice - buyPx) / buyPx) * 100;
    }
    const startDate = String(life.buy?.date || '').trim();
    const endDate = life.endDate ? String(life.endDate) : null;
    const open = life.outcome === 'open';
    return {
      id: life.id,
      lifecycleId: life.id,
      entityId: life.entityId || '',
      stockName: life.stockName || life.entityId || '',
      startDate,
      endDate,
      holdingDays: open ? null : holdingCalendarDays(startDate, endDate),
      holdingLabel: formatHoldingPeriodLabel(startDate, endDate, { open }),
      shares: Number.isFinite(shares) ? shares : 0,
      buyPrice: Number.isFinite(buyPx) ? buyPx : null,
      cost: Number.isFinite(basis) ? basis : null,
      exitPrice: Number.isFinite(exitPrice) ? exitPrice : null,
      returnPct: Number.isFinite(returnPct) ? returnPct : null,
      profit: (() => {
        const p = Number(life.profit);
        return life.outcome !== 'open' && Number.isFinite(p) ? p : null;
      })(),
      outcome: life.outcome,
      open,
      sellCount: life.sells.length,
    };
  });
}

function sliceCurveAround(labels, values, startDate, endDate, pad = 20) {
  const i0 = labels.indexOf(String(startDate));
  if (i0 < 0) return { labels, values };
  const i1raw = endDate ? labels.indexOf(String(endDate)) : i0;
  const i1 = i1raw >= 0 ? i1raw : i0;
  const from = Math.max(0, Math.min(i0, i1) - pad);
  const to = Math.min(labels.length - 1, Math.max(i0, i1) + pad);
  return {
    labels: labels.slice(from, to + 1),
    values: values.slice(from, to + 1),
  };
}

/**
 * @param {object} metrics
 * @param {{ activeLifecycleId?: string|null, focusLifecycleId?: string|null }} [overlay]
 *   focusLifecycleId：只画该笔（全屏审阅）；activeLifecycleId：hover 高亮
 */
export function buildPortfolioTradeLifecycleChartOption(metrics, overlay = {}) {
  const full = pickCurve(metrics);
  if (full.labels.length < 2) return null;

  const palette = resolveMarketPnlPalette(metrics?.marketProfile || metrics?.market_profile);
  const lifecycles = pairTradeLifecycles(metrics?.tradeEvents);
  if (!lifecycles.length) return null;

  const focusId = String(overlay?.focusLifecycleId || '').trim();
  const focus = focusId ? lifecycles.find((life) => life.id === focusId) : null;

  let labels = full.labels;
  let values = full.values;
  if (focus) {
    const sliced = sliceCurveAround(
      full.labels,
      full.values,
      focus.buy?.date,
      focus.endDate,
      20,
    );
    labels = sliced.labels;
    values = sliced.values;
  }

  const labelIndex = new Map(labels.map((d, i) => [String(d), i]));
  const { min: yMin, max: yMax } = equityAxisMinMax(values);
  const positive = equityResultIsPositive(metrics);
  const lineColor = positive ? palette.profit : palette.loss;
  const areaColor = positive
    ? (palette.polarity === 'cn' ? 'rgba(255, 77, 103, 0.10)' : 'rgba(0, 217, 165, 0.10)')
    : (palette.polarity === 'cn' ? 'rgba(0, 217, 165, 0.10)' : 'rgba(255, 77, 103, 0.10)');

  const activeId = focusId || String(overlay?.activeLifecycleId || '').trim();
  const active = activeId
    ? lifecycles.find((life) => life.id === activeId)
    : null;
  const hasActive = Boolean(active);
  const focusedMode = Boolean(focus);

  const dayCount = new Map();
  const startData = [];
  const sourceLives = focusedMode ? [focus] : lifecycles;

  sourceLives.forEach((life) => {
    if (!life) return;
    const start = String(life.buy?.date || '').trim();
    if (!start || !labelIndex.has(start)) return;
    const y = valueAt(labels, values, start);
    if (y == null) return;
    const n = dayCount.get(start) || 0;
    dayCount.set(start, n + 1);
    const span = (Number.isFinite(yMax) && Number.isFinite(yMin))
      ? Math.max(yMax - yMin, 1)
      : Math.abs(y) || 1;
    const yOff = focusedMode ? 0 : (n % 5) * span * 0.012;
    const isActive = focusedMode || (hasActive && life.id === active.id);
    const isDim = !focusedMode && hasActive && !isActive;
    const color = outcomeColor(life.outcome, palette);
    startData.push({
      value: [start, y + yOff],
      lifecycle: life,
      symbol: isActive ? MARKET_MARKER_PIN_UP : 'circle',
      symbolSize: isActive
        ? MARKET_MARKER_PIN_SIZE
        : (isDim ? START_DOT_SIZE_DIM : START_DOT_SIZE),
      symbolOffset: isActive ? [0, MARKET_MARKER_PIN_OFFSET_UP] : [0, 0],
      itemStyle: startDotStyle(color, outcomeShadow(life.outcome, palette), {
        active: isActive,
        dim: isDim,
      }),
    });
  });

  if (!startData.length) return null;

  const eventData = [];
  let markLineData = [];
  let markAreaData = [];

  if (active) {
    const startDate = String(active.buy?.date || '').trim();
    active.sells.forEach((sell, idx) => {
      const date = String(sell?.date || '').trim();
      if (!date || !labelIndex.has(date)) return;
      const y = valueAt(labels, values, date);
      if (y == null) return;
      const color = sellPointColor(sell, active, palette);
      const isLast = idx === active.sells.length - 1;
      eventData.push({
        value: [date, y],
        lifecycle: active,
        sell,
        itemStyle: marketMarkerPinStyle(color, outcomeShadow(
          Number.isFinite(Number(sell?.profit)) && Number(sell.profit) < 0 ? 'loss' : 'profit',
          palette,
        )),
        symbolSize: isLast ? MARKET_MARKER_PIN_SIZE + 2 : MARKET_MARKER_PIN_SIZE,
      });
    });

    if (startDate && labelIndex.has(startDate)) {
      markLineData.push({
        xAxis: startDate,
        lineStyle: { color: palette.buy, type: 'dashed', width: 1, opacity: 0.55 },
      });
    }
    if (active.endDate && labelIndex.has(String(active.endDate))) {
      const endColor = outcomeColor(active.outcome, palette);
      markLineData.push({
        xAxis: String(active.endDate),
        lineStyle: { color: endColor, type: 'dashed', width: 1.25, opacity: 0.85 },
      });
      if (startDate && labelIndex.has(startDate)) {
        markAreaData = [[
          { xAxis: startDate },
          { xAxis: String(active.endDate) },
        ]];
      }
    }
  }

  const areaTint = active
    ? (active.outcome === 'loss'
      ? (palette.polarity === 'cn' ? 'rgba(0, 217, 165, 0.08)' : 'rgba(255, 77, 103, 0.08)')
      : active.outcome === 'profit'
        ? (palette.polarity === 'cn' ? 'rgba(255, 77, 103, 0.08)' : 'rgba(0, 217, 165, 0.08)')
        : 'rgba(0, 229, 255, 0.06)')
    : 'transparent';

  return {
    animation: false,
    grid: {
      left: 44,
      right: 16,
      top: 28,
      bottom: focusedMode ? 48 : 36,
    },
    legend: {
      data: focusedMode ? ['总资产', '开仓', '事件'] : ['总资产', '开仓'],
      top: 0,
      left: 0,
      itemWidth: 14,
      itemHeight: 14,
      textStyle: { color: 'rgba(255, 255, 255, 0.72)', fontSize: 11 },
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisTick: { show: false },
      axisLine: REPORT_CHART_AXIS_LINE,
      axisLabel: {
        ...REPORT_CHART_AXIS_LABEL,
        formatter: (v) => formatReportChartDateLabel(v),
      },
      axisPointer: { show: true, label: { show: false } },
    },
    yAxis: {
      type: 'value',
      ...((yMin !== undefined && yMax !== undefined) ? { min: yMin, max: yMax } : {}),
      splitNumber: 3,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        ...REPORT_CHART_AXIS_LABEL,
        formatter: (value) => formatEquityAxisWan(value, yMin, yMax),
      },
      splitLine: REPORT_CHART_SPLIT_LINE,
    },
    dataZoom: focusedMode
      ? [
        {
          type: 'slider',
          xAxisIndex: 0,
          height: 16,
          bottom: 6,
          brushSelect: false,
          filterMode: 'none',
          borderColor: 'rgba(255, 255, 255, 0.14)',
          fillerColor: 'rgba(255, 255, 255, 0.14)',
          handleStyle: { color: 'rgba(255, 255, 255, 0.72)' },
          textStyle: { color: 'rgba(255, 255, 255, 0.58)', fontSize: 10 },
        },
      ]
      : [
        {
          type: 'inside',
          xAxisIndex: 0,
          filterMode: 'none',
          zoomOnMouseWheel: false,
          moveOnMouseWheel: false,
          moveOnMouseMove: false,
        },
      ],
    tooltip: {
      ...REPORT_CHART_TOOLTIP,
      trigger: 'item',
      confine: true,
      formatter: (params) => {
        const name = String(params?.seriesName || '');
        if (name === '事件') {
          return formatSellTooltip(params?.data?.sell, params?.data?.lifecycle, palette);
        }
        return formatLifecycleTooltip(params?.data?.lifecycle, palette);
      },
    },
    series: [
      {
        name: '总资产',
        type: 'line',
        data: values,
        smooth: true,
        symbol: 'none',
        color: lineColor,
        lineStyle: { width: 1.5, color: lineColor, opacity: 0.85 },
        areaStyle: { color: areaColor },
        tooltip: { show: false },
        z: 1,
      },
      {
        name: '持有指引',
        type: 'line',
        data: [],
        silent: true,
        tooltip: { show: false },
        markLine: {
          symbol: 'none',
          silent: true,
          label: { show: false },
          data: markLineData,
        },
        markArea: {
          silent: true,
          itemStyle: { color: areaTint },
          data: markAreaData,
        },
        z: 2,
      },
      {
        name: '开仓',
        type: 'scatter',
        data: startData,
        symbol: 'circle',
        symbolSize: START_DOT_SIZE,
        color: palette.buy,
        z: 5,
      },
      {
        name: '事件',
        type: 'scatter',
        data: eventData,
        symbol: MARKET_MARKER_PIN_DOWN,
        symbolSize: MARKET_MARKER_PIN_SIZE,
        symbolOffset: [0, MARKET_MARKER_PIN_OFFSET_DOWN],
        color: palette.sell,
        z: 6,
      },
    ],
  };
}

function stockLabelFromLife(life) {
  const code = String(life?.entityId || '').trim();
  const name = String(life?.stockName || '').trim();
  if (name && code && name !== code) return `${name}(${code})`;
  return name || code || '未知';
}

/** 整表事件图开仓点：三档大小（按合并后盈亏金额绝对值） */
export const OVERVIEW_DOT_SIZE = {
  small: 8,
  medium: 13,
  large: 18,
};

/**
 * 同日合并后的总盈亏（金额，非 ROI）。
 * 仅累加已平仓笔；全未平仓 → profit null / outcome open。
 */
export function summarizeOverviewDayLives(lives) {
  let sum = 0;
  let closed = 0;
  let openCount = 0;
  (lives || []).forEach((life) => {
    const p = Number(life?.profit);
    if (life?.outcome === 'open' || !Number.isFinite(p)) {
      openCount += 1;
      return;
    }
    closed += 1;
    sum += p;
  });
  if (!closed) {
    return {
      profit: null,
      absProfit: 0,
      outcome: 'open',
      closedCount: 0,
      openCount,
      count: (lives || []).length,
    };
  }
  let outcome = 'flat';
  if (sum > 0) outcome = 'profit';
  else if (sum < 0) outcome = 'loss';
  return {
    profit: sum,
    absProfit: Math.abs(sum),
    outcome,
    closedCount: closed,
    openCount,
    count: (lives || []).length,
  };
}

/** 相对本图最大 |盈亏| 切成小 / 中 / 大三档 */
export function overviewDotSizeForAbsProfit(absProfit, maxAbs) {
  const abs = Number(absProfit);
  const max = Number(maxAbs);
  if (!Number.isFinite(abs) || abs <= 0 || !Number.isFinite(max) || max <= 0) {
    return OVERVIEW_DOT_SIZE.small;
  }
  if (abs <= max / 3) return OVERVIEW_DOT_SIZE.small;
  if (abs <= (2 * max) / 3) return OVERVIEW_DOT_SIZE.medium;
  return OVERVIEW_DOT_SIZE.large;
}

function overviewDayColor(outcome, palette) {
  if (outcome === 'loss') return palette.loss;
  if (outcome === 'profit') return palette.profit;
  return palette.neutral;
}

function overviewDayShadow(outcome, palette) {
  if (outcome === 'loss') return palette.shadow.loss;
  if (outcome === 'profit') return palette.shadow.profit;
  return palette.shadow.neutral;
}

function formatOverviewDayTooltip(point, palette) {
  const lives = Array.isArray(point?.lifecycles) ? point.lifecycles : [];
  const date = point?.value?.[0];
  const summary = point?.summary || summarizeOverviewDayLives(lives);
  let head = `${formatReportChartDateLabel(date)} · 开仓 ${lives.length} 笔`;
  if (summary.outcome === 'open') {
    head += ' · 未平仓';
  } else if (Number.isFinite(Number(summary.profit))) {
    const sign = summary.profit > 0 ? '+' : '';
    const color = overviewDayColor(summary.outcome, palette);
    head += ` · <span style="color:${color}">合计 ${sign}${formatReportMoney(summary.profit)}</span>`;
  }
  const lines = [head];
  lives.slice(0, 12).forEach((life) => {
    const shares = Number(life?.buy?.shares);
    const shareText = Number.isFinite(shares) ? `${shares.toLocaleString()}股` : '—股';
    const px = formatReportMoney(life?.buy?.price);
    let tail = '';
    if (life.outcome === 'open') {
      tail = '未平仓';
    } else if (Number.isFinite(Number(life.profit))) {
      const sign = life.profit >= 0 ? '+' : '';
      const color = outcomeColor(life.outcome, palette);
      tail = `<span style="color:${color}">${sign}${formatReportMoney(life.profit)}</span>`;
    }
    lines.push(
      `${escapeHtml(stockLabelFromLife(life))} · ${escapeHtml(shareText)} · ${escapeHtml(px)}`
      + (tail ? ` · ${tail}` : ''),
    );
  });
  if (lives.length > 12) {
    lines.push(`…另有 ${lives.length - 12} 笔`);
  }
  return lines.join('<br/>');
}

/**
 * 整表事件图：净值曲线 + 仅开仓起点；同日多笔合并。
 * 点色按合并后总盈亏（赚红亏绿），点大小按 |盈亏金额| 三档。
 */
export function buildPortfolioTradeOverviewChartOption(metrics) {
  const { labels, values } = pickCurve(metrics);
  if (labels.length < 2) return null;

  const palette = resolveMarketPnlPalette(metrics?.marketProfile || metrics?.market_profile);
  const lifecycles = pairTradeLifecycles(metrics?.tradeEvents);
  if (!lifecycles.length) return null;

  const labelIndex = new Map(labels.map((d, i) => [String(d), i]));
  const { min: yMin, max: yMax } = equityAxisMinMax(values);
  // 资金线用中性灰白，避开红/绿盈亏点与买卖色
  const lineColor = 'rgba(226, 232, 240, 0.88)';
  const areaColor = 'rgba(226, 232, 240, 0.08)';

  const byDate = new Map();
  lifecycles.forEach((life) => {
    const start = String(life.buy?.date || '').trim();
    if (!start || !labelIndex.has(start)) return;
    let bucket = byDate.get(start);
    if (!bucket) {
      bucket = [];
      byDate.set(start, bucket);
    }
    bucket.push(life);
  });

  const drafts = [];
  let maxAbs = 0;
  byDate.forEach((lives, date) => {
    const y = valueAt(labels, values, date);
    if (y == null) return;
    const summary = summarizeOverviewDayLives(lives);
    if (summary.absProfit > maxAbs) maxAbs = summary.absProfit;
    drafts.push({ date, y, lives, summary });
  });

  const startData = drafts.map(({ date, y, lives, summary }) => {
    const color = overviewDayColor(summary.outcome, palette);
    const symbolSize = overviewDotSizeForAbsProfit(summary.absProfit, maxAbs);
    return {
      value: [date, y],
      lifecycles: lives,
      summary,
      count: summary.count,
      profit: summary.profit,
      absProfit: summary.absProfit,
      outcome: summary.outcome,
      symbolSize,
      itemStyle: {
        color,
        borderColor: 'rgba(255,255,255,0.9)',
        borderWidth: 1.5,
        shadowBlur: symbolSize >= OVERVIEW_DOT_SIZE.large ? 8 : 0,
        shadowColor: `rgba(${overviewDayShadow(summary.outcome, palette)}, 0.55)`,
      },
    };
  });

  if (!startData.length) return null;

  return {
    animation: false,
    grid: {
      left: 48,
      right: 20,
      top: 36,
      bottom: 52,
    },
    legend: {
      data: ['总资产', '开仓'],
      top: 0,
      left: 0,
      itemWidth: 14,
      itemHeight: 14,
      textStyle: { color: 'rgba(255, 255, 255, 0.72)', fontSize: 11 },
    },
    toolbox: {
      right: 8,
      top: 0,
      itemSize: 14,
      iconStyle: { borderColor: 'rgba(255, 255, 255, 0.72)' },
      feature: {
        restore: { title: '还原缩放' },
      },
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisTick: { show: false },
      axisLine: REPORT_CHART_AXIS_LINE,
      axisLabel: {
        ...REPORT_CHART_AXIS_LABEL,
        formatter: (v) => formatReportChartDateLabel(v),
      },
      axisPointer: { show: true, label: { show: false } },
    },
    yAxis: {
      type: 'value',
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
    dataZoom: [
      {
        type: 'slider',
        xAxisIndex: 0,
        height: 18,
        bottom: 8,
        brushSelect: false,
        filterMode: 'none',
        borderColor: 'rgba(255, 255, 255, 0.14)',
        fillerColor: 'rgba(255, 255, 255, 0.14)',
        handleStyle: { color: 'rgba(255, 255, 255, 0.72)' },
        textStyle: { color: 'rgba(255, 255, 255, 0.58)', fontSize: 10 },
      },
      {
        type: 'inside',
        xAxisIndex: 0,
        filterMode: 'none',
        zoomOnMouseWheel: false,
        moveOnMouseWheel: false,
        moveOnMouseMove: false,
      },
    ],
    tooltip: {
      ...REPORT_CHART_TOOLTIP,
      trigger: 'item',
      confine: true,
      formatter: (params) => {
        if (String(params?.seriesName || '') !== '开仓') return '';
        return formatOverviewDayTooltip(params?.data, palette);
      },
    },
    series: [
      {
        name: '总资产',
        type: 'line',
        data: values,
        smooth: true,
        symbol: 'none',
        color: lineColor,
        lineStyle: { width: 2, color: lineColor, opacity: 0.9 },
        areaStyle: { color: areaColor },
        tooltip: { show: false },
        z: 1,
      },
      {
        name: '开仓',
        type: 'scatter',
        data: startData,
        symbol: 'circle',
        symbolSize: (val) => val?.symbolSize || START_DOT_SIZE,
        color: palette.buy,
        z: 5,
      },
    ],
  };
}
