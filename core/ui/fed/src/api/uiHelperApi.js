import request, { API_VERSION_PREFIX } from 'services/request';

const API_UI_HELPER = `${API_VERSION_PREFIX}/settings/ui-helper`;

function normalizeEntry(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const version = Number(raw.version);
  const source = String(raw.source || '').trim().toLowerCase();
  if (!Number.isInteger(version) || version < 1) return null;
  if (source !== 'ack' && source !== 'skip') return null;
  return {
    version,
    at: String(raw.at || '').trim(),
    source,
  };
}

function normalizeDismissed(raw) {
  if (!raw || typeof raw !== 'object') return {};
  const out = {};
  Object.keys(raw).forEach((key) => {
    const helpId = String(key || '').trim();
    const entry = normalizeEntry(raw[key]);
    if (helpId && entry) out[helpId] = entry;
  });
  return out;
}

/**
 * @returns {Promise<{ dismissed: Record<string, { version: number, at: string, source: string }> }>}
 */
export async function fetchUiHelper() {
  const json = await request.getJson(API_UI_HELPER);
  return { dismissed: normalizeDismissed(json?.message?.dismissed) };
}

/**
 * @param {{ helpId: string, version: number, source: 'ack'|'skip' }} body
 */
export async function dismissUiHelper(body) {
  const json = await request.postJson(API_UI_HELPER, {
    body: {
      helpId: String(body?.helpId || '').trim(),
      version: Number(body?.version) || 1,
      source: String(body?.source || 'ack').trim(),
    },
  });
  return { dismissed: normalizeDismissed(json?.message?.dismissed) };
}
