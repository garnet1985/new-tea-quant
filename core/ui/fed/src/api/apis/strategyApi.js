import { requestJson } from '../global/httpClient';
import { API_VERSION_PREFIX } from '../conf/apiConfig';

const API_BASE = `${API_VERSION_PREFIX}/strategies`;

/**
 * 获取已发现策略列表（策略工作台 list 页使用）
 * BFF 返回：{ status: 'ok', message: { strategies: [...] } }
 * @returns {Promise<{ data: object[] }>}
 */
export async function fetchStrategyList() {
  const json = await requestJson(API_BASE, { method: 'GET' });
  const list = json?.message?.strategies || [];
  return {
    data: list.map((item) => ({
      id: item.key || item.name,
      name: item.name || item.key,
      description: item.description || '',
      is_enabled: Boolean(item.is_enabled),
      is_valid: item.is_valid !== false,
    })),
  };
}

/** 构建策略调试页路径（与路由定义保持一致） */
export function getStrategyConsolePath(strategyName) {
  return `/strategy-workbench/${encodeURIComponent(strategyName)}`;
}
