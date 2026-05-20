import { requestJson } from '../global/httpClient';

/**
 * BFF 健康检查；版本号来自 ``core/system.json``（``GET /api/health``）。
 * @returns {Promise<{ version: string, healthy: boolean }>}
 */
export async function fetchAppHealth() {
  const json = await requestJson('/api/health', { method: 'GET' });
  const msg = json?.message || {};
  const raw = typeof msg.version === 'string' ? msg.version.trim() : '';
  return {
    healthy: msg.healthy !== false,
    version: raw,
  };
}
