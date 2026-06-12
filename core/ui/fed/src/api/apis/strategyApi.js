import { requestJson } from '../global/httpClient';
import { API_VERSION_PREFIX } from '../conf/apiConfig';

/** 分页策略列表（V2-02）：`/api/v1/strategies/list` */
const API_STRATEGIES_LIST_BASE = `${API_VERSION_PREFIX}/strategies/list`;
/** 策略列表/扫描页展示名：优先 ``display_name``，否则回退路径 ID。 */
export function getStrategyDisplayLabel(item) {
  return String(item?.display_name || item?.name || '').trim();
}

/** 将策略路径 ID（可含 ``/``）编码为 URL 路径段。 */
function encodeStrategyPathSegments(strategyName) {
  return String(strategyName || '')
    .split('/')
    .filter(Boolean)
    .map((seg) => encodeURIComponent(seg))
    .join('/');
}

/** 单策略工作台资源前缀（V2-01…09）：`/api/v1/strategy/{name}/…`（注意单数 `strategy`） */
function apiStrategyPath(strategyName) {
  const encoded = encodeStrategyPathSegments(strategyName);
  return `${API_VERSION_PREFIX}/strategy/${encoded}`;
}
/** V2-04 全局选项（无 strategy_name 路径段） */
const API_SETTINGS_CAPITAL = `${API_VERSION_PREFIX}/strategy/settings/capital-allocation-strategies`;
const API_SETTINGS_SAMPLING = `${API_VERSION_PREFIX}/strategy/settings/sampling-strategies`;
const API_SETTINGS_SIMULATION_TEMPLATES = `${API_VERSION_PREFIX}/strategy/settings/simulation-templates`;
const API_SETTINGS_SKIP_INVESTMENT_WHEN = `${API_VERSION_PREFIX}/strategy/settings/skip-investment-when`;
const API_SETTINGS_MARKET_PROFILES = `${API_VERSION_PREFIX}/strategy/settings/market-profiles`;

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
      display_name: getStrategyDisplayLabel(item),
      description: String(item.description || '').trim(),
      keywords: Array.isArray(item.keywords) ? item.keywords : [],
      details: item.details && typeof item.details === 'object' ? item.details : null,
      is_enabled: Boolean(item.is_enabled),
    })),
  };
}

/**
 * 扫描按钮语义（与当前 demo 模式、磁盘结果对齐）；BFF 仅透传 `primary_action`。
 * GET /api/v1/strategy/{strategy_name}/scan?demo=0|1
 */
export async function fetchStrategyScanReadiness(strategyName, { demo = false } = {}) {
  const params = new URLSearchParams({ demo: demo ? '1' : '0' });
  const json = await requestJson(`${apiStrategyPath(strategyName)}/scan?${params.toString()}`, { method: 'GET' });
  const m = json?.message || {};
  const report = m.report && typeof m.report === 'object' ? m.report : null;
  return {
    primary_action: m.primary_action === 'rerun' ? 'rerun' : 'run',
    report,
  };
}

/**
 * 启动单策略扫描（机会扫描页使用）
 * BFF：`POST /api/v1/strategy/{strategy_name}/scan?demo=0|1&force=0|1`
 */
export async function startStrategyScan(strategyName, { demo = false, force = false } = {}) {
  const params = new URLSearchParams({ demo: demo ? '1' : '0' });
  if (force) params.set('force', '1');
  const json = await requestJson(`${apiStrategyPath(strategyName)}/scan?${params.toString()}`, { method: 'POST' });
  const m = json?.message || {};
  return {
    strategy_name: m.strategy_name || strategyName,
    job_id: m.job_id || '',
    demo: Boolean(m.demo),
    force: Boolean(m.force),
  };
}

/**
 * 轮询单策略扫描进度
 * BFF：`GET /api/v1/strategy/{strategy_name}/scan/progress?job_id=...`
 */
export async function fetchStrategyScanProgress(strategyName, jobId) {
  const params = new URLSearchParams({ job_id: String(jobId || '') });
  const json = await requestJson(`${apiStrategyPath(strategyName)}/scan/progress?${params.toString()}`, { method: 'GET' });
  return json?.message || {};
}

/** 构建单策略策略工作台（调试）页路径（与路由定义保持一致） */
export function getStrategyWorkbenchPath(strategyName) {
  const encoded = encodeStrategyPathSegments(strategyName);
  return `/strategy-workbench/${encoded}`;
}

/** 制定策略：单策略调试页路径（可选 step：enum | price | capital） */
export function getStrategyDesignPath(strategyName, step = '') {
  const encoded = encodeStrategyPathSegments(strategyName);
  const base = `/strategy-design/${encoded}`;
  const seg = String(step || '').trim();
  if (seg === 'enum' || seg === 'price' || seg === 'capital') {
    return `${base}/${seg}`;
  }
  return base;
}

/**
 * V2-01：读取 latest 工作台快照（settings + version_id + step_status + result_report）。
 * @param {string} strategyName
 * @returns {Promise<{ strategy_name: string, settings: object, workbench_version_id?: string, has_persisted_snapshot?: boolean, has_other_versions?: boolean }>}
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
    execution_panel: m.execution_panel ?? null,
    has_persisted_snapshot: Boolean(m.has_persisted_snapshot),
    has_other_versions: Boolean(m.has_other_versions),
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
      version_id: row.version_id || (row.version != null ? `v${row.version}` : ''),
      version: Number(row.version ?? 0),
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
    execution_panel: m.execution_panel ?? null,
  };
}

/**
 * 恢复历史版本到工作台：无单独写库 restore；以 **V2-08** ``GET …/version/{id}`` 的快照正文为准。
 * 与 ``GET …/version/latest`` 正文同形（冷启动仅 latest 有合成行）；前端页面加载仍用 latest，恢复快照只用 detail。
 * @param {string} strategyName
 * @param {string} versionId
 * @returns {Promise<{ restored: boolean, version_id: string, detail: object }>}
 */
export async function restoreStrategyVersion(strategyName, versionId) {
  const detail = await fetchStrategyVersionDetail(strategyName, versionId);
  return {
    restored: true,
    version_id: versionId,
    detail,
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
 * V2-05：启动 run（路径上的 ``step`` 为用户点击步；实际子步骤链见响应 ``steps`` / ``resolved_chain``，由后端 ``plan_schema`` 规划）。
 * @param {string} strategyName
 * @param {'enum'|'price'|'capital'} targetStep
 * @param {object=} settings
 */
export async function startStrategyRun(strategyName, targetStep, settings, options = {}) {
  const forceRefresh = Boolean(options?.force_refresh);
  const body = {
    settings: settings && typeof settings === 'object' ? settings : {},
    force_refresh: forceRefresh,
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
  const steps = Array.isArray(m.steps) ? m.steps : [];
  const resolved_chain = steps.map((row) => String(row.step_name || '').trim()).filter(Boolean);
  return {
    run_id: m.run_id || jid,
    job_id: jid,
    steps,
    resolved_chain: resolved_chain.length ? resolved_chain : [targetStep],
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
 * 枚举逐股 ref（``0_stock_ref.json``）。成功时 ``message.stock_ref`` 可为 ``null``（磁盘已清理），
 * 此时 ``stock_ref_available === false``；仅快照不存在时 HTTP 非 2xx。
 * @param {string} strategyName
 * @param {'enum'|'price'|'capital'} step
 * @param {string} versionId
 * @returns {Promise<object|null>}
 */
/**
 * V2-07c：单股 K 线 + 步骤 markers。
 * GET /api/v1/strategy/{name}/{step}/stock/{stock_id}?version_id=...
 */
export async function fetchStrategyStockDetail(strategyName, step, versionId, stockId) {
  const vid = encodeURIComponent(String(versionId || '').trim());
  const code = encodeURIComponent(String(stockId || '').trim());
  if (!vid || !code) {
    throw new Error('缺少 version_id 或 stock_id');
  }
  const params = new URLSearchParams({ version_id: String(versionId || '').trim() });
  const url = `${apiStrategyPath(strategyName)}/${encodeURIComponent(step)}/stock/${code}?${params.toString()}`;
  const json = await requestJson(url, { method: 'GET' });
  return json?.message || {};
}

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

/**
 * V2-06b：整次 run 编排进度（``steps[]``），不依赖路径 ``step``。
 * @param {string} strategyName
 * @param {string} jobId
 */
export async function fetchStrategyRunProgress(strategyName, jobId) {
  const json = await requestJson(
    `${apiStrategyPath(strategyName)}/run/progress?job_id=${encodeURIComponent(jobId)}`,
    { method: 'GET' },
  );
  return json?.message || null;
}

/**
 * 将 ``GET …/run/progress`` 正文映射为执行面板 ``applyStatus`` 所需字段。
 * @param {object|null} envelope
 */
export function mapWorkbenchRunProgressToPanel(envelope) {
  const steps = Array.isArray(envelope?.steps) ? envelope.steps : [];
  const phase = String(envelope?.phase || '').toLowerCase();
  const runProgress = envelope?.run_progress && typeof envelope.run_progress === 'object'
    ? envelope.run_progress
    : null;

  const step_status_merge = {};
  const step_progress = {};
  steps.forEach((row) => {
    const k = String(row.step_name || '').trim();
    if (k !== 'enum' && k !== 'price' && k !== 'capital') return;
    const st = String(row.status || '').toLowerCase();
    if (st === 'pending') step_status_merge[k] = 'pending';
    else if (st === 'running') step_status_merge[k] = 'running';
    else if (st === 'completed') step_status_merge[k] = 'done';
    else if (st === 'failed') step_status_merge[k] = 'failed';
    else step_status_merge[k] = 'idle';
    step_progress[k] = Number(row.progress ?? 0);
  });

  const anyFailed = steps.some((r) => String(r.status || '').toLowerCase() === 'failed') || phase === 'failed';
  const allDone =
    steps.length > 0
    && steps.every((r) => String(r.status || '').toLowerCase() === 'completed');
  let state = 'running';
  if (anyFailed) state = 'failed';
  else if (allDone || phase === 'completed') state = 'done';

  let running_step = '';
  ['enum', 'price', 'capital'].forEach((k) => {
    if (step_status_merge[k] === 'running') running_step = k;
  });
  if (!running_step && runProgress?.substep) {
    running_step = String(runProgress.substep).trim();
  }

  let progress_pct = 0;
  if (runProgress && runProgress.pct != null) {
    progress_pct = Number(runProgress.pct);
  } else if (running_step) {
    progress_pct = Number(step_progress[running_step] ?? 0);
  } else if (state === 'done') {
    progress_pct = 100;
  }

  const progress_label = typeof runProgress?.label === 'string' ? runProgress.label.trim() : '';
  const progress_stage_label = typeof runProgress?.substep_stage_label === 'string'
    ? runProgress.substep_stage_label.trim()
    : '';
  const progress_counter_text = typeof runProgress?.counter_text === 'string'
    ? runProgress.counter_text.trim()
    : '';

  let version_id = '';
  steps.forEach((row) => {
    const vid = row?.result?.version_id;
    if (typeof vid === 'string' && vid.trim()) version_id = vid.trim();
  });

  let fail_reason = '';
  if (state === 'failed') {
    const failedRow = steps.find((r) => String(r.status || '').toLowerCase() === 'failed');
    const msg = failedRow?.result?.message;
    fail_reason = typeof msg === 'string' && msg.trim() ? msg.trim() : '';
  }

  return {
    run_id: envelope?.run_id || '',
    step_status_merge,
    step_progress,
    running_step,
    progress_pct,
    progress_label,
    progress_stage_label,
    progress_counter_text,
    state,
    version_id,
    fail_reason,
  };
}

/**
 * V2-06b：轮询整次 run 进度（内部聚合 ``steps``）。
 * 第三参 ``step`` 已废弃，保留签名以兼容旧调用。
 * @param {string} strategyName
 * @param {string} jobId
 * @param {'enum'|'price'|'capital'} [_step]
 */
export async function fetchStrategyRunStatus(strategyName, jobId, _step = 'enum') {
  void _step;
  const envelope = await fetchStrategyRunProgress(strategyName, jobId);
  if (!envelope) {
    return {
      run_id: jobId,
      progress_pct: 0,
      state: 'failed',
      running_step: '',
      step_status_merge: {},
      fail_reason: '无编排进度数据',
    };
  }
  return mapWorkbenchRunProgressToPanel(envelope);
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
 * SWB-13：读取单股票 K 线与买卖点。
 * @param {string} strategyName
 * @param {string} runId
 * @param {string} stockId
 */
/** @deprecated 使用 ``fetchStrategyStockDetail`` */
export async function fetchStrategyReportStockKline(strategyName, runId, stockId) {
  void strategyName;
  void runId;
  void stockId;
  return {};
}

/**
 * SWB-02：资金分配模式选项（`capital_simulator.allocation.mode`）
 * @returns {Promise<StrategySettingOption[]>}
 */
export async function fetchCapitalAllocationModeOptions() {
  const json = await requestJson(API_SETTINGS_CAPITAL, { method: 'GET' });
  const items = json?.message?.items ?? [];
  return items.map((row) => ({
    value: row.value,
    label: row.label,
    tooltip: row.tooltip || '',
  }));
}

/**
 * SWB-02：资金分配模式选项 + 联动字段 profile。
 * @returns {Promise<{ options: StrategySettingOption[], profiles: Record<string, StrategySettingProfile> }>}
 */
export async function fetchCapitalAllocationModeConfig() {
  const json = await requestJson(API_SETTINGS_CAPITAL, { method: 'GET' });
  const items = json?.message?.items ?? [];
  return {
    options: items.map((row) => ({
      value: row.value,
      label: row.label,
      tooltip: row.tooltip || '',
    })),
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
  return items.map((row) => ({
    value: row.value,
    label: row.label,
    tooltip: row.tooltip || '',
  }));
}

/**
 * SWB-03：采样策略选项 + 联动字段 profile。
 * @returns {Promise<{ options: StrategySettingOption[], profiles: Record<string, StrategySettingProfile> }>}
 */
export async function fetchSamplingStrategyConfig() {
  const json = await requestJson(API_SETTINGS_SAMPLING, { method: 'GET' });
  const items = json?.message?.items ?? [];
  return {
    options: items.map((row) => ({
      value: row.value,
      label: row.label,
      tooltip: row.tooltip || '',
    })),
    profiles: {},
  };
}

/**
 * SWB：回测执行模板选项（`simulation.template`）
 * @returns {Promise<StrategySettingOption[]>}
 */
export async function fetchSimulationTemplateOptions() {
  const json = await requestJson(API_SETTINGS_SIMULATION_TEMPLATES, { method: 'GET' });
  const items = json?.message?.items ?? [];
  return items.map((row) => ({
    value: row.value,
    label: row.label,
    tooltip: row.tooltip || '',
  }));
}

/**
 * SWB：回测模板选项 + 联动字段 profile（当前无 profile，与 sampling 对齐）。
 * @returns {Promise<{ options: StrategySettingOption[], profiles: Record<string, StrategySettingProfile> }>}
 */
export async function fetchSimulationTemplateConfig() {
  const json = await requestJson(API_SETTINGS_SIMULATION_TEMPLATES, { method: 'GET' });
  const items = json?.message?.items ?? [];
  const profiles = {};
  items.forEach((row) => {
    if (row?.value && row?.defaults && typeof row.defaults === 'object') {
      profiles[row.value] = row.defaults;
    }
  });
  return {
    options: items.map((row) => ({
      value: row.value,
      label: row.label,
      tooltip: row.tooltip || '',
    })),
    profiles,
  };
}

/**
 * ``simulation.skip_investment_when`` 可勾选标签（``st`` / ``star_st``）。
 * @returns {Promise<StrategySettingOption[]>}
 */
export async function fetchSkipInvestmentWhenOptions() {
  const json = await requestJson(API_SETTINGS_SKIP_INVESTMENT_WHEN, { method: 'GET' });
  const items = json?.message?.items ?? [];
  return items.map((row) => ({
    value: row.value,
    label: row.label,
    tooltip: row.tooltip || '',
  }));
}

/**
 * SWB：市场规则 profile（根级 `market_profile`）
 * @returns {Promise<StrategySettingOption[]>}
 */
export async function fetchMarketProfileOptions() {
  const json = await requestJson(API_SETTINGS_MARKET_PROFILES, { method: 'GET' });
  const items = json?.message?.items ?? [];
  return items.map((row) => ({ value: row.value, label: row.label }));
}

const API_STRATEGY_PACKAGE_IMPORT = `${API_VERSION_PREFIX}/strategy/package/import`;
const API_STRATEGY_PACKAGE_IMPORT_PREVIEW = `${API_VERSION_PREFIX}/strategy/package/import/preview`;

async function readFetchErrorDetail(response) {
  try {
    const json = await response.json();
    return json?.message?.detail || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

/**
 * 下载策略交流包（V2-13）：`GET /api/v1/strategy/{name}/package/export`
 * @param {string} strategyName
 * @param {{ scope?: 'bundle'|'strategy' }} [options]
 */
export async function downloadStrategyPackage(strategyName, { scope = 'bundle' } = {}) {
  const params = new URLSearchParams({ scope });
  const url = `${apiStrategyPath(strategyName)}/package/export?${params.toString()}`;
  const response = await fetch(url, { method: 'GET' });
  if (!response.ok) {
    throw new Error(await readFetchErrorDetail(response));
  }
  const blob = await response.blob();
  let filename = `${strategyName}-strategy.zip`;
  const cd = response.headers.get('Content-Disposition') || '';
  const match = /filename\*?=(?:UTF-8''|utf-8'')?["']?([^"';]+)/i.exec(cd);
  if (match?.[1]) {
    try {
      filename = decodeURIComponent(match[1].trim());
    } catch {
      filename = match[1].trim();
    }
  }
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = href;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(href);
}

/**
 * 策略包导入预览（V2-14）
 * @param {File} file
 * @param {{ policy?: 'reject'|'skip_existing'|'overwrite' }} [options]
 */
export async function previewStrategyPackageImport(file, { policy = 'reject' } = {}) {
  const fd = new FormData();
  fd.append('file', file);
  const params = new URLSearchParams({ policy });
  const response = await fetch(`${API_STRATEGY_PACKAGE_IMPORT_PREVIEW}?${params.toString()}`, {
    method: 'POST',
    body: fd,
  });
  const json = await response.json();
  if (!response.ok || json?.status !== 'ok') {
    throw new Error(json?.message?.detail || `HTTP ${response.status}`);
  }
  return json.message;
}

/**
 * 策略包导入（V2-15）
 * @param {File} file
 * @param {{ policy?: 'reject'|'skip_existing'|'overwrite' }} [options]
 */
export async function importStrategyPackage(file, { policy = 'reject' } = {}) {
  const fd = new FormData();
  fd.append('file', file);
  const params = new URLSearchParams({ policy });
  const response = await fetch(`${API_STRATEGY_PACKAGE_IMPORT}?${params.toString()}`, {
    method: 'POST',
    body: fd,
  });
  const json = await response.json();
  if (response.status === 409) {
    const err = new Error(json?.message?.detail || '导入冲突');
    err.code = 'package_conflict';
    err.preview = json?.message?.preview;
    throw err;
  }
  if (!response.ok || json?.status !== 'ok') {
    throw new Error(json?.message?.detail || `HTTP ${response.status}`);
  }
  return json.message;
}
