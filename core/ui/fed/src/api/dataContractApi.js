import request, { API_VERSION_PREFIX } from 'service/request';

const API_DATA_CONTRACTS_LIST = `${API_VERSION_PREFIX}/data-contracts/list`;
const API_DATA_CONTRACTS_RELOAD = `${API_VERSION_PREFIX}/data-contracts/reload`;

/** 列表展示名：优先 ``display_name``，否则 ``key``。 */
export function getDataContractDisplayLabel(item) {
  return String(item?.display_name || item?.key || '').trim();
}

/** ``origin`` 展示文案。 */
export function getDataContractOriginLabel(origin) {
  return String(origin || '').trim().toLowerCase() === 'userspace' ? '自定义' : '系统';
}

function mapContractItems(items) {
  return (Array.isArray(items) ? items : []).map((item) => ({
    id: String(item.key || '').trim(),
    key: String(item.key || '').trim(),
    display_name: getDataContractDisplayLabel(item),
    is_time_series: Boolean(item.is_time_series),
    is_per_entity: Boolean(item.is_per_entity),
    origin: String(item.origin || 'system').trim().toLowerCase() === 'userspace' ? 'userspace' : 'system',
    is_custom: Boolean(item.is_custom),
  }));
}

/**
 * DC-01：Data contract 目录
 * @returns {Promise<{ data: object[], total: number }>}
 */
export async function fetchDataContractList({ page = 1, limit = 200 } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(limit),
  });
  const json = await request.getJson(`${API_DATA_CONTRACTS_LIST}?${params.toString()}`);
  const m = json?.message || {};
  const items = Array.isArray(m.items) ? m.items : [];
  return {
    data: mapContractItems(items),
    total: Number(m.total) || items.length,
  };
}

/**
 * DC-02：强制重新发现系统 + userspace 契约（更新进程内注册表，无需重启 NTQ）
 * @returns {Promise<{ data: object[], total: number, reloaded: boolean }>}
 */
export async function reloadDataContractCatalog({ page = 1, limit = 500 } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    limit: String(limit),
  });
  const json = await request.postJson(`${API_DATA_CONTRACTS_RELOAD}?${params.toString()}`, {
    body: {},
  });
  const m = json?.message || {};
  const items = Array.isArray(m.items) ? m.items : [];
  return {
    data: mapContractItems(items),
    total: Number(m.total) || items.length,
    reloaded: Boolean(m.reloaded),
  };
}
