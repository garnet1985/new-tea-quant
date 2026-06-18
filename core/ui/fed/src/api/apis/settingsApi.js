import { requestJson } from '../global/httpClient';
import { API_VERSION_PREFIX } from '../conf/apiConfig';

const API_SETTINGS_DB = `${API_VERSION_PREFIX}/settings/database`;
const API_SETTINGS_DATA = `${API_VERSION_PREFIX}/settings/data`;

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
  const json = await requestJson(API_SETTINGS_DB, { method: 'GET' });
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
  const json = await requestJson(API_SETTINGS_DB, {
    method: 'POST',
    body: JSON.stringify({
      database_type: normalizeDatabaseType(body.database_type),
      database: body.database_type === 'duckdb' ? '' : String(body.database || '').trim(),
    }),
  });
  const m = json?.message || {};
  return {
    database_type: normalizeDatabaseType(m.database_type),
    database: String(m.database || '').trim(),
    duckdb_domains: m.duckdb_domains && typeof m.duckdb_domains === 'object' ? m.duckdb_domains : {},
  };
}

/**
 * @returns {Promise<{ default_start_date: string, as_of_latest_completed_trading_date: string|null, use_sample_stock_list: number|null, config_path: string }>}
 */
export async function fetchDataSettings() {
  const json = await requestJson(API_SETTINGS_DATA, { method: 'GET' });
  const m = json?.message || {};
  const sample = m.use_sample_stock_list;
  return {
    default_start_date: normalizeYyyymmdd(m.default_start_date),
    as_of_latest_completed_trading_date: m.as_of_latest_completed_trading_date
      ? normalizeYyyymmdd(m.as_of_latest_completed_trading_date)
      : null,
    use_sample_stock_list: sample != null && sample !== '' ? Number(sample) : null,
    config_path: String(m.config_path || '').trim(),
  };
}

/**
 * @param {{ default_start_date: string, as_of_latest_completed_trading_date?: string, use_sample_stock_list?: string|number }} body
 */
export async function saveDataSettings(body) {
  const json = await requestJson(API_SETTINGS_DATA, {
    method: 'POST',
    body: JSON.stringify({
      default_start_date: normalizeYyyymmdd(body.default_start_date),
      as_of_latest_completed_trading_date: normalizeOptionalYyyymmdd(
        body.as_of_latest_completed_trading_date,
      ),
      use_sample_stock_list: String(body.use_sample_stock_list ?? '').trim() || null,
    }),
  });
  const m = json?.message || {};
  const sample = m.use_sample_stock_list;
  return {
    default_start_date: normalizeYyyymmdd(m.default_start_date),
    as_of_latest_completed_trading_date: m.as_of_latest_completed_trading_date
      ? normalizeYyyymmdd(m.as_of_latest_completed_trading_date)
      : null,
    use_sample_stock_list: sample != null && sample !== '' ? Number(sample) : null,
    config_path: String(m.config_path || '').trim(),
  };
}
