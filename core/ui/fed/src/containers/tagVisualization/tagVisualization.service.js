/** 甘特配色：同一取值固定同一颜色。 */
const LANE_PALETTE = [
  '#22d3ee',
  '#a78bfa',
  '#fbbf24',
  '#34d399',
  '#fb7185',
  '#60a5fa',
  '#f472b6',
  '#f97316',
];

const GANTT_BAR_HEIGHT = 18;
const ONE_DAY_MS = 24 * 60 * 60 * 1000;
const ZOOM_MONTHS = 6;
const AXIS_LABEL = { color: 'rgba(255, 255, 255, 0.72)', fontSize: 11 };
const AXIS_LINE = { lineStyle: { color: 'rgba(255, 255, 255, 0.18)' } };
const TIME_AXIS_FORMATTER = {
  year: '{yyyy}年',
  month: '{M}月',
  day: '{d}日',
};

export function tagValueColor(label) {
  const text = String(label || '');
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash + text.charCodeAt(i) * (i + 1)) % LANE_PALETTE.length;
  }
  return LANE_PALETTE[hash];
}

function toUtcMs(yyyymmdd) {
  const raw = String(yyyymmdd || '').replace(/-/g, '');
  if (!/^\d{8}$/.test(raw)) return NaN;
  return Date.UTC(
    Number(raw.slice(0, 4)),
    Number(raw.slice(4, 6)) - 1,
    Number(raw.slice(6, 8)),
  );
}

export function formatVizDate(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
  if (/^\d{8}$/.test(raw)) return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`;
  return raw;
}

function clipRect(rect, bound) {
  const x = Math.max(rect.x, bound.x);
  const y = Math.max(rect.y, bound.y);
  const x2 = Math.min(rect.x + rect.width, bound.x + bound.width);
  const y2 = Math.min(rect.y + rect.height, bound.y + bound.height);
  if (x2 <= x || y2 <= y) return null;
  return { x, y, width: x2 - x, height: y2 - y };
}

export function ganttBarShape(startPx, endPx, centerY, laneSpan, bound) {
  const span = Math.abs(Number(laneSpan) || 0);
  const barHeight = span > 0 ? Math.min(GANTT_BAR_HEIGHT, span * 0.72) : GANTT_BAR_HEIGHT;
  const x = Math.min(startPx, endPx);
  return clipRect(
    {
      x,
      y: centerY - barHeight / 2,
      width: Math.max(Math.abs(endPx - startPx), 2),
      height: barHeight,
    },
    bound,
  );
}

function renderGanttItem(params, api) {
  const categoryIndex = api.value(0);
  const start = api.coord([api.value(1), categoryIndex]);
  const end = api.coord([api.value(2), categoryIndex]);
  if (!start || !end) return null;
  const laneSpan = (api.size([0, 1]) || [])[1];
  const rect = ganttBarShape(start[0], end[0], start[1], laneSpan, params.coordSys);
  if (!rect) return null;
  const radius = Math.min(4, rect.height / 2, rect.width / 2);
  return {
    type: 'rect',
    shape: { ...rect, r: radius },
    style: api.style(),
  };
}

/**
 * 时序甘特。``intervals[].lane`` 是纵轴，``start`` / ``end`` 是 YYYYMMDD。
 * 无区间时返回 null。
 */
export function buildTagGanttOption(intervals, laneOrder) {
  const rows = Array.isArray(intervals) ? intervals : [];
  if (!rows.length) return null;
  const lanes = [];
  const laneIndex = new Map();
  const remember = (lane) => {
    if (!lane || laneIndex.has(lane)) return;
    laneIndex.set(lane, lanes.length);
    lanes.push(lane);
  };
  (Array.isArray(laneOrder) ? laneOrder : []).forEach((name) => remember(String(name || '').trim()));
  rows.forEach((item) => remember(String(item?.lane || '').trim()));
  const zoomWindow = ganttZoomWindow(rows) || {};
  const data = rows.map((item) => {
    const lane = String(item.lane || '').trim();
    const label = String(item.value_label || '');
    return {
      value: [
        laneIndex.get(lane),
        toUtcMs(item.start),
        toUtcMs(item.end),
        label,
      ],
      itemStyle: { color: tagValueColor(lane) },
    };
  });
  return {
    animation: false,
    backgroundColor: 'transparent',
    grid: { left: 96, right: 24, top: 16, bottom: 64 },
    tooltip: {
      trigger: 'item',
      formatter(params) {
        const value = params?.value || [];
        const lane = lanes[value[0]] || '';
        const label = value[3] || '';
        const start = formatVizDate(msToYyyymmdd(value[1]));
        const end = formatVizDate(msToYyyymmdd(value[2]));
        const valueLine = label && label !== lane ? `${label}<br/>` : '';
        return `${lane}<br/>${valueLine}${start} → ${end}`;
      },
    },
    xAxis: {
      type: 'time',
      minInterval: ONE_DAY_MS,
      axisLabel: { ...AXIS_LABEL, formatter: TIME_AXIS_FORMATTER },
      axisLine: AXIS_LINE,
      splitLine: { show: false },
    },
    yAxis: {
      type: 'category',
      data: lanes,
      inverse: true,
      axisLabel: AXIS_LABEL,
      axisLine: AXIS_LINE,
      splitLine: { show: false },
    },
    dataZoom: [
      {
        type: 'slider',
        xAxisIndex: 0,
        bottom: 8,
        height: 18,
        filterMode: 'none',
        ...zoomWindow,
      },
      { type: 'inside', xAxisIndex: 0, filterMode: 'none', ...zoomWindow },
    ],
    series: [
      {
        type: 'custom',
        renderItem: renderGanttItem,
        encode: { x: [1, 2], y: 0 },
        clip: true,
        data,
      },
    ],
  };
}

function addUtcMonths(ms, delta) {
  const date = new Date(ms);
  const day = date.getUTCDate();
  const shifted = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + delta, 1));
  const lastDay = new Date(Date.UTC(
    shifted.getUTCFullYear(),
    shifted.getUTCMonth() + 1,
    0,
  )).getUTCDate();
  shifted.setUTCDate(Math.min(day, lastDay));
  return shifted.getTime();
}

/** 跨度超过 6 个月时，窗口停在序列末端往前 6 个自然月。 */
function ganttZoomWindow(rows) {
  let minStart = Infinity;
  let maxEnd = -Infinity;
  rows.forEach((item) => {
    const start = toUtcMs(item?.start);
    const end = toUtcMs(item?.end);
    if (Number.isFinite(start)) minStart = Math.min(minStart, start);
    if (Number.isFinite(end)) maxEnd = Math.max(maxEnd, end);
  });
  if (!Number.isFinite(maxEnd)) return null;
  const startValue = addUtcMonths(maxEnd, -ZOOM_MONTHS);
  if (!Number.isFinite(minStart) || startValue <= minStart) return null;
  return { startValue, endValue: maxEnd };
}

function msToYyyymmdd(ms) {
  const time = Number(ms);
  if (!Number.isFinite(time)) return '';
  const date = new Date(time);
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, '0');
  const d = String(date.getUTCDate()).padStart(2, '0');
  return `${y}${m}${d}`;
}

/** 把「104只 · 上海、江苏 · 样例 000001.SZ · 未映射 3」拆成卡片字段。对不上就返回 null。 */
export function parseSnapshotNote(text) {
  const raw = String(text || '').trim();
  const countMatch = raw.match(/^(\d+)只/);
  if (!countMatch) return null;
  const provinces = [];
  const samples = [];
  let unmapped = null;
  raw.split(' · ').slice(1).forEach((part) => {
    const piece = part.trim();
    if (!piece) return;
    if (piece.startsWith('样例')) {
      samples.push(...piece.slice(2).split('、').map((item) => item.trim()).filter(Boolean));
      return;
    }
    if (piece.startsWith('未映射')) {
      const count = Number(piece.slice(3).trim());
      unmapped = Number.isFinite(count) ? count : null;
      return;
    }
    provinces.push(...piece.split('、').map((item) => item.trim()).filter(Boolean));
  });
  return {
    count: Number(countMatch[1]),
    provinces,
    samples,
    unmapped,
  };
}

/** 多条「N只」标量快照收成一块看板；夹杂别的形状时返回 null，沿用原来的块。 */
export function snapshotBoardCards(snapshots) {
  const rows = Array.isArray(snapshots) ? snapshots : [];
  if (!rows.length || rows.some((item) => item?.kind && item.kind !== 'scalar')) return null;
  const cards = rows.map((item) => {
    const parsed = parseSnapshotNote(item?.scalar);
    if (!parsed) return null;
    return {
      key: String(item.tag_name || item.tag_display_name || ''),
      name: String(item.tag_display_name || item.tag_name || ''),
      asOf: String(item.as_of || ''),
      ...parsed,
    };
  });
  if (cards.some((item) => !item)) return null;
  const total = cards.reduce((sum, item) => sum + item.count, 0);
  const asOfs = [...new Set(cards.map((item) => item.asOf).filter(Boolean))];
  return {
    total,
    asOf: asOfs.length === 1 ? asOfs[0] : '',
    cards: [...cards].sort(
      (a, b) => b.count - a.count || a.name.localeCompare(b.name, 'zh-CN'),
    ),
  };
}

export function countEntitiesByValue(entities) {
  const counts = new Map();
  (entities || []).forEach((row) => {
    const label = String(row?.value_label || '').trim() || '（空）';
    counts.set(label, (counts.get(label) || 0) + 1);
  });
  return [...counts.entries()]
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
}
