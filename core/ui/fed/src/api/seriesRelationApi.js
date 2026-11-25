import request, { API_VERSION_PREFIX } from 'service/request';

const API_LIST = `${API_VERSION_PREFIX}/series-relations/list`;

/** 编码场景 key 为 URL 路径段（支持 ``a/b``）。 */
export function encodeSeriesRelationKeyPath(key) {
  return String(key || '')
    .split('/')
    .filter(Boolean)
    .map((seg) => encodeURIComponent(seg))
    .join('/');
}

/** 详情页路由：``/advanced/series-relation/<key>`` */
export function getSeriesRelationPath(key) {
  const path = encodeSeriesRelationKeyPath(key);
  return path ? `/advanced/series-relation/${path}` : '/advanced/series-relation';
}

/** 从 splat / pathname 解析 key。 */
export function parseSeriesRelationKeyFromPath(splatOrPath) {
  const raw = String(splatOrPath || '').trim();
  const stripped = raw.replace(/^\/?advanced\/series-relation\/?/, '');
  return stripped
    .split('/')
    .filter(Boolean)
    .map((seg) => {
      try {
        return decodeURIComponent(seg);
      } catch {
        return seg;
      }
    })
    .join('/');
}

function encodeKeyPath(key) {
  return encodeSeriesRelationKeyPath(key);
}

function apiScenePath(key) {
  return `${API_VERSION_PREFIX}/series-relations/${encodeKeyPath(key)}`;
}

export async function fetchSeriesRelationList({ page = 1, limit = 100 } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(limit),
  });
  const json = await request.getJson(`${API_LIST}?${params.toString()}`);
  const m = json?.message || {};
  const items = Array.isArray(m.items) ? m.items : [];
  return {
    data: items.map((item) => ({
      key: String(item.key || '').trim(),
      display_name: String(item.display_name || item.key || '').trim(),
      relative_path: String(item.relative_path || item.key || '').trim(),
      has_results: Boolean(item.has_results),
    })),
    total: Number(m.total) || items.length,
  };
}

export async function fetchSeriesRelationScene(key) {
  const json = await request.getJson(apiScenePath(key));
  const m = json?.message || {};
  return {
    key: String(m.key || key).trim(),
    display_name: String(m.display_name || '').trim(),
    settings: m.settings && typeof m.settings === 'object' ? m.settings : {},
    has_results: Boolean(m.has_results),
    max_series: Number(m.max_series) || 6,
  };
}

export async function saveSeriesRelationScene(key, settings) {
  const json = await request.putJson(apiScenePath(key), {
    body: { settings },
  });
  return json?.message || {};
}

export async function runSeriesRelationScene(key) {
  const json = await request.postJson(`${apiScenePath(key)}/run`, { body: {} });
  return json?.message || {};
}

export async function fetchSeriesRelationResults(key, { maxPoints = 800 } = {}) {
  const params = new URLSearchParams({ max_points: String(maxPoints) });
  const json = await request.getJson(
    `${apiScenePath(key)}/results?${params.toString()}`,
  );
  return json?.message || {};
}
