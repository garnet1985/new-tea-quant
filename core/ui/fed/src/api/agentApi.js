import request, { API_VERSION_PREFIX, HTTP_TIMEOUT_MS } from 'service/request';

const API_AGENT_RUN = `${API_VERSION_PREFIX}/agent/run`;
const API_AGENT_SESSION_CLEAR = `${API_VERSION_PREFIX}/agent/session/clear`;

/**
 * @param {{ content: string, sessionId?: string }} body
 * @returns {Promise<{ reply: string, sessionId: string }>}
 */
export async function runAgent(body) {
  const json = await request.postJson(API_AGENT_RUN, {
    timeoutMs: HTTP_TIMEOUT_MS.AGENT,
    body: {
      content: String(body?.content || ''),
      sessionId: String(body?.sessionId || '').trim() || undefined,
    },
  });
  const m = json?.message || {};
  return {
    reply: String(m.reply || ''),
    sessionId: String(m.sessionId || 'default'),
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
