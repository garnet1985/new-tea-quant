import { requestJson } from '../global/httpClient';
import { API_VERSION_PREFIX } from '../conf/apiConfig';

const API_SETTINGS_DB = `${API_VERSION_PREFIX}/settings/database`;

const SUPPORTED_DB_TYPES = new Set(['postgresql', 'mysql', 'duckdb']);

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
