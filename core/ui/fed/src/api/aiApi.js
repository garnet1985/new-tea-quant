import request, { API_VERSION_PREFIX } from 'service/request';

const API_AI_PROVIDERS = `${API_VERSION_PREFIX}/ai/providers`;

/**
 * @returns {Promise<Array<{
 *   providerId: string,
 *   baseUrl: string,
 *   model: string,
 *   enabled: boolean,
 *   hasApiKey: boolean,
 * }>>}
 */
export async function listAiProviders() {
  const json = await request.getJson(API_AI_PROVIDERS);
  const items = json?.message?.items;
  return Array.isArray(items) ? items : [];
}

/**
 * @param {string} providerId
 * @param {string} apiKey
 * @returns {Promise<{
 *   providerId: string,
 *   baseUrl: string,
 *   model: string,
 *   enabled: boolean,
 *   hasApiKey: boolean,
 * }>}
 */
export async function saveAiProviderApiKey(providerId, apiKey) {
  const id = encodeURIComponent(String(providerId || '').trim());
  const json = await request.putJson(`${API_AI_PROVIDERS}/${id}/api-key`, {
    body: { apiKey: String(apiKey || '') },
  });
  const m = json?.message || {};
  return {
    providerId: String(m.providerId || ''),
    baseUrl: String(m.baseUrl || ''),
    model: String(m.model || ''),
    enabled: Boolean(m.enabled),
    hasApiKey: Boolean(m.hasApiKey),
  };
}
