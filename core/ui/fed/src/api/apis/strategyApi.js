import { requestJson } from '../global/httpClient';
import { API_VERSION_PREFIX } from '../conf/apiConfig';

/** 分页策略列表（V2-02）：`/api/v1/strategies/list` */
const API_STRATEGIES_LIST_BASE = `${API_VERSION_PREFIX}/strategies/list`;
/** 单策略工作台资源前缀（V2-01…09）：`/api/v1/strategy/{name}/…`（注意单数 `strategy`） */
function apiStrategyPath(strategyName) {
  return `${API_VERSION_PREFIX}/strategy/${encodeURIComponent(strategyName)}`;
}
/** V2-04 全局选项（无 strategy_name 路径段） */
const API_SETTINGS_CAPITAL = `${API_VERSION_PREFIX}/strategy/settings/capital-allocation-strategies`;
const API_SETTINGS_SAMPLING = `${API_VERSION_PREFIX}/strategy/settings/sampling-strategies`;

/** @typedef {{ value: string, label: string }} StrategySettingOption */
/** @typedef {{ configurable_fields: string[], required_fields: string[] }} StrategySettingProfile */

/**
 * 获取已发现策略列表（策略工作台 list 页使用）
 * V2 BFF：`GET /api/v1/strategies/list` → `{ status, message: { items, total, page, limit } }`
 * @returns {Promise<{ data: object[] }>}
 */
export async function fetchStrategyList() {
  const params = new URLSearchParams({ page: '1', limit: '100' });
  const json = await requestJson(`${API_STRATEGIES_LIST_BASE}?${params.toString()}`, { method: 'GET' });
  const list = json?.message?.items || [];
  return {
    data: list.map((item) => ({
      id: item.name,
      name: item.name,
      description: item.worker_class_name || item.folder || '',
      is_enabled: Boolean(item.is_enabled),
    })),
  };
}

/** 构建单策略策略工作台（调试）页路径（与路由定义保持一致） */
export function getStrategyWorkbenchPath(strategyName) {
  return `/strategy-workbench/${encodeURIComponent(strategyName)}`;
}

/**
 * V2-01：读取 latest 工作台快照（settings + version_id + step_status + result_report）。
 * @param {string} strategyName
 * @returns {Promise<{ strategy_name: string, settings: object, workbench_version_id?: string }>}
 */
export async function fetchStrategySettings(strategyName) {
  const json = await requestJson(`${apiStrategyPath(strategyName)}/version/latest`, { method: 'GET' });
  const m = json?.message || {};
  return {
    strategy_name: strategyName,
    settings: m.settings || {},
    settings_source: undefined,
    workbench_version_id: typeof m.version_id === 'string' ? m.version_id : '',
    step_status: m.step_status,
    result_report: m.result_report,
  };
}

/**
 * V2-09：将**指定快照版本**的 settings 写入 userspace `settings.py`。
 * 若未传 `versionId`，则用当前 **latest**（先隐式依赖 V2-01）的 `version_id`。
 * @param {string} strategyName
 * @param {object} _settings 保留参数兼容旧调用；V2 以服务端快照为准，此参数不参与请求体
 * @param {{ version_id?: string }} [opts]
 */
export async function applyStrategySettingsToUserspace(strategyName, _settings, opts = {}) {
  let versionId = typeof opts.version_id === 'string' ? opts.version_id.trim() : '';
  if (!versionId) {
    const latest = await fetchStrategySettings(strategyName);
    versionId = (latest.workbench_version_id || '').trim();
  }
  if (!versionId) {
    throw new Error('缺少工作台 version_id，无法发布（请先加载有效快照）');
  }
  const json = await requestJson(
    `${apiStrategyPath(strategyName)}/apply-settings/${encodeURIComponent(versionId)}`,
    {
      method: 'POST',
      body: JSON.stringify({}),
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
  const json = await requestJson(`${apiStrategyPath(strategyName)}/versions`, { method: 'GET' });
  const items = json?.message?.items ?? [];
  return {
    versions: items.map((row) => ({
      version_id: row.version_id || (row.snapshot_id != null ? `v${row.snapshot_id}` : ''),
      version: Number(row.snapshot_id || 0),
      created_at: row.created_at || '',
      updated_at: row.updated_at || '',
    })),
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
    `${apiStrategyPath(strategyName)}/version/${encodeURIComponent(versionId)}`,
    { method: 'GET' },
  );
  const m = json?.message || {};
  return {
    version_id: m.version_id || versionId,
    settings: m.settings || {},
    step_status: m.step_status,
    result_report: m.result_report,
  };
}

/**
 * 恢复历史版本到工作台：无单独 V2 restore；校验 **V2-08** 可读后由前端再 **GET V2-01** 刷新。
 * @param {string} strategyName
 * @param {string} versionId
 * @returns {Promise<{ restored: boolean, version_id: string }>}
 */
export async function restoreStrategyVersion(strategyName, versionId) {
  await fetchStrategyVersionDetail(strategyName, versionId);
  return {
    restored: true,
    version_id: versionId,
  };
}

/**
 * 固化快照：V2 暂无对应接口（占位）。
 */
export async function createStrategyVersion(strategyName, settings, source = 'manual_apply') {
  void strategyName;
  void settings;
  void source;
  throw new Error('createStrategyVersion：当前 V2 契约未提供该接口');
}

/**
 * V2-05：启动单步 run（路径含 step）。
 * @param {string} strategyName
 * @param {'enum'|'price'|'capital'} targetStep
 * @param {object=} settings
 */
export async function startStrategyRun(strategyName, targetStep, settings, options = {}) {
  const isForce = Boolean(options?.is_force);
  const body = {
    settings: settings && typeof settings === 'object' ? settings : {},
    is_force: isForce,
  };
  const json = await requestJson(
    `${apiStrategyPath(strategyName)}/${encodeURIComponent(targetStep)}/run`,
    { method: 'POST', body: JSON.stringify(body) },
  );
  const m = json?.message || {};
  if (!m.is_triggered) {
    const reason = m.reason;
    throw new Error(typeof reason === 'string' ? reason : '启动失败');
  }
  const jid = m.job_id || '';
  return {
    run_id: jid,
    job_id: jid,
    resolved_chain: [targetStep],
  };
}

/**
 * 枚举复用预判：前端不对缓存感知；占位返回。
 */
export async function fetchEnumeratorReusePreview(strategyName) {
  void strategyName;
  return {};
}

/**
 * V2-06：读取 step 进度（query `job_id`）。返回形状兼容执行面板旧 `applyStatus`。
 * @param {string} strategyName
 * @param {string} jobId
 * @param {'enum'|'price'|'capital'} [step='enum']
 */
/**
 * V2-07：按路径 ``version_id`` 读取该步 ``report`` 槽位 JSON。
 * @param {string} strategyName
 * @param {'enum'|'price'|'capital'} step
 * @param {string} versionId 如 ``v3`` / ``3``
 */
export async function fetchStrategyStepReport(strategyName, step, versionId) {
  const vid = encodeURIComponent(String(versionId || '').trim());
  if (!vid) {
    throw new Error('缺少 version_id');
  }
  const json = await requestJson(
    `${apiStrategyPath(strategyName)}/${encodeURIComponent(step)}/report/${vid}`,
    { method: 'GET' },
  );
  return json?.message || {};
}

/**
 * 枚举逐股 ref（``0_stock_ref.json``）；不存在时返回 ``null``（不抛错）。
 * @param {string} strategyName
 * @param {'enum'|'price'|'capital'} step
 * @param {string} versionId
 * @returns {Promise<object|null>}
 */
export async function fetchStrategyStepReportRef(strategyName, step, versionId) {
  const vid = encodeURIComponent(String(versionId || '').trim());
  if (!vid) {
    return null;
  }
  const url = `${apiStrategyPath(strategyName)}/${encodeURIComponent(step)}/report_ref/${vid}`;
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
  });
  let json = {};
  try {
    json = await response.json();
  } catch {
    return null;
  }
  if (!response.ok || json?.status !== 'ok') {
    return null;
  }
  return json?.message || null;
}

export async function fetchStrategyRunStatus(strategyName, jobId, step = 'enum') {
  const json = await requestJson(
    `${apiStrategyPath(strategyName)}/${encodeURIComponent(step)}/progress?job_id=${encodeURIComponent(jobId)}`,
    { method: 'GET' },
  );
  const m = json?.message || {};
  const prog = Number(m.progress ?? 0);
  const rawStatus = String(m.status || '');
  const failed = rawStatus === 'failed';
  const completed = rawStatus === 'completed';
  const running = rawStatus === 'running' || rawStatus === 'queued';

  const stepVal = completed ? 'done' : failed ? 'failed' : (running || (prog > 0 && prog < 100)) ? 'running' : 'idle';

  const snapshotId = m.snapshot_id != null ? Number(m.snapshot_id) : null;
  const versionId = typeof m.version_id === 'string' ? m.version_id : '';
  const resultReport = m.result_report && typeof m.result_report === 'object' ? m.result_report : {};

  return {
    run_id: m.job_id || jobId,
    progress_pct: prog,
    state: completed ? 'done' : failed ? 'failed' : 'running',
    running_step: running || (prog > 0 && prog < 100) ? step : '',
    step_status: {
      enum: step === 'enum' ? stepVal : 'idle',
      price: step === 'price' ? stepVal : 'idle',
      capital: step === 'capital' ? stepVal : 'idle',
    },
    snapshot_id: Number.isFinite(snapshotId) && snapshotId > 0 ? snapshotId : null,
    version_id: versionId,
    result_report: resultReport,
  };
}

/**
 * 执行摘要（旧 SWB）：暂无 V2；占位。
 */
export async function fetchStrategyRunResults(strategyName, runId) {
  void strategyName;
  void runId;
  return {};
}

/**
 * SWB-10：工作台快照版本标识列表（含 latest），供下拉等选用。
 * @param {string} strategyName
 * @returns {Promise<{ versions: string[] }>}
 */
export async function fetchStrategyVersionHistory(strategyName) {
  const json = await requestJson(`${apiStrategyPath(strategyName)}/versions`, { method: 'GET' });
  const items = json?.message?.items ?? [];
  const ids = items
    .map((row) => (typeof row.version_id === 'string' ? row.version_id.trim() : ''))
    .filter(Boolean);
  return { versions: ids.length ? ['latest', ...ids] : ['latest'] };
}

/**
 * SWB-11：读取报告摘要。
 * @param {string} strategyName
 * @param {string} runId
 * @param {string[]} [reportTypes]
 */
export async function fetchStrategyReports(strategyName, runId, reportTypes) {
  void strategyName;
  void runId;
  void reportTypes;
  return {};
}

/**
 * SWB-12：读取报告样本股票表。
 * @param {string} strategyName
 * @param {string} runId
 * @param {'enum'|'price'|'capital'} reportType
 * @param {{limit?: number, search?: string, sortBy?: string, sortOrder?: 'asc'|'desc'}} [options]
 */
export async function fetchStrategyReportStocks(strategyName, runId, reportType, options = {}) {
  void strategyName;
  void runId;
  void reportType;
  void options;
  return {};
}

/**
 * SWB-13：读取单股票 K 线与买卖点。
 * @param {string} strategyName
 * @param {string} runId
 * @param {string} stockId
 */
export async function fetchStrategyReportStockKline(strategyName, runId, stockId) {
  void strategyName;
  void runId;
  void stockId;
  return {};
}

/**
 * SWB-14：读取报告对比数据。
 * @param {string} strategyName
 * @param {string} baseRunId
 * @param {string} compareVersion
 * @param {'enum'|'price'|'capital'} [reportType]
 */
export async function fetchStrategyReportCompare(strategyName, baseRunId, compareVersion, reportType) {
  void strategyName;
  void baseRunId;
  void compareVersion;
  void reportType;
  return {};
}

/**
 * SWB-02：资金分配模式选项（`capital_simulator.allocation.mode`）
 * @returns {Promise<StrategySettingOption[]>}
 */
export async function fetchCapitalAllocationModeOptions() {
  const json = await requestJson(API_SETTINGS_CAPITAL, { method: 'GET' });
  const items = json?.message?.items ?? [];
  return items.map((row) => ({ value: row.value, label: row.label }));
}

/**
 * SWB-02：资金分配模式选项 + 联动字段 profile。
 * @returns {Promise<{ options: StrategySettingOption[], profiles: Record<string, StrategySettingProfile> }>}
 */
export async function fetchCapitalAllocationModeConfig() {
  const json = await requestJson(API_SETTINGS_CAPITAL, { method: 'GET' });
  const items = json?.message?.items ?? [];
  return {
    options: items.map((row) => ({ value: row.value, label: row.label })),
    profiles: {},
  };
}

/**
 * SWB-03：股票采样策略选项（`sampling.strategy`）
 * @returns {Promise<StrategySettingOption[]>}
 */
export async function fetchSamplingStrategyOptions() {
  const json = await requestJson(API_SETTINGS_SAMPLING, { method: 'GET' });
  const items = json?.message?.items ?? [];
  return items.map((row) => ({ value: row.value, label: row.label }));
}

/**
 * SWB-03：采样策略选项 + 联动字段 profile。
 * @returns {Promise<{ options: StrategySettingOption[], profiles: Record<string, StrategySettingProfile> }>}
 */
export async function fetchSamplingStrategyConfig() {
  const json = await requestJson(API_SETTINGS_SAMPLING, { method: 'GET' });
  const items = json?.message?.items ?? [];
  return {
    options: items.map((row) => ({ value: row.value, label: row.label })),
    profiles: {},
  };
}
