import { requestJson } from '../global/httpClient';
import { API_VERSION_PREFIX } from '../conf/apiConfig';
import { mapDataEnd } from '../shared/dataEnd';

const API_TAGS_LIST = `${API_VERSION_PREFIX}/tags/list`;
const API_RUNTIME_PIPELINE = `${API_VERSION_PREFIX}/runtime/pipeline`;

/** 列表展示名：优先 ``display_name``，否则 ``name``（tag_key）。 */
export function getTagDisplayLabel(item) {
  return String(item?.display_name || item?.name || '').trim();
}

/** 将 tag_key（可含 ``/``）编码为 URL 路径段。 */
function encodeTagPathSegments(tagKey) {
  return String(tagKey || '')
    .split('/')
    .filter(Boolean)
    .map((seg) => encodeURIComponent(seg))
    .join('/');
}

function apiTagPath(tagKey) {
  const encoded = encodeTagPathSegments(tagKey);
  return `${API_VERSION_PREFIX}/tag/${encoded}`;
}

const UPDATE_MODE_LABELS = {
  incremental: '增量',
  refresh: '刷新',
};

/** ``update_mode`` 展示文案。 */
export function getTagUpdateModeLabel(mode) {
  const key = String(mode || '').trim().toLowerCase();
  if (!key) return '—';
  return UPDATE_MODE_LABELS[key] || key;
}

/** ``update_mode`` 对应 ``NtqIcon`` name。 */
export function getTagUpdateModeIcon(mode) {
  const key = String(mode || '').trim().toLowerCase();
  if (key === 'refresh') return 'refresh';
  if (key === 'incremental') return 'syncAlt';
  return 'info';
}

/** 格式化 ``last_computed_as_of``（YYYYMMDD → YYYY-MM-DD）。 */
export function formatTagAsOfDate(value) {
  const raw = String(value || '').trim();
  if (!raw) return '—';
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
  if (/^\d{8}$/.test(raw)) return `${raw.slice(0, 4)}-${raw.slice(4, 6)}-${raw.slice(6, 8)}`;
  return raw;
}

/** 计算状态展示文案。 */
export function getTagComputeStatusLabel(item) {
  return String(item?.compute_status_label || '—').trim() || '—';
}

/**
 * T1-00：全局 pipeline 状态
 * @returns {Promise<{ busy: boolean, kind?: string|null, label?: string|null, resource_key?: string|null }>}
 */
export async function fetchPipelineStatus() {
  const json = await requestJson(API_RUNTIME_PIPELINE, { method: 'GET' });
  const m = json?.message || {};
  return {
    busy: Boolean(m.busy),
    kind: m.kind ?? null,
    job_id: m.job_id ?? null,
    resource_key: m.resource_key ?? null,
    label: m.label ?? null,
    domains: Array.isArray(m.domains) ? m.domains : [],
  };
}

/**
 * T1-01：Tag scenario 列表
 * @returns {Promise<{ data: object[], total: number, dataEnd: object }>}
 */
export async function fetchTagList({ page = 1, limit = 100 } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(limit),
  });
  const json = await requestJson(`${API_TAGS_LIST}?${params.toString()}`, { method: 'GET' });
  const m = json?.message || {};
  const items = Array.isArray(m.items) ? m.items : [];
  const dataEnd = m.data_end && typeof m.data_end === 'object' ? m.data_end : {};
  return {
    data: items.map((item) => ({
      id: item.name,
      name: item.name,
      display_name: getTagDisplayLabel(item),
      description: String(item.description || '').trim(),
      is_enabled: Boolean(item.is_enabled),
      tag_definitions: Array.isArray(item.tag_definitions) ? item.tag_definitions : [],
      last_computed_as_of: item.last_computed_as_of ?? null,
      compute_status: String(item.compute_status || '').trim(),
      compute_status_label: getTagComputeStatusLabel(item),
      compute_status_hint: String(item.compute_status_hint || '').trim(),
      scenario_updated_at: item.scenario_updated_at ?? null,
      execution_mode: String(item.execution_mode || '').trim(),
      update_mode: String(item.update_mode || 'incremental').trim().toLowerCase(),
      recompute: Boolean(item.recompute),
    })),
    total: Number(m.total) || items.length,
    dataEnd: mapDataEnd(dataEnd),
  };
}

/**
 * T1-02：启动 Tag 计算
 */
export async function startTagRun(tagKey) {
  const json = await requestJson(`${apiTagPath(tagKey)}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  const m = json?.message || {};
  return {
    job_id: String(m.job_id || m.run_id || '').trim(),
    run_id: String(m.run_id || m.job_id || '').trim(),
    tag_key: m.tag_key || tagKey,
    name: m.name || tagKey,
  };
}

/**
 * T1-03：轮询 Tag run 进度
 */
export async function fetchTagRunProgress(tagKey, jobId) {
  const params = new URLSearchParams({ job_id: String(jobId || '') });
  const json = await requestJson(`${apiTagPath(tagKey)}/run/progress?${params.toString()}`, { method: 'GET' });
  return json?.message || {};
}
