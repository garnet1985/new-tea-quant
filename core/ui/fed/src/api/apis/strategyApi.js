import { requestJson } from '../global/httpClient';
import { API_VERSION_PREFIX } from '../conf/apiConfig';

const API_BASE = `${API_VERSION_PREFIX}/strategies`;

/** @typedef {{ value: string, label: string }} StrategySettingOption */
/** @typedef {{ configurable_fields: string[], required_fields: string[] }} StrategySettingProfile */

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
    })),
  };
}

/** 构建单策略策略工作台（调试）页路径（与路由定义保持一致） */
export function getStrategyWorkbenchPath(strategyName) {
  return `/strategy-workbench/${encodeURIComponent(strategyName)}`;
}

/**
 * SWB-04：读取单策略完整 settings。
 * @param {string} strategyName
 * @returns {Promise<{ strategy_name: string, settings: object }>}
 */
export async function fetchStrategySettings(strategyName) {
  const json = await requestJson(`${API_BASE}/${encodeURIComponent(strategyName)}/settings`, { method: 'GET' });
  return {
    strategy_name: json?.message?.strategy_name || strategyName,
    settings: json?.message?.settings || {},
  };
}

/**
 * SWB-05：保存单策略完整 settings。
 * @param {string} strategyName
 * @param {object} settings
 * @returns {Promise<{ strategy_name: string, saved: boolean }>}
 */
export async function saveStrategySettings(strategyName, settings) {
  const json = await requestJson(`${API_BASE}/${encodeURIComponent(strategyName)}/settings`, {
    method: 'PUT',
    body: JSON.stringify({ settings }),
  });
  return {
    strategy_name: json?.message?.strategy_name || strategyName,
    saved: Boolean(json?.message?.saved),
  };
}

/**
 * SWB-02：资金分配模式选项（`capital_simulator.allocation.mode`）
 * @returns {Promise<StrategySettingOption[]>}
 */
export async function fetchCapitalAllocationModeOptions() {
  const json = await requestJson(`${API_BASE}/settings-options/allocation-modes`, { method: 'GET' });
  return json?.message?.options ?? [];
}

/**
 * SWB-02：资金分配模式选项 + 联动字段 profile。
 * @returns {Promise<{ options: StrategySettingOption[], profiles: Record<string, StrategySettingProfile> }>}
 */
export async function fetchCapitalAllocationModeConfig() {
  const json = await requestJson(`${API_BASE}/settings-options/allocation-modes`, { method: 'GET' });
  return {
    options: json?.message?.options ?? [],
    profiles: json?.message?.profiles ?? {},
  };
}

/**
 * SWB-03：股票采样策略选项（`sampling.strategy`）
 * @returns {Promise<StrategySettingOption[]>}
 */
export async function fetchSamplingStrategyOptions() {
  const json = await requestJson(`${API_BASE}/settings-options/sampling-strategies`, { method: 'GET' });
  return json?.message?.options ?? [];
}

/**
 * SWB-03：采样策略选项 + 联动字段 profile。
 * @returns {Promise<{ options: StrategySettingOption[], profiles: Record<string, StrategySettingProfile> }>}
 */
export async function fetchSamplingStrategyConfig() {
  const json = await requestJson(`${API_BASE}/settings-options/sampling-strategies`, { method: 'GET' });
  return {
    options: json?.message?.options ?? [],
    profiles: json?.message?.profiles ?? {},
  };
}
