/**
 * Attribution facts → display labels / chart option (FED copy only).
 */

import {
  REPORT_CHART_AXIS_LABEL,
  REPORT_CHART_AXIS_LINE,
  REPORT_CHART_BAR_COLOR_POS,
  REPORT_CHART_BAR_SHADOW,
  REPORT_CHART_DATA_LABEL,
  REPORT_CHART_GRID_BASE,
  REPORT_CHART_SPLIT_LINE,
  REPORT_CHART_TOOLTIP,
  reportChartSignedBarData,
} from './reportChartsTheme';

const HERO_BAR_COLOR_WEAK = '#fb923c';

export function asFiniteNumber(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

export function formatRoiPct(value) {
  const n = asFiniteNumber(value);
  if (n == null) return '—';
  return `${(n * 100).toFixed(1)}%`;
}

export function formatWinPct(value) {
  const n = asFiniteNumber(value);
  if (n == null) return '—';
  return `${(n * 100).toFixed(0)}%`;
}

export function formatNum(value, digits = 2) {
  const n = asFiniteNumber(value);
  if (n == null) return '—';
  return n.toFixed(digits);
}

export function formatPValue(value) {
  const n = asFiniteNumber(value);
  if (n == null) return '—';
  if (n === 0) return '0';
  if (n < 0.001) return n.toExponential(1);
  return n.toFixed(3);
}

export function formatCount(value) {
  const n = asFiniteNumber(value);
  if (n == null) return '—';
  return Math.round(n).toLocaleString();
}

export function stripCornerQuotes(text) {
  return String(text || '').replace(/[「」]/g, '');
}

export function formatPlain(value) {
  if (value == null) return '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

/** 相关方向：只描述数值升高时收益倾向，不点名具体字段。 */
export function correlationDirection(rho) {
  const n = asFiniteNumber(rho);
  if (n == null) return { label: '—', tone: 'neutral' };
  if (Math.abs(n) < 0.05) return { label: '关系很弱', tone: 'neutral' };
  if (n < 0) return { label: '越高，收益往往越低', tone: 'neg' };
  return { label: '越高，收益往往越高', tone: 'pos' };
}

export function significanceLabel(pValue) {
  const n = asFiniteNumber(pValue);
  if (n == null) return { label: '—', tone: 'neutral' };
  if (n < 0.01) return { label: '显著', tone: 'pos' };
  if (n < 0.05) return { label: '较显著', tone: 'pos' };
  return { label: '不显著', tone: 'neutral' };
}

export function sampleSizeFromFacts(facts) {
  const fromTech = asFiniteNumber(facts?.technical?.sample_size);
  if (fromTech != null) return fromTech;
  const source = Array.isArray(facts?.buckets) && facts.buckets.length
    ? facts.buckets
    : (Array.isArray(facts?.tiers) ? facts.tiers : []);
  let sum = 0;
  let any = false;
  source.forEach((row) => {
    const n = asFiniteNumber(row?.count);
    if (n != null) {
      sum += n;
      any = true;
    }
  });
  return any ? sum : null;
}

export function maxAbs(values) {
  let max = 0;
  (Array.isArray(values) ? values : []).forEach((value) => {
    const n = asFiniteNumber(value);
    if (n != null) max = Math.max(max, Math.abs(n));
  });
  return max;
}

export function rankFillPct(value, peak) {
  const n = asFiniteNumber(value);
  if (n == null || !(peak > 0)) return 0;
  return Math.max(4, Math.round((Math.abs(n) / peak) * 100));
}

export function multivariateKindLabel(kind) {
  if (kind === 'win') return '对胜率';
  if (kind === 'roi') return '对收益';
  return '';
}

export function sameBinning(left, right) {
  const a = Array.isArray(left) ? left : [];
  const b = Array.isArray(right) ? right : [];
  if (!a.length || a.length !== b.length) return false;
  return a.every((row, i) => {
    const other = b[i];
    if (!row || !other) return false;
    return String(row.label || '') === String(other.label || '')
      && asFiniteNumber(row.mean_roi) === asFiniteNumber(other.mean_roi)
      && asFiniteNumber(row.count) === asFiniteNumber(other.count);
  });
}

export function buildRoiBarOption(rows, { barMaxWidth = 36, rotate = 0 } = {}) {
  const list = Array.isArray(rows) ? rows.filter((t) => t && typeof t === 'object') : [];
  const labels = list.map((t) => String(t.label || '?').trim() || '?');
  const roiPct = list.map((t) => {
    const n = asFiniteNumber(t.mean_roi);
    return n == null ? 0 : n * 100;
  });
  const counts = list.map((t) => asFiniteNumber(t.count));
  const winRates = list.map((t) => asFiniteNumber(t.win_rate));
  const ranges = list.map((t) => {
    const lo = asFiniteNumber(t.min);
    const hi = asFiniteNumber(t.max);
    if (lo == null && hi == null) return '';
    if (lo != null && hi != null) return `${lo}~${hi}`;
    return String(lo ?? hi);
  });
  return {
    animation: false,
    grid: { ...REPORT_CHART_GRID_BASE, left: 42, top: 28, bottom: rotate ? 44 : 32 },
    xAxis: {
      type: 'category',
      data: labels,
      axisTick: { show: false },
      axisLine: REPORT_CHART_AXIS_LINE,
      axisLabel: {
        ...REPORT_CHART_AXIS_LABEL,
        interval: 0,
        rotate,
      },
    },
    yAxis: {
      type: 'value',
      splitNumber: 3,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        ...REPORT_CHART_AXIS_LABEL,
        formatter: (value) => `${value}%`,
      },
      splitLine: REPORT_CHART_SPLIT_LINE,
    },
    series: [
      {
        type: 'bar',
        data: reportChartSignedBarData(roiPct),
        barMaxWidth,
        label: {
          show: true,
          position: 'top',
          ...REPORT_CHART_DATA_LABEL,
          formatter: (params) => {
            const n = Number(params?.value ?? 0);
            return `${n.toFixed(1)}%`;
          },
        },
      },
    ],
    tooltip: {
      ...REPORT_CHART_TOOLTIP,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        const idx = Number(point.dataIndex ?? -1);
        const roi = Number(point.value ?? 0);
        const n = idx >= 0 ? counts[idx] : null;
        const win = idx >= 0 ? winRates[idx] : null;
        const range = idx >= 0 ? ranges[idx] : '';
        const lines = [String(point.axisValue || '')];
        if (range && range !== point.axisValue) lines.push(`区间：${range}`);
        lines.push(`平均收益：${roi.toFixed(1)}%`);
        if (win != null) lines.push(`胜率：${(win * 100).toFixed(0)}%`);
        if (n != null) lines.push(`样本：${Math.round(n).toLocaleString()}`);
        return lines.join('<br/>');
      },
    },
  };
}

export function buildTierRoiOption(tiers) {
  return buildRoiBarOption(tiers, { barMaxWidth: 48 });
}

export function formatRange(min, max, digits = 1) {
  const lo = asFiniteNumber(min);
  const hi = asFiniteNumber(max);
  if (lo == null && hi == null) return '';
  if (lo != null && hi != null) return `${formatNum(lo, digits)}~${formatNum(hi, digits)}`;
  return String(lo ?? hi);
}

export function rowsExtent(rows) {
  let lo = null;
  let hi = null;
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    const a = asFiniteNumber(row?.min);
    const b = asFiniteNumber(row?.max);
    if (a != null) lo = lo == null ? a : Math.min(lo, a);
    if (b != null) hi = hi == null ? b : Math.max(hi, b);
  });
  return { min: lo, max: hi };
}

export function splitValueFromTiers(tiers) {
  const rows = Array.isArray(tiers) ? tiers.filter((row) => row && typeof row === 'object') : [];
  if (rows.length !== 2) return null;
  return asFiniteNumber(rows[1]?.min) ?? asFiniteNumber(rows[0]?.max);
}

export function highlightCardsFromTiers({ tiers, buckets }) {
  const merged = Array.isArray(tiers) ? tiers.filter((row) => row && typeof row === 'object') : [];
  const fine = Array.isArray(buckets) ? buckets.filter((row) => row && typeof row === 'object') : [];
  const source = merged.length >= 2 ? merged : fine;
  if (source.length < 2) return [];
  const rois = source.map((row) => asFiniteNumber(row.mean_roi)).filter((n) => n != null);
  const wins = source.map((row) => asFiniteNumber(row.win_rate)).filter((n) => n != null);
  const cards = [];
  if (rois.length >= 2) {
    const best = Math.max(...rois);
    const worst = Math.min(...rois);
    if (worst > 0.0005) {
      const x = best / worst;
      cards.push({
        key: 'roi',
        value: `${x.toFixed(1)}x`,
        caption: `收益更好的那一档是较弱一档的 ${x.toFixed(1)} 倍`,
        tone: 'pos',
      });
    } else {
      const gap = (best - worst) * 100;
      cards.push({
        key: 'roi',
        value: `${gap >= 0 ? '+' : ''}${gap.toFixed(1)}%`,
        caption: '最好档与最弱档的平均收益差距',
        tone: gap >= 0 ? 'pos' : 'neg',
      });
    }
  }
  if (wins.length >= 2) {
    const best = Math.max(...wins);
    const worst = Math.min(...wins);
    const gap = (best - worst) * 100;
    cards.push({
      key: 'win',
      value: `${Math.abs(gap).toFixed(0)}%`,
      caption: `胜率差距：${(best * 100).toFixed(0)}% vs ${(worst * 100).toFixed(0)}%`,
      tone: 'info',
    });
  }
  if (merged.length >= 2 && fine.length > merged.length) {
    cards.push({
      key: 'bins',
      value: `${merged.length} 档`,
      caption: `实际有效分档（不是 ${fine.length} 档）`,
      tone: 'accent',
    });
  } else if (source.length >= 2) {
    cards.push({
      key: 'bins',
      value: `${source.length} 档`,
      caption: '按收益形态分成的档数',
      tone: 'accent',
    });
  }
  return cards;
}

export function buildHeroRoiOption(rows, { watershedLabel = '' } = {}) {
  const list = Array.isArray(rows) ? rows.filter((t) => t && typeof t === 'object') : [];
  const option = buildRoiBarOption(list, {
    barMaxWidth: list.length <= 2 ? 72 : 36,
    rotate: 0,
  });
  option.grid = { ...option.grid, left: 42, top: 44, bottom: 56 };
  option.xAxis = {
    ...option.xAxis,
    axisLabel: {
      ...REPORT_CHART_AXIS_LABEL,
      interval: 0,
      lineHeight: 16,
      formatter: (_value, idx) => {
        const row = list[idx];
        if (!row) return '';
        const range = formatRange(row.min, row.max) || String(row.label || '?');
        const n = asFiniteNumber(row.count);
        const win = asFiniteNumber(row.win_rate);
        const extra = [];
        if (n != null) extra.push(`${Math.round(n)} 笔`);
        if (win != null) extra.push(`${(win * 100).toFixed(0)}% 胜率`);
        return extra.length ? `${range}\n${extra.join(' · ')}` : range;
      },
    },
  };
  const rois = list.map((row) => {
    const n = asFiniteNumber(row.mean_roi);
    return n == null ? 0 : n * 100;
  });
  const allNonNeg = rois.length > 0 && rois.every((n) => n >= 0);
  if (allNonNeg && rois.length >= 2 && option.series?.[0]) {
    const best = Math.max(...rois);
    option.series[0].data = rois.map((n) => ({
      value: n,
      itemStyle: {
        color: n === best ? REPORT_CHART_BAR_COLOR_POS : HERO_BAR_COLOR_WEAK,
        borderRadius: [4, 4, 0, 0],
        ...REPORT_CHART_BAR_SHADOW,
      },
    }));
  }
  if (list.length === 2 && watershedLabel && option.series?.[0]) {
    option.series[0].markLine = {
      silent: true,
      symbol: 'none',
      animation: false,
      label: {
        formatter: watershedLabel,
        color: '#f87171',
        fontSize: 10,
        position: 'middle',
      },
      lineStyle: { type: 'dashed', color: 'rgba(248, 113, 113, 0.7)', width: 1 },
      data: [{ xAxis: 0.5 }],
    };
  }
  return option;
}
