import request, { HTTP_TIMEOUT_MS } from 'services/request';

/**
 * BFF 健康检查；版本号来自 ``core/system.json``（``GET /api/health``）。
 * @returns {Promise<{ version: string, healthy: boolean }>}
 */
export async function fetchAppHealth() {
  const json = await request.getJson('/api/health', {
    timeoutMs: HTTP_TIMEOUT_MS.POLL,
  });
  const msg = json?.message || {};
  const raw = typeof msg.version === 'string' ? msg.version.trim() : '';
  return {
    healthy: msg.healthy !== false,
    version: raw,
  };
}
