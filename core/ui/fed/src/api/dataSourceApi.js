import request, { API_VERSION_PREFIX } from 'service/request';
import { mapDataEnd } from 'service/dataEnd';
import { getUpdateModeIcon } from 'service/updateModeIcon';

const API_DATA_SOURCES_LIST = `${API_VERSION_PREFIX}/data-sources/list`;
const API_DATA_SOURCES_FRESHNESS = `${API_VERSION_PREFIX}/data-sources/freshness`;
const API_DATA_SOURCES_RENEW = `${API_VERSION_PREFIX}/data-sources/renew`;

/** 列表展示名：优先 ``display_name``，否则 ``name``。 */
export function getDataSourceDisplayLabel(item) {
  return String(item?.display_name || item?.name || '').trim();
}

/** ``origin`` 展示文案。 */
export function getDataSourceOriginLabel(origin) {
  return String(origin || '').trim().toLowerCase() === 'userspace' ? '自定义' : '系统';
}

/** 更新方式展示文案。 */
export function getDataSourceRenewTypeLabel(item) {
  return String(item?.renew_type_label || item?.renew_type || '—').trim() || '—';
}

/** 数据状态展示文案。 */
export function getDataSourceUpdateStatusLabel(item) {
  if (item?.freshness_pending) return '计算中…';
  return String(item?.update_status_label || '—').trim() || '—';
}

/** 认证状态展示文案。 */
export function getDataSourceAuthLabel(item) {
  if (!item?.requires_auth) return '无需 Token';
  return item?.auth_ready ? '已配置' : '未配置 Token';
}

/** 更新方式对应 ``NtqIcon`` name。 */
export function getDataSourceRenewTypeIcon(mode) {
  return getUpdateModeIcon(mode);
}

/**
 * DS-01：Data source 目录
 * @returns {Promise<{ data: object[], total: number, dataEnd: object }>}
 */
export async function fetchDataSourceList({ page = 1, limit = 200 } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(limit),
  });
  const json = await request.getJson(`${API_DATA_SOURCES_LIST}?${params.toString()}`);
  const m = json?.message || {};
  const items = Array.isArray(m.items) ? m.items : [];
  const dataEnd = m.data_end && typeof m.data_end === 'object' ? m.data_end : {};
  return {
    data: items.map((item) => {
      const name = String(item.name || '').trim();
      const origin = String(item.origin || 'system').trim().toLowerCase() === 'userspace'
        ? 'userspace'
        : 'system';
      return {
        id: name,
        name,
        display_name: getDataSourceDisplayLabel(item),
        target_table: String(item.target_table || '').trim(),
        is_enabled: Boolean(item.is_enabled),
        depends_on: Array.isArray(item.depends_on) ? item.depends_on : [],
        providers: Array.isArray(item.providers) ? item.providers : [],
        providers_label: String(item.providers_label || '').trim(),
        renew_type: String(item.renew_type || '').trim(),
        renew_type_label: getDataSourceRenewTypeLabel(item),
        renew_interval_days: item.renew_interval_days ?? null,
        rate_limit_per_minute: item.rate_limit_per_minute ?? null,
        requires_auth: Boolean(item.requires_auth),
        auth_ready: Boolean(item.auth_ready),
        missing_auth_providers: Array.isArray(item.missing_auth_providers)
          ? item.missing_auth_providers
          : [],
        auth_hint: String(item.auth_hint || '').trim(),
        can_renew: Boolean(item.can_renew),
        freshness_pending: true,
        update_status: '',
        update_status_label: '',
        update_status_hint: '',
        origin,
        is_custom: Boolean(item.is_custom),
      };
    }),
    total: Number(m.total) || items.length,
    dataEnd: mapDataEnd(dataEnd),
  };
}

function mapFreshnessItem(name, item) {
  return {
    update_status: String(item?.update_status || '').trim(),
    update_status_label: String(item?.update_status_label || '').trim(),
    update_status_hint: String(item?.update_status_hint || '').trim(),
    freshness_pending: false,
  };
}

/**
 * DS-01：Lazy freshness — DB last update + renew_if_over_days vs data.json.
 * @param {{ names?: string[] }} [options]
 * @returns {Promise<{ items: Record<string, object>, dataEnd: object }>}
 */
export async function fetchDataSourceFreshness({ names } = {}) {
  const params = new URLSearchParams();
  if (Array.isArray(names) && names.length > 0) {
    params.set('names', names.map((n) => String(n || '').trim()).filter(Boolean).join(','));
  }
  const query = params.toString();
  const url = query ? `${API_DATA_SOURCES_FRESHNESS}?${query}` : API_DATA_SOURCES_FRESHNESS;
  const json = await request.getJson(url);
  const m = json?.message || {};
  const rawItems = m.items && typeof m.items === 'object' ? m.items : {};
  const dataEnd = m.data_end && typeof m.data_end === 'object' ? m.data_end : {};
  const items = {};
  Object.entries(rawItems).forEach(([name, item]) => {
    const key = String(name || '').trim();
    if (!key) return;
    items[key] = mapFreshnessItem(key, item);
  });
  return {
    items,
    dataEnd: mapDataEnd(dataEnd),
  };
}

/**
 * 更新全部数据源，或只更新 source 这一项。
 * @param {string} [source]
 * @returns {Promise<{ is_triggered: boolean, job_id: string, source: string, running: boolean }>}
 */
export async function startDataSourceRenew(source = '') {
  const body = {};
  const key = String(source || '').trim();
  if (key) body.source = key;
  const json = await request.postJson(API_DATA_SOURCES_RENEW, { body });
  const m = json?.message || {};
  return {
    is_triggered: Boolean(m.is_triggered),
    job_id: String(m.job_id || '').trim(),
    source: String(m.source || '').trim(),
    running: Boolean(m.running),
  };
}

function mapRenewTask(task) {
  const numberOrNull = (value) => {
    if (value == null || value === '') return null;
    const number = Number(value);
    return Number.isFinite(number) ? number : null;
  };
  return {
    source: String(task?.source || '').trim(),
    status: String(task?.status || '').trim(),
    startedAt: Number(task?.started_at) || 0,
    totalSeconds: numberOrNull(task?.total_seconds),
    progressDone: numberOrNull(task?.progress_done),
    progressTotal: numberOrNull(task?.progress_total),
    progressLabel: String(task?.progress_label || '').trim(),
    error: String(task?.error || '').trim(),
  };
}

/**
 * @returns {Promise<{ running: boolean, job_id: string, source: string, error: string, message: string, tasks: object[] }>}
 */
export async function fetchDataSourceRenewStatus() {
  const json = await request.getJson(API_DATA_SOURCES_RENEW, { silent: true });
  const m = json?.message || {};
  const rawTasks = Array.isArray(m.tasks) ? m.tasks : [];
  return {
    running: Boolean(m.running),
    job_id: String(m.job_id || '').trim(),
    source: String(m.source || '').trim(),
    error: String(m.error || '').trim(),
    message: String(m.message || '').trim(),
    tasks: rawTasks.map(mapRenewTask).filter((task) => task.source),
  };
}
