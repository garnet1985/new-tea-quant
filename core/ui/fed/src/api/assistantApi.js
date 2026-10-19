import request, { API_VERSION_PREFIX, HTTP_TIMEOUT_MS } from 'service/request';

const API_ASSISTANT_PROVIDERS = `${API_VERSION_PREFIX}/assistant/providers`;
const API_ASSISTANT_CHAT = `${API_VERSION_PREFIX}/assistant/chat`;
const API_ASSISTANT_NTQ_QUOTA = `${API_VERSION_PREFIX}/assistant/ntq-quota`;

/**
 * @returns {Promise<Array<{
 *   providerId: string,
 *   baseUrl: string,
 *   model: string,
 *   enabled: boolean,
 *   hasApiKey: boolean,
 * }>>}
 */
/**
 * @returns {Promise<{
 *   available: boolean,
 *   balance: number|null,
 *   tokenBalance: number|null,
 *   currency: string,
 *   usage: object|null,
 *   models: object|null,
 *   limit: number|null,
 *   remaining: number|null,
 * }>}
 */
export async function fetchNtqQuota() {
  const json = await request.getJson(API_ASSISTANT_NTQ_QUOTA);
  const m = json?.message || {};
  const balance = m.balance == null ? null : Number(m.balance);
  const tokenBalance = m.token_balance == null ? null : Number(m.token_balance);
  const remaining = m.remaining == null ? balance : Number(m.remaining);
  const limit = m.limit == null ? null : Number(m.limit);
  return {
    available: Boolean(m.available) && Number.isFinite(remaining),
    balance: Number.isFinite(balance) ? Number(balance.toFixed(2)) : null,
    tokenBalance: Number.isFinite(tokenBalance) ? tokenBalance : null,
    currency: String(m.currency || '猫粮'),
    usage: m.usage && typeof m.usage === 'object' ? m.usage : null,
    models: m.models && typeof m.models === 'object' ? m.models : null,
    limit: Number.isFinite(limit) ? limit : null,
    remaining: Number.isFinite(remaining) ? Number(Number(remaining).toFixed(2)) : null,
  };
}

export async function listAssistantProviders() {
  const json = await request.getJson(API_ASSISTANT_PROVIDERS);
  const items = json?.message?.items;
  return Array.isArray(items) ? items : [];
}

/**
 * @param {{ content: string, providerId?: string, history?: Array<{ role: string, content: string }> }} body
 * @returns {Promise<{ reply: string, providerId: string, model: string }>}
 */
export async function chatWithAssistant(body) {
  const history = Array.isArray(body?.history)
    ? body.history
      .filter((item) => item && (item.role === 'user' || item.role === 'assistant') && item.content)
      .map((item) => ({ role: item.role, content: String(item.content) }))
    : [];
  const json = await request.postJson(API_ASSISTANT_CHAT, {
    timeoutMs: HTTP_TIMEOUT_MS.ASSISTANT,
    body: {
      content: String(body?.content || ''),
      providerId: String(body?.providerId || '').trim() || undefined,
      history: history.length ? history : undefined,
    },
  });
  const m = json?.message || {};
  return {
    reply: String(m.reply || ''),
    providerId: String(m.providerId || ''),
    model: String(m.model || ''),
  };
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
export async function saveAssistantProviderApiKey(providerId, apiKey) {
  const id = encodeURIComponent(String(providerId || '').trim());
  const json = await request.putJson(`${API_ASSISTANT_PROVIDERS}/${id}/api-key`, {
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
