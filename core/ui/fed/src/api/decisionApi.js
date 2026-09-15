import request, { API_VERSION_PREFIX, HTTP_TIMEOUT_MS } from 'services/request';

function formatMoney(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  return n.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatWinRate(rate, sampleSize) {
  if (sampleSize != null && Number(sampleSize) <= 0) return '—';
  if (rate == null || !Number.isFinite(Number(rate))) return '—';
  return `${(Number(rate) * 100).toFixed(0)}%`;
}

function formatAvgRoi(roi, sampleSize) {
  if (sampleSize != null && Number(sampleSize) <= 0) return '—';
  if (roi == null || !Number.isFinite(Number(roi))) return '—';
  const n = Number(roi) * 100;
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(1)}%`;
}

function encodeStrategyPathSegments(strategyName) {
  return String(strategyName || '')
    .split('/')
    .filter(Boolean)
    .map((seg) => encodeURIComponent(seg))
    .join('/');
}

function apiDecisionSessions(strategyName) {
  const encoded = encodeStrategyPathSegments(strategyName);
  return `${API_VERSION_PREFIX}/strategy/${encoded}/decision/sessions`;
}

function withVersion(url, versionId) {
  const vid = String(versionId || '').trim();
  if (!vid) return url;
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}version=${encodeURIComponent(vid)}`;
}

function unwrapMessage(json) {
  return json?.message && typeof json.message === 'object' ? json.message : {};
}

/** BFF ``YYYYMMDD`` → 页面 ``YYYY-MM-DD``。 */
export function formatDecisionDate(raw) {
  const s = String(raw || '').trim();
  if (/^\d{8}$/.test(s)) return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`;
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
  return s;
}

export function readSimulationRange(settings) {
  const exec = settings?.simulation?.execution && typeof settings.simulation.execution === 'object'
    ? settings.simulation.execution
    : {};
  return {
    start: formatDecisionDate(exec.start_date),
    end: formatDecisionDate(exec.end_date),
  };
}

export function decisionLobbyPath(strategyName) {
  const key = String(strategyName || '').trim();
  if (!key) return '/decision';
  return `/decision?${new URLSearchParams({ strategy: key }).toString()}`;
}

export function decisionPlayPath({
  strategy,
  session,
  isNew = false,
  readonly = false,
} = {}) {
  const query = new URLSearchParams();
  if (strategy) query.set('strategy', String(strategy));
  if (isNew) query.set('new', '1');
  else if (session) query.set('session', String(session));
  if (readonly) query.set('readonly', '1');
  return `/decision/play?${query.toString()}`;
}

export function mapDecisionSessionRow(row) {
  const raw = row && typeof row === 'object' ? row : {};
  const dmId = String(raw.dm_id || raw.dmId || '').trim();
  return {
    id: dmId,
    dmId,
    status: String(raw.status || ''),
    date: formatDecisionDate(raw.current_date),
    updatedAt: String(raw.updated_at || ''),
  };
}

function mapStats(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const sampleSize = Number(raw.sample_size);
  return {
    sampleSize: Number.isFinite(sampleSize) ? sampleSize : 0,
    wins: Number(raw.wins) || 0,
    winRate: raw.win_rate,
    avgRoi: raw.avg_roi,
    winRateLabel: formatWinRate(raw.win_rate, raw.sample_size),
    avgRoiLabel: formatAvgRoi(raw.avg_roi, raw.sample_size),
  };
}

function mapOpportunity(row) {
  const raw = row && typeof row === 'object' ? row : {};
  const stats = mapStats(raw.stats);
  const localId = Number(raw.local_id) || 0;
  return {
    id: localId,
    ticker: String(raw.entity_id || ''),
    name: String(raw.name || ''),
    price: Number(raw.entry_price) || 0,
    wr: stats ? stats.winRateLabel : '—',
    roi: stats ? stats.avgRoiLabel : '—',
    stats,
    lotSize: Number.isFinite(Number(raw.lot_size)) && Number(raw.lot_size) > 0
      ? Number(raw.lot_size)
      : null,
    suggestedShares: raw.suggested_shares == null || !Number.isFinite(Number(raw.suggested_shares))
      ? null
      : Number(raw.suggested_shares),
  };
}

function mapExit(row) {
  const raw = row && typeof row === 'object' ? row : {};
  const profit = Number(raw.profit);
  const win = Number.isFinite(profit) ? profit >= 0 : true;
  const shares = Number(raw.shares) || 0;
  const reason = String(raw.reason || raw.goal_names || '').trim();
  const ticker = String(raw.entity_id || '');
  const name = String(raw.name || '');
  const date = formatDecisionDate(raw.date);
  const pnl = Number.isFinite(profit) ? formatMoney(profit) : '—';
  const sign = Number.isFinite(profit) && profit > 0 ? '+' : '';
  return {
    date,
    ticker,
    name,
    shares,
    profit: Number.isFinite(profit) ? profit : 0,
    win,
    text: `出场 ${ticker} ${name}  ${shares.toLocaleString()} 股  盈亏 ${sign}${pnl}${reason ? `  (${reason})` : ''}`,
  };
}

function picksFromDraft(draft) {
  const picks = {};
  (Array.isArray(draft) ? draft : []).forEach((line) => {
    const lid = Number(line?.local_id);
    const shares = Number(line?.shares);
    if (Number.isFinite(lid) && lid > 0 && Number.isFinite(shares) && shares > 0) {
      picks[lid] = shares;
    }
  });
  return picks;
}

export function mapDecisionSnapshot(message) {
  const m = message && typeof message === 'object' ? message : {};
  const asof = mapStats(m.asof_stats);
  const opps = (m.opportunities || []).map(mapOpportunity);
  const draft = Array.isArray(m.draft) ? m.draft : [];
  const bill = Array.isArray(m.bill) ? m.bill : [];
  const completed = Boolean(m.completed) || m.phase === 'completed';
  return {
    dmId: String(m.dm_id || ''),
    versionId: String(m.version_id || ''),
    strategyKey: String(m.strategy_key || ''),
    status: String(m.status || ''),
    phase: String(m.phase || ''),
    completed,
    clockDate: formatDecisionDate(m.current_date),
    startDate: formatDecisionDate(m.start_date),
    endDate: formatDecisionDate(m.end_date),
    cash: Number(m.cash) || 0,
    initialCash: Number(m.initial_cash) || 0,
    openPositionCount: Number(m.open_position_count) || 0,
    maxPortfolioSize: Number(m.max_portfolio_size) || 0,
    asof,
    opps,
    draft,
    picks: picksFromDraft(draft),
    bill: bill.map((line) => ({
      id: Number(line.local_id) || 0,
      ticker: String(line.entity_id || ''),
      name: String(line.name || ''),
      shares: Number(line.shares) || 0,
      price: Number(line.entry_price) || 0,
      notional: Number(line.notional) || 0,
    })),
    events: (m.exits || []).map(mapExit),
    reportAvailable: Boolean(m.report_available),
    hasOpps: opps.length > 0,
  };
}

export function mapDecisionHoldings(message) {
  const m = message && typeof message === 'object' ? message : {};
  const rows = Array.isArray(m.holdings) ? m.holdings : [];
  return rows.map((row, index) => {
    const shares = Number(row.shares) || 0;
    const close = row.close == null ? null : Number(row.close);
    const unrealized = row.unrealized == null ? null : Number(row.unrealized);
    const buyDate = formatDecisionDate(row.buy_date);
    const buyPrice = Number(row.buy_price);
    const cost = Number.isFinite(buyPrice) ? shares * buyPrice : null;
    const marketValue = close != null && Number.isFinite(close) ? shares * close : null;
    const pnlPct = cost && Number.isFinite(unrealized) && cost !== 0
      ? unrealized / cost
      : null;
    return {
      id: `${row.entity_id || 'h'}-${row.buy_date || index}`,
      ticker: String(row.entity_id || ''),
      name: String(row.name || ''),
      shares,
      buyDate,
      buyPrice: Number.isFinite(buyPrice) ? buyPrice : null,
      holdDays: Number(row.hold_days) || 0,
      close: close != null && Number.isFinite(close) ? close : null,
      cost,
      marketValue,
      unrealized: unrealized != null && Number.isFinite(unrealized) ? unrealized : null,
      pnlPct,
      goals: (Array.isArray(row.goals) ? row.goals : []).map(mapHoldingGoal),
    };
  });
}

function mapHoldingGoal(text) {
  const raw = String(text || '').trim();
  let kind = 'other';
  if (raw.startsWith('止盈')) kind = 'take_profit';
  else if (raw.startsWith('止损')) kind = 'stop_loss';
  else if (raw.startsWith('保护')) kind = 'protect';
  else if (raw.startsWith('到期')) kind = 'expiry';
  return {
    text: raw,
    kind,
    done: false,
  };
}

export function holdingsMarketValue(holdings) {
  return (holdings || []).reduce((sum, row) => sum + (Number(row.marketValue) || 0), 0);
}

export function infoRowsToCandles(rows) {
  return (Array.isArray(rows) ? rows : []).map((row) => {
    const date = String(row?.date || '').replace(/-/g, '');
    const open = Number(row.open);
    const close = Number(row.close);
    const high = Number(row.high);
    const low = Number(row.low);
    if (!/^\d{8}$/.test(date) || ![open, close].every(Number.isFinite)) return null;
    let hi = Number.isFinite(high) ? high : close;
    let lo = Number.isFinite(low) ? low : close;
    if (hi < lo) {
      const tmp = hi;
      hi = lo;
      lo = tmp;
    }
    return { date, open, close, high: hi, low: lo };
  }).filter(Boolean);
}

function mapIndicatorSeries(raw) {
  if (!Array.isArray(raw)) return [];
  return raw.map((row) => ({
    key: String(row?.key || ''),
    label: String(row?.label || row?.key || ''),
    panel: row?.panel === 'oscillator' ? 'oscillator' : 'overlay',
    color: row?.color || undefined,
    data: Array.isArray(row?.data)
      ? row.data.map((value) => (value == null || !Number.isFinite(Number(value)) ? null : Number(value)))
      : [],
  })).filter((row) => row.key);
}

const LONG = { timeoutMs: HTTP_TIMEOUT_MS.LONG };

export async function fetchDecisionSessions(strategyName, { versionId } = {}) {
  const json = await request.getJson(
    withVersion(apiDecisionSessions(strategyName), versionId),
    LONG,
  );
  const m = unwrapMessage(json);
  return {
    versionId: String(m.version_id || ''),
    strategyKey: String(m.strategy_key || ''),
    hasPortfolio: Boolean(m.has_portfolio),
    sessions: (m.sessions || []).map(mapDecisionSessionRow),
  };
}

export async function openDecisionSession(strategyName, {
  versionId,
  sessionId,
  newSession = false,
} = {}) {
  const body = {};
  if (versionId) body.version_id = String(versionId);
  if (sessionId) body.session_id = String(sessionId);
  if (newSession) body.new_session = true;
  const json = await request.postJson(apiDecisionSessions(strategyName), { body, ...LONG });
  return mapDecisionSnapshot(unwrapMessage(json));
}

export async function fetchDecisionSession(strategyName, sessionId, { versionId } = {}) {
  const json = await request.getJson(
    withVersion(`${apiDecisionSessions(strategyName)}/${encodeURIComponent(sessionId)}`, versionId),
    LONG,
  );
  return mapDecisionSnapshot(unwrapMessage(json));
}

export async function deleteDecisionSession(strategyName, sessionId, { versionId } = {}) {
  const json = await request.deleteJson(
    withVersion(`${apiDecisionSessions(strategyName)}/${encodeURIComponent(sessionId)}`, versionId),
  );
  return unwrapMessage(json);
}

export async function pickDecisionShares(strategyName, sessionId, { localId, shares, versionId } = {}) {
  const json = await request.postJson(
    `${apiDecisionSessions(strategyName)}/${encodeURIComponent(sessionId)}/pick`,
    {
      body: {
        local_id: Number(localId),
        shares: Number(shares) || 0,
        ...(versionId ? { version_id: String(versionId) } : {}),
      },
    },
  );
  return mapDecisionSnapshot(unwrapMessage(json));
}

export async function doneDecisionDay(strategyName, sessionId, { versionId } = {}) {
  const json = await request.postJson(
    `${apiDecisionSessions(strategyName)}/${encodeURIComponent(sessionId)}/done`,
    { body: versionId ? { version_id: String(versionId) } : {} },
  );
  return mapDecisionSnapshot(unwrapMessage(json));
}

export async function resetDecisionDraft(strategyName, sessionId, { versionId } = {}) {
  const json = await request.postJson(
    `${apiDecisionSessions(strategyName)}/${encodeURIComponent(sessionId)}/reset`,
    { body: versionId ? { version_id: String(versionId) } : {} },
  );
  return mapDecisionSnapshot(unwrapMessage(json));
}

export async function nextDecisionDay(strategyName, sessionId, { versionId } = {}) {
  const json = await request.postJson(
    `${apiDecisionSessions(strategyName)}/${encodeURIComponent(sessionId)}/next`,
    { body: versionId ? { version_id: String(versionId) } : {}, ...LONG },
  );
  return mapDecisionSnapshot(unwrapMessage(json));
}

export async function fetchDecisionHoldings(strategyName, sessionId, { versionId } = {}) {
  const json = await request.getJson(
    withVersion(
      `${apiDecisionSessions(strategyName)}/${encodeURIComponent(sessionId)}/holdings`,
      versionId,
    ),
    LONG,
  );
  return mapDecisionHoldings(unwrapMessage(json));
}

export async function fetchDecisionInfo(strategyName, sessionId, {
  target,
  n,
  columns,
  versionId,
} = {}) {
  const load = async (columnFilter) => {
    const params = new URLSearchParams({ target: String(target || '').trim() });
    if (n != null) params.set('n', String(n));
    if (columnFilter) params.set('columns', String(columnFilter));
    if (versionId) params.set('version', String(versionId));
    const json = await request.getJson(
      `${apiDecisionSessions(strategyName)}/${encodeURIComponent(sessionId)}/info?${params.toString()}`,
      LONG,
    );
    const m = unwrapMessage(json);
    const candles = Array.isArray(m.candles) && m.candles.length
      ? m.candles.map((row) => ({
        date: String(row?.date || '').replace(/-/g, ''),
        open: Number(row.open),
        close: Number(row.close),
        high: Number(row.high),
        low: Number(row.low),
      })).filter((row) => row.date && [row.open, row.close, row.high, row.low].every(Number.isFinite))
      : infoRowsToCandles(m.rows);
    return {
      entityId: String(m.entity_id || ''),
      name: String(m.name || ''),
      asOf: formatDecisionDate(m.as_of),
      stats: mapStats(m.stats),
      tickerStats: mapStats(m.ticker_stats),
      columns: Array.isArray(m.columns) ? m.columns : [],
      rows: Array.isArray(m.rows) ? m.rows : [],
      candles,
      indicatorSeries: mapIndicatorSeries(m.indicator_series),
    };
  };
  try {
    return await load(columns);
  } catch (err) {
    if (columns) throw err;
    return load('open,high,low,close,volume');
  }
}
