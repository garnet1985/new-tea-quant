import { requestJson } from '../global/httpClient';
import { API_VERSION_PREFIX } from '../conf/apiConfig';

const API_DATA_SOURCES_LIST = `${API_VERSION_PREFIX}/data-sources/list`;
const API_DATA_SOURCES_FRESHNESS = `${API_VERSION_PREFIX}/data-sources/freshness`;

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
  const key = String(mode || '').trim().toLowerCase();
  if (key === 'refresh') return 'refresh';
  if (key === 'incremental') return 'add';
  if (key === 'rolling') return 'webhook';
  return 'info';
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
  const json = await requestJson(`${API_DATA_SOURCES_LIST}?${params.toString()}`, { method: 'GET' });
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
    dataEnd: {
      configured_as_of: dataEnd.configured_as_of ?? null,
      effective_end_date: dataEnd.effective_end_date ?? null,
      is_end_date_truncated: Boolean(dataEnd.is_end_date_truncated),
      truncation_hint: String(dataEnd.truncation_hint || '').trim(),
      truncation_settings_path: String(dataEnd.truncation_settings_path || '').trim() || null,
    },
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

function mapDataEnd(dataEnd) {
  return {
    configured_as_of: dataEnd.configured_as_of ?? null,
    effective_end_date: dataEnd.effective_end_date ?? null,
    is_end_date_truncated: Boolean(dataEnd.is_end_date_truncated),
    truncation_hint: String(dataEnd.truncation_hint || '').trim(),
    truncation_settings_path: String(dataEnd.truncation_settings_path || '').trim() || null,
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
  const json = await requestJson(url, { method: 'GET' });
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
