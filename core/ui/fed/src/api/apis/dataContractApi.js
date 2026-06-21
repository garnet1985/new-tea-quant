import { requestJson } from '../global/httpClient';
import { API_VERSION_PREFIX } from '../conf/apiConfig';

const API_DATA_CONTRACTS_LIST = `${API_VERSION_PREFIX}/data-contracts/list`;

/** 列表展示名：优先 ``display_name``，否则 ``key``。 */
export function getDataContractDisplayLabel(item) {
  return String(item?.display_name || item?.key || '').trim();
}

/** ``origin`` 展示文案。 */
export function getDataContractOriginLabel(origin) {
  return String(origin || '').trim().toLowerCase() === 'userspace' ? '自定义' : '系统';
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
  const json = await requestJson(`${API_DATA_CONTRACTS_LIST}?${params.toString()}`, { method: 'GET' });
  const m = json?.message || {};
  const items = Array.isArray(m.items) ? m.items : [];
  return {
    data: items.map((item) => ({
      id: String(item.key || '').trim(),
      key: String(item.key || '').trim(),
      display_name: getDataContractDisplayLabel(item),
      is_time_series: Boolean(item.is_time_series),
      is_per_entity: Boolean(item.is_per_entity),
      origin: String(item.origin || 'system').trim().toLowerCase() === 'userspace' ? 'userspace' : 'system',
      is_custom: Boolean(item.is_custom),
    })),
    total: Number(m.total) || items.length,
  };
}
