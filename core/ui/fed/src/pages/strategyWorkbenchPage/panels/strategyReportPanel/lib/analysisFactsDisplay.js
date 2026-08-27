/**
 * Attribution facts → display labels / chart option (FED copy only).
 */

import {
  REPORT_CHART_AXIS_LABEL,
  REPORT_CHART_AXIS_LINE,
  REPORT_CHART_DATA_LABEL,
  REPORT_CHART_GRID_BASE,
  REPORT_CHART_SPLIT_LINE,
  REPORT_CHART_TOOLTIP,
  reportChartSignedBarData,
} from './reportChartsTheme';

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
