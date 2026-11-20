import request, { API_VERSION_PREFIX, HTTP_TIMEOUT_MS } from 'service/request';

const API_SETTINGS_DB = `${API_VERSION_PREFIX}/settings/database`;
const API_SETTINGS_DATA = `${API_VERSION_PREFIX}/settings/data`;
const API_SETTINGS_CACHE_CLEAR = `${API_VERSION_PREFIX}/settings/cache/clear`;
const API_SETTINGS_TRACE = `${API_VERSION_PREFIX}/settings/trace`;
const API_SETTINGS_MEMBERSHIP = `${API_VERSION_PREFIX}/settings/membership`;

const SUPPORTED_DB_TYPES = new Set(['postgresql', 'mysql', 'duckdb']);

function normalizeYyyymmdd(value) {
  const raw = String(value || '').trim().replace(/-/g, '');
  return raw.length === 8 && /^\d{8}$/.test(raw) ? raw : String(value || '').trim();
}

function normalizeOptionalYyyymmdd(value) {
  const raw = String(value || '').trim();
  if (!raw) return null;
  return normalizeYyyymmdd(raw) || null;
}

function normalizeDatabaseType(value) {
  const dt = String(value || 'duckdb').trim().toLowerCase();
  return SUPPORTED_DB_TYPES.has(dt) ? dt : 'duckdb';
}

/**
 * @returns {Promise<{ database_type: string, database: string, duckdb_domains: Record<string, string> }>}
 */
export async function fetchDatabaseSettings() {
  const json = await request.getJson(API_SETTINGS_DB);
  const m = json?.message || {};
  return {
    database_type: normalizeDatabaseType(m.database_type),
    database: String(m.database || '').trim(),
    duckdb_domains: m.duckdb_domains && typeof m.duckdb_domains === 'object' ? m.duckdb_domains : {},
  };
}

/**
 * @param {{ database_type: string, database?: string }} body
 * @returns {Promise<{ database_type: string, database: string, duckdb_domains: Record<string, string> }>}
 */
export async function saveDatabaseSettings(body) {
  const json = await request.postJson(API_SETTINGS_DB, {
    body: {
      database_type: normalizeDatabaseType(body.database_type),
      database: body.database_type === 'duckdb' ? '' : String(body.database || '').trim(),
    },
  });
  const m = json?.message || {};
  return {
    database_type: normalizeDatabaseType(m.database_type),
    database: String(m.database || '').trim(),
    duckdb_domains: m.duckdb_domains && typeof m.duckdb_domains === 'object' ? m.duckdb_domains : {},
  };
}

function _assumedFromMessage(m) {
  const raw = m.assumed_latest_completed_trading_date;
  return raw ? normalizeYyyymmdd(raw) : null;
}

/**
 * @returns {Promise<{ default_start_date: string, assumed_latest_completed_trading_date: string|null, simulation_results_max_stale_envs: number|null, config_path: string }>}
 */
export async function fetchDataSettings() {
  const json = await request.getJson(API_SETTINGS_DATA);
  const m = json?.message || {};
  const retentionMax = m.simulation_results_max_stale_envs;
  return {
    default_start_date: normalizeYyyymmdd(m.default_start_date),
    assumed_latest_completed_trading_date: _assumedFromMessage(m),
    simulation_results_max_stale_envs:
      retentionMax != null && retentionMax !== '' ? Number(retentionMax) : null,
    config_path: String(m.config_path || '').trim(),
  };
}

/**
 * @param {{ default_start_date: string, assumed_latest_completed_trading_date?: string, simulation_results_max_stale_envs?: string|number }} body
 */
export async function saveDataSettings(body) {
  const json = await request.postJson(API_SETTINGS_DATA, {
    body: {
      default_start_date: normalizeYyyymmdd(body.default_start_date),
      assumed_latest_completed_trading_date: normalizeOptionalYyyymmdd(
        body.assumed_latest_completed_trading_date,
      ),
      simulation_results_max_stale_envs:
        String(body.simulation_results_max_stale_envs ?? '').trim() || null,
    },
  });
  const m = json?.message || {};
  const retentionMax = m.simulation_results_max_stale_envs;
  return {
    default_start_date: normalizeYyyymmdd(m.default_start_date),
    assumed_latest_completed_trading_date: _assumedFromMessage(m),
    simulation_results_max_stale_envs:
      retentionMax != null && retentionMax !== '' ? Number(retentionMax) : null,
    config_path: String(m.config_path || '').trim(),
  };
}

/**
 * @returns {Promise<{ decided: boolean, enabled: boolean, needs_ask: boolean, decided_at: string, source: string }>}
 */
export async function fetchTraceSettings() {
  const json = await request.getJson(API_SETTINGS_TRACE);
  const m = json?.message || {};
  return {
    decided: Boolean(m.decided),
    enabled: Boolean(m.enabled),
    needs_ask: Boolean(m.needs_ask),
    decided_at: String(m.decided_at || '').trim(),
    source: String(m.source || '').trim(),
  };
}

/**
 * @param {{ enabled: boolean, source?: string }} body
 * @returns {Promise<{ decided: boolean, enabled: boolean, needs_ask: boolean, decided_at: string, source: string }>}
 */
export async function saveTraceSettings(body) {
  const source = String(body?.source || 'settings_ui').trim().slice(0, 32) || 'settings_ui';
  const json = await request.postJson(API_SETTINGS_TRACE, {
    body: {
      enabled: Boolean(body?.enabled),
      source,
    },
  });
  const m = json?.message || {};
  return {
    decided: Boolean(m.decided),
    enabled: Boolean(m.enabled),
    needs_ask: Boolean(m.needs_ask),
    decided_at: String(m.decided_at || '').trim(),
    source: String(m.source || '').trim(),
  };
}

/** 会员凭证变更后，顶栏等监听此事件刷新。 */
export const MEMBERSHIP_CHANGED_EVENT = 'ntq-membership-changed';

/**
 * @param {{ catfood?: number|null, profile?: object }} [detail]
 */
export function notifyMembershipChanged(detail = {}) {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(MEMBERSHIP_CHANGED_EVENT, { detail: detail || {} }));
}

/**
 * @returns {Promise<{ configured: boolean, invalid: boolean, path: string }>}
 */
export async function fetchMembershipSettings() {
  const json = await request.getJson(API_SETTINGS_MEMBERSHIP);
  const m = json?.message || {};
  return {
    configured: Boolean(m.configured),
    invalid: Boolean(m.invalid),
    path: String(m.path || 'userspace/system/membership/membership_token.txt'),
  };
}

/**
 * @param {string} token
 * @returns {Promise<{ configured: boolean, invalid: boolean, path: string }>}
 */
export async function saveMembershipToken(token) {
  const json = await request.putJson(API_SETTINGS_MEMBERSHIP, {
    body: { token: String(token || '') },
  });
  const m = json?.message || {};
  notifyMembershipChanged();
  return {
    configured: Boolean(m.configured),
    invalid: Boolean(m.invalid),
    path: String(m.path || ''),
  };
}

/**
 * @returns {Promise<{ configured: boolean, invalid: boolean, path: string }>}
 */
/**
 * 顶栏会员条。没有凭证或官网拒绝时 signed_in 为 false。
 * @returns {Promise<{
 *   signed_in: boolean,
 *   register_url: string,
 *   name: string,
 *   avatar: string,
 *   points: number|null,
 *   tier: string|null,
 *   is_pro: boolean,
 *   catfood: number|null,
 *   catfood_free: number|null,
 *   catfood_paid: number|null,
 *   catfood_free_expires_at: string|null,
 *   reason: string
 * }>}
 */
export async function fetchMemberProfile() {
  const json = await request.getJson(`${API_VERSION_PREFIX}/membership/profile`, { silent: true });
  const m = json?.message || {};
  const points = m.points;
  const catfood = m.catfood;
  const catfoodFree = m.catfood_free;
  const catfoodPaid = m.catfood_paid;
  const tier = String(m.tier || '').trim().toLowerCase();
  const expiresAt = String(m.catfood_free_expires_at || '').trim();
  return {
    signed_in: Boolean(m.signed_in),
    register_url: String(m.register_url || '').trim(),
    name: String(m.name || '').trim(),
    avatar: String(m.avatar || '').trim(),
    points: points == null || points === '' ? null : Number(points),
    tier: tier === 'pro' || tier === 'standard' ? tier : null,
    is_pro: Boolean(m.is_pro),
    catfood: catfood == null || catfood === '' ? null : Number(catfood),
    catfood_free: catfoodFree == null || catfoodFree === '' ? null : Number(catfoodFree),
    catfood_paid: catfoodPaid == null || catfoodPaid === '' ? null : Number(catfoodPaid),
    catfood_free_expires_at: expiresAt || null,
    reason: String(m.reason || '').trim(),
  };
}

/**
 * 会员邮件代发额度（经本机 BFF 转发官网）。
 * @returns {Promise<{
 *   available: boolean,
 *   reason: string,
 *   limit: number|null,
 *   used: number|null,
 *   remaining: number|null,
 *   unlimited: boolean,
 *   policy: string,
 * }>}
 */
export async function fetchMemberMailQuota() {
  const json = await request.getJson(
    `${API_VERSION_PREFIX}/membership/mail-quota`,
    { silent: true },
  );
  const m = json?.message || {};
  const limit = m.limit;
  const used = m.used;
  const remaining = m.remaining;
  return {
    available: Boolean(m.available),
    reason: String(m.reason || '').trim(),
    limit: limit == null || limit === '' ? null : Number(limit),
    used: used == null || used === '' ? null : Number(used),
    remaining: remaining == null || remaining === '' ? null : Number(remaining),
    unlimited: Boolean(m.unlimited),
    policy: String(m.policy || '').trim(),
  };
}

/**
 * 会员邮件额度的「还可发」短句；读不到时返回空串。
 * @param {{ available?: boolean, unlimited?: boolean, remaining?: number|null, used?: number|null, limit?: number|null }|null|undefined} quota
 */
export function formatMailQuotaRemaining(quota) {
  if (!quota || !quota.available) return '';
  if (quota.unlimited) return '不限发送次数';
  const remaining = Number(quota.remaining);
  if (!Number.isFinite(remaining)) return '';
  if (remaining <= 0) {
    const used = Number(quota.used);
    const limit = Number(quota.limit);
    if (Number.isFinite(used) && Number.isFinite(limit)) {
      return `额度已用完（已用 ${used} / 共 ${limit} 封）`;
    }
    return '额度已用完';
  }
  const used = Number(quota.used);
  const limit = Number(quota.limit);
  if (Number.isFinite(used) && Number.isFinite(limit)) {
    return `还可发 ${remaining} 封（已用 ${used} / 共 ${limit}）`;
  }
  return `还可发 ${remaining} 封`;
}

/**
 * 最近猫粮流水（经本机 BFF 转发官网）。
 * @returns {Promise<{ available: boolean, catfood: number|null, currency: string, items: Array<object> }>}
 */
export async function fetchCatfoodLedger(limit = 20) {
  const json = await request.getJson(
    `${API_VERSION_PREFIX}/membership/catfood-ledger?limit=${encodeURIComponent(String(limit))}`,
    { silent: true },
  );
  const m = json?.message || {};
  const items = Array.isArray(m.items) ? m.items : [];
  const catfood = m.catfood;
  return {
    available: Boolean(m.available),
    catfood: catfood == null || catfood === '' ? null : Number(catfood),
    currency: String(m.currency || '猫粮'),
    items: items.map((row) => ({
      id: Number(row?.id) || 0,
      created: Number(row?.created) || 0,
      reason: String(row?.reason || ''),
      reasonLabel: String(row?.reason_label || row?.reason || ''),
      mode: String(row?.mode || ''),
      catfoodDelta: Number(row?.catfood_delta),
      catfoodBalanceAfter: Number(row?.catfood_balance_after),
    })),
  };
}

/**
 * @returns {Promise<{ configured: boolean, invalid: boolean, path: string }>}
 */
export async function clearMembershipToken() {
  const json = await request.deleteJson(API_SETTINGS_MEMBERSHIP);
  const m = json?.message || {};
  notifyMembershipChanged();
  return {
    configured: Boolean(m.configured),
    invalid: Boolean(m.invalid),
    path: String(m.path || ''),
  };
}

/**
 * 清理 userspace 缓存（Settings → 缓存管理）。
 */
export async function clearSettingsCache(body) {
  const json = await request.postJson(API_SETTINGS_CACHE_CLEAR, {
    timeoutMs: HTTP_TIMEOUT_MS.LONG,
    body: {
      clear_backtest_results: Boolean(body?.clear_backtest_results),
      clear_scan_results: Boolean(body?.clear_scan_results),
      clear_userspace_ntq: Boolean(body?.clear_userspace_ntq),
    },
  });
  const m = json?.message || {};
  return {
    cleared: Boolean(m.cleared),
    message: String(m.message || '缓存已经全部清理').trim() || '缓存已经全部清理',
  };
}
