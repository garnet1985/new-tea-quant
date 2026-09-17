import request, { API_VERSION_PREFIX, HTTP_TIMEOUT_MS } from 'services/request';

const API_ASSISTANT_PROVIDERS = `${API_VERSION_PREFIX}/assistant/providers`;
const API_ASSISTANT_CHAT = `${API_VERSION_PREFIX}/assistant/chat`;

/**
 * @returns {Promise<Array<{
 *   providerId: string,
 *   baseUrl: string,
 *   model: string,
 *   enabled: boolean,
 *   hasApiKey: boolean,
 * }>>}
 */
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
    timeoutMs: HTTP_TIMEOUT_MS.LONG,
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
