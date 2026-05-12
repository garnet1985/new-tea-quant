import { requestJson } from '../global/httpClient';
import { API_VERSION_PREFIX } from '../conf/apiConfig';

const API_SETTINGS_DB = `${API_VERSION_PREFIX}/settings/database`;

/**
 * @returns {Promise<{ database_type: string, database: string }>}
 */
export async function fetchDatabaseSettings() {
  const json = await requestJson(API_SETTINGS_DB, { method: 'GET' });
  const m = json?.message || {};
  return {
    database_type: m.database_type === 'mysql' ? 'mysql' : 'postgresql',
    database: String(m.database || '').trim(),
  };
}

/**
 * @param {{ database_type: 'postgresql'|'mysql', database: string }} body
 * @returns {Promise<{ database_type: string, database: string }>}
 */
export async function saveDatabaseSettings(body) {
  const json = await requestJson(API_SETTINGS_DB, {
    method: 'POST',
    body: JSON.stringify({
      database_type: body.database_type,
      database: body.database,
    }),
  });
  const m = json?.message || {};
  return {
    database_type: m.database_type === 'mysql' ? 'mysql' : 'postgresql',
    database: String(m.database || '').trim(),
  };
}
