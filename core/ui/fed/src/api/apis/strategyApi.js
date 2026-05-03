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
    settings_source: json?.message?.settings_source,
    workbench_version_id: json?.message?.workbench_version_id,
  };
}

/**
 * 将当前参数写入 userspace 策略 `settings.py`（显式发布，非快照保存）。
 * @param {string} strategyName
 * @param {object} settings
 */
export async function applyStrategySettingsToUserspace(strategyName, settings) {
  const json = await requestJson(
    `${API_BASE}/${encodeURIComponent(strategyName)}/settings/apply-to-userspace`,
    {
      method: 'POST',
      body: JSON.stringify({ settings }),
    },
  );
  return {
    strategy_name: json?.message?.strategy_name || strategyName,
    applied: Boolean(json?.message?.applied),
  };
}

/**
 * SWB-17：读取策略工作台版本列表。
 * @param {string} strategyName
 * @returns {Promise<{ versions: Array<{ version_id: string, version: number, created_at: string, updated_at: string }> }>}
 */
export async function fetchStrategyVersions(strategyName) {
  const json = await requestJson(`${API_BASE}/${encodeURIComponent(strategyName)}/versions`, { method: 'GET' });
  return {
    versions: json?.message?.versions ?? [],
  };
}

/**
 * SWB-18：读取单个版本详情。
 * @param {string} strategyName
 * @param {string} versionId
 * @returns {Promise<{ version_id: string, settings: object }>}
 */
export async function fetchStrategyVersionDetail(strategyName, versionId) {
  const json = await requestJson(
    `${API_BASE}/${encodeURIComponent(strategyName)}/versions/${encodeURIComponent(versionId)}`,
    { method: 'GET' },
  );
  return {
    version_id: json?.message?.version_id || versionId,
    settings: json?.message?.settings || {},
  };
}

/**
 * SWB-19：恢复指定版本到当前 settings。
 * @param {string} strategyName
 * @param {string} versionId
 * @returns {Promise<{ restored: boolean, version_id: string }>}
 */
export async function restoreStrategyVersion(strategyName, versionId) {
  const json = await requestJson(
    `${API_BASE}/${encodeURIComponent(strategyName)}/versions/${encodeURIComponent(versionId)}/restore`,
    { method: 'POST' },
  );
  return {
    restored: Boolean(json?.message?.restored),
    version_id: json?.message?.version_id || versionId,
    restored_from_version_id: json?.message?.restored_from_version_id,
  };
}

/**
 * SWB-20：固化当前工作台配置为后端版本。
 * @param {string} strategyName
 * @param {object} settings
 * @param {string=} source
 * @returns {Promise<{ version_id: string, created: boolean }>}
 */
export async function createStrategyVersion(strategyName, settings, source = 'manual_apply') {
  const json = await requestJson(`${API_BASE}/${encodeURIComponent(strategyName)}/versions`, {
    method: 'POST',
    body: JSON.stringify({
      source,
      source_ref: null,
      settings,
    }),
  });
  return {
    version_id: json?.message?.version_id || '',
    created: Boolean(json?.message?.created),
  };
}

/**
 * SWB-06：启动执行 run。
 * @param {string} strategyName
 * @param {'enum'|'price'|'capital'} targetStep
 * @param {object=} settings
 */
export async function startStrategyRun(strategyName, targetStep, settings, options = {}) {
  const isForce = Boolean(options?.is_force);
  const workbenchVersionId =
    typeof options?.workbench_version_id === 'string' ? options.workbench_version_id.trim() : '';
  const body = {
    target_step: targetStep,
    settings: settings && typeof settings === 'object' ? settings : undefined,
    is_force: isForce,
  };
  if (workbenchVersionId) {
    body.workbench_version_id = workbenchVersionId;
  }
  const json = await requestJson(`${API_BASE}/${encodeURIComponent(strategyName)}/runs`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
  return json?.message || {};
}

/**
 * 枚举复用预判：与真实枚举相同的 preprocess/plan_reuse，不跑子进程。
 * 若 would_reuse_full 为 true，message.enum_result_preview 为磁盘元数据中的摘要（与 REUSE_FULL 跑完一致）。
 * @param {string} strategyName
 */
export async function fetchEnumeratorReusePreview(strategyName) {
  const json = await requestJson(
    `${API_BASE}/${encodeURIComponent(strategyName)}/enumerator-reuse-preview`,
    { method: 'GET' },
  );
  return json?.message || {};
}

/**
 * SWB-07：读取执行状态。
 * @param {string} strategyName
 * @param {string} runId
 */
export async function fetchStrategyRunStatus(strategyName, runId) {
  const json = await requestJson(
    `${API_BASE}/${encodeURIComponent(strategyName)}/runs/${encodeURIComponent(runId)}`,
    { method: 'GET' },
  );
  return json?.message || {};
}

/**
 * SWB-09：读取执行摘要结果。
 * @param {string} strategyName
 * @param {string} runId
 */
export async function fetchStrategyRunResults(strategyName, runId) {
  const json = await requestJson(
    `${API_BASE}/${encodeURIComponent(strategyName)}/run-results/${encodeURIComponent(runId)}`,
    { method: 'GET' },
  );
  return json?.message || {};
}

/**
 * SWB-10：工作台快照版本标识列表（含 latest），供下拉等选用。
 * @param {string} strategyName
 * @returns {Promise<{ versions: string[] }>}
 */
export async function fetchStrategyVersionHistory(strategyName) {
  const json = await requestJson(
    `${API_BASE}/${encodeURIComponent(strategyName)}/version-history`,
    { method: 'GET' },
  );
  return json?.message || {};
}

/**
 * SWB-11：读取报告摘要。
 * @param {string} strategyName
 * @param {string} runId
 * @param {string[]} [reportTypes]
 */
export async function fetchStrategyReports(strategyName, runId, reportTypes) {
  const params = new URLSearchParams();
  if (Array.isArray(reportTypes) && reportTypes.length > 0) {
    params.set('report_types', reportTypes.join(','));
  }
  const query = params.toString();
  const json = await requestJson(
    `${API_BASE}/${encodeURIComponent(strategyName)}/reports/${encodeURIComponent(runId)}${query ? `?${query}` : ''}`,
    { method: 'GET' },
  );
  return json?.message || {};
}

/**
 * SWB-12：读取报告样本股票表。
 * @param {string} strategyName
 * @param {string} runId
 * @param {'enum'|'price'|'capital'} reportType
 * @param {{limit?: number, search?: string, sortBy?: string, sortOrder?: 'asc'|'desc'}} [options]
 */
export async function fetchStrategyReportStocks(strategyName, runId, reportType, options = {}) {
  const params = new URLSearchParams();
  params.set('report_type', reportType);
  if (Number.isFinite(options.limit)) params.set('limit', String(options.limit));
  if (options.search) params.set('search', options.search);
  if (options.sortBy) params.set('sort_by', options.sortBy);
  if (options.sortOrder) params.set('sort_order', options.sortOrder);
  const json = await requestJson(
    `${API_BASE}/${encodeURIComponent(strategyName)}/reports/${encodeURIComponent(runId)}/stocks?${params.toString()}`,
    { method: 'GET' },
  );
  return json?.message || {};
}

/**
 * SWB-13：读取单股票 K 线与买卖点。
 * @param {string} strategyName
 * @param {string} runId
 * @param {string} stockId
 */
export async function fetchStrategyReportStockKline(strategyName, runId, stockId) {
  const json = await requestJson(
    `${API_BASE}/${encodeURIComponent(strategyName)}/reports/${encodeURIComponent(runId)}/stocks/${encodeURIComponent(stockId)}/kline`,
    { method: 'GET' },
  );
  return json?.message || {};
}

/**
 * SWB-14：读取报告对比数据。
 * @param {string} strategyName
 * @param {string} baseRunId
 * @param {string} compareVersion
 * @param {'enum'|'price'|'capital'} [reportType]
 */
export async function fetchStrategyReportCompare(strategyName, baseRunId, compareVersion, reportType) {
  const params = new URLSearchParams();
  params.set('base_run_id', baseRunId);
  params.set('compare_version', compareVersion);
  if (reportType) params.set('report_type', reportType);
  const json = await requestJson(
    `${API_BASE}/${encodeURIComponent(strategyName)}/reports/compare?${params.toString()}`,
    { method: 'GET' },
  );
  return json?.message || {};
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
