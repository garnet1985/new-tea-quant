import request, { API_VERSION_PREFIX, HTTP_TIMEOUT_MS } from 'service/request';

const API_AGENT_RUN = `${API_VERSION_PREFIX}/agent/run`;
const API_AGENT_QUOTA = `${API_VERSION_PREFIX}/agent/quota`;
const API_AGENT_SESSION_CLEAR = `${API_VERSION_PREFIX}/agent/session/clear`;
const API_AGENT_SESSION_HISTORY = `${API_VERSION_PREFIX}/agent/session/history`;

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
export async function fetchAgentQuota() {
  const json = await request.getJson(API_AGENT_QUOTA);
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

/**
 * @param {{ content: string, sessionId?: string, providerId?: string }} body
 * @returns {Promise<{
 *   reply: string,
 *   sessionId: string,
 *   mode: 'ask'|'work'|string,
 *   catfoodSpent: number|null,
 *   balance: number|null,
 * }>}
 */
export async function runAgent(body) {
  const json = await request.postJson(API_AGENT_RUN, {
    timeoutMs: HTTP_TIMEOUT_MS.AGENT,
    body: {
      content: String(body?.content || ''),
      sessionId: String(body?.sessionId || '').trim() || undefined,
      providerId: String(body?.providerId || '').trim() || undefined,
    },
  });
  const m = json?.message || {};
  const spent = m.catfoodSpent == null ? m.catfood_spent : m.catfoodSpent;
  const balance = m.balance;
  const mode = String(m.mode || '').trim().toLowerCase();
  return {
    reply: String(m.reply || ''),
    sessionId: String(m.sessionId || 'default'),
    mode: mode === 'work' || mode === 'ask' ? mode : (m.handoff ? 'work' : 'ask'),
    catfoodSpent: spent == null || spent === '' || Number.isNaN(Number(spent))
      ? null
      : Number(Number(spent).toFixed(2)),
    balance: balance == null || balance === '' || Number.isNaN(Number(balance))
      ? null
      : Number(Number(balance).toFixed(2)),
  };
}

/**
 * @param {{ sessionId?: string }} [body]
 * @returns {Promise<{ cleared: boolean, sessionId: string }>}
 */
export async function clearAgentSession(body = {}) {
  const json = await request.postJson(API_AGENT_SESSION_CLEAR, {
    body: {
      sessionId: String(body?.sessionId || '').trim() || undefined,
    },
  });
  const m = json?.message || {};
  return {
    cleared: Boolean(m.cleared),
    sessionId: String(m.sessionId || 'default'),
  };
}

/**
 * @param {{ sessionId?: string, limit?: number }} [body]
 * @returns {Promise<{ sessionId: string, messages: Array<{ role: string, content: string }> }>}
 */
export async function fetchAgentSessionHistory(body = {}) {
  const params = new URLSearchParams();
  const sessionId = String(body?.sessionId || '').trim();
  if (sessionId) params.set('sessionId', sessionId);
  params.set('limit', String(body?.limit == null ? 20 : body.limit));
  const url = `${API_AGENT_SESSION_HISTORY}?${params.toString()}`;
  const json = await request.getJson(url);
  const m = json?.message || {};
  const rows = Array.isArray(m.messages) ? m.messages : [];
  return {
    sessionId: String(m.sessionId || 'default'),
    messages: rows
      .filter((item) => item && (item.role === 'user' || item.role === 'assistant') && item.content)
      .map((item) => ({
        role: item.role === 'user' ? 'user' : 'assistant',
        content: String(item.content),
      })),
  };
}
