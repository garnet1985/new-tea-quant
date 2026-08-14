import { requestJson } from '../global/httpClient';
import { coerceMetaDescription } from '../../utils/formatStrategyDescription';
import { API_VERSION_PREFIX } from '../conf/apiConfig';
import { mapDataEnd } from '../shared/dataEnd';

/** 分页策略目录（V2-02）：`/api/v1/strategy/catalog/:page/:limit` */
const API_STRATEGY_CATALOG = (page, limit) =>
  `${API_VERSION_PREFIX}/strategy/catalog/${encodeURIComponent(page)}/${encodeURIComponent(limit)}`;
const API_STRATEGY_SCAN_CONTEXT = `${API_VERSION_PREFIX}/strategy/scan/context`;
/** 策略列表/扫描页展示名：优先 ``display_name``，否则回退路径 ID。 */
export function getStrategyDisplayLabel(item) {
  return String(item?.display_name || item?.name || '').trim();
}

/** 无 ``meta.category`` 时的 UI 归类名。 */
export const UNKNOWN_STRATEGY_CATEGORY = '未知归类';

/** 策略归类展示名：有 category 用原文，否则「未知归类」。 */
export function getStrategyCategoryLabel(item) {
  const category = String(item?.category || '').trim();
  return category || UNKNOWN_STRATEGY_CATEGORY;
}

/**
 * 按 category 分组；命名类按中文序，``未知归类`` 始终在最后。
 * @param {object[]} rows
 * @returns {{ category: string, rows: object[] }[]}
 */
export function groupStrategiesByCategory(rows) {
  const map = new Map();
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    const category = getStrategyCategoryLabel(row);
    if (!map.has(category)) map.set(category, []);
    map.get(category).push(row);
  });
  const named = [...map.keys()]
    .filter((name) => name !== UNKNOWN_STRATEGY_CATEGORY)
    .sort((a, b) => a.localeCompare(b, 'zh-CN'));
  const order = [...named];
  if (map.has(UNKNOWN_STRATEGY_CATEGORY)) {
    order.push(UNKNOWN_STRATEGY_CATEGORY);
  }
  return order.map((category) => ({
    category,
    rows: map.get(category) || [],
  }));
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
const API_SETTINGS_PORTFOLIO = `${API_VERSION_PREFIX}/strategy/settings/portfolio`;
const API_SETTINGS_SAMPLING = `${API_VERSION_PREFIX}/strategy/settings/sampling`;
const API_SETTINGS_SIMULATION = `${API_VERSION_PREFIX}/strategy/settings/simulation`;
const API_SETTINGS_RISK_CONTROL = `${API_VERSION_PREFIX}/strategy/settings/risk-control`;
const API_SETTINGS_MARKET_RULES = `${API_VERSION_PREFIX}/strategy/settings/market-rules`;

/** @typedef {{ value: string, label: string }} StrategySettingOption */
/** @typedef {{ configurable_fields: string[], required_fields: string[] }} StrategySettingProfile */

/**
 * 获取已发现策略列表（策略工作台 list 页使用）
 * V2 BFF：`GET /api/v1/strategy/catalog/:page/:limit` → `{ status, message: { items, total, page, limit } }`
 * @returns {Promise<{ data: object[] }>}
 */
export async function fetchStrategyList() {
  const json = await requestJson(API_STRATEGY_CATALOG(1, 100), { method: 'GET' });
  const list = json?.message?.items || [];
  return {
    data: list.map((item) => {
      const pathName = String(item.name || '').trim();
      const key = String(item.key || '').trim();
      // API / 路由身份：优先 meta.key；无 key 时回落 path（兼容旧策略）
      const identity = key || pathName;
      return {
        id: identity,
        name: identity,
        path: pathName,
        key,
        // 保留服务端原值；展示时用 getStrategyDisplayLabel，勿把路径写进 display_name
        display_name: String(item.display_name || '').trim(),
        category: String(item.category || '').trim(),
        description: coerceMetaDescription(item.description),
        keywords: Array.isArray(item.keywords) ? item.keywords : [],
        details: item.details && typeof item.details === 'object' ? item.details : null,
        is_enabled: Boolean(item.is_enabled),
      };
    }),
  };
}

/**
 * 扫描页上下文：data.json 截至日 + 演示模式截止日（与后端 ScanDateResolver 一致）。
 */
export async function fetchStrategyScanContext() {
  const json = await requestJson(API_STRATEGY_SCAN_CONTEXT, { method: 'GET' });
  const m = json?.message || {};
  const dataEnd = m.data_end && typeof m.data_end === 'object' ? m.data_end : {};
  const cutoff = String(m.demo_scan_cutoff_date || '').trim();
  return {
    dataEnd: mapDataEnd(dataEnd),
    demoScanCutoffDate: cutoff,
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
  const blockReason = String(m.block_reason || m.blockReason || '').trim();
  // 缺省 can_scan 视为不可扫，避免「未定义 = 允许」的障眼法
  const canScanRaw = m.can_scan ?? m.canScan;
  const canScan = typeof canScanRaw === 'boolean' ? canScanRaw : false;
  return {
    primary_action: m.primary_action === 'rerun' ? 'rerun' : 'run',
    report,
    can_scan: canScan,
    block_reason: blockReason || (canScanRaw === undefined ? '扫描就绪状态未知' : ''),
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

/** 构建制定策略页路径（可选 step：enum | price | portfolio） */
export function getStrategyDesignPath(strategyName, step = '') {
  const encoded = encodeStrategyPathSegments(strategyName);
  const base = `/strategy-design/${encoded}`;
  const seg = String(step || '').trim();
  if (seg === 'enum' || seg === 'price' || seg === 'portfolio') {
    return `${base}/${seg}`;
  }
  return base;
}

/**
 * V2-01：读取 latest 工作台快照（settings + version_id + step_status + result_report）。
 * @param {string} strategyKeyOrName ``meta.key``（推荐）或 path name
 * @returns {Promise<{ strategy_name: string, settings: object, workbench_version_id?: string, has_persisted_snapshot?: boolean, has_other_versions?: boolean }>}
 */
export async function fetchStrategySettings(strategyKeyOrName) {
  const json = await requestJson(
    `${apiStrategyPath(strategyKeyOrName)}/version/latest`,
    { method: 'GET' },
  );
  const m = json?.message || {};
  return {
    strategy_name: strategyKeyOrName,
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
 * @param {string} strategyKeyOrName ``meta.key``（推荐）或 path name
 * @param {object} _settings 保留参数；V2 以服务端快照为准，此参数不参与请求体
 * @param {{ version_id?: string }} [opts]
 */
export async function applyStrategySettingsToUserspace(strategyKeyOrName, _settings, opts = {}) {
  let versionId = typeof opts.version_id === 'string' ? opts.version_id.trim() : '';
  if (!versionId) {
    const latest = await fetchStrategySettings(strategyKeyOrName);
    versionId = (latest.workbench_version_id || '').trim();
  }
  if (!versionId) {
    throw new Error('缺少工作台 version_id，无法发布（请先加载有效快照）');
  }
  const json = await requestJson(
    `${apiStrategyPath(strategyKeyOrName)}/settings/apply/${encodeURIComponent(versionId)}`,
    {
      method: 'POST',
      body: JSON.stringify({}),
    },
  );
  return {
    strategy_name: json?.message?.strategy_name || strategyKeyOrName,
    applied: Boolean(json?.message?.applied),
  };
}

/**
 * V2-03：读取策略工作台版本列表（至多 10 条）。
 * @param {string} strategyKeyOrName ``meta.key``（推荐）或 path name
 * @returns {Promise<{ versions: Array<{ version_id: string, version: number, created_at: string, updated_at: string }> }>}
 */
export async function fetchStrategyVersions(strategyKeyOrName) {
  const json = await requestJson(
    `${apiStrategyPath(strategyKeyOrName)}/versions`,
    { method: 'GET' },
  );
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
 * V2-08：读取单个版本详情（与 V2-01 同形，无冷启动）。
 * @param {string} strategyKeyOrName ``meta.key``（推荐）或 path name
 * @param {string} versionId
 * @returns {Promise<{ version_id: string, settings: object }>}
 */
export async function fetchStrategyVersionDetail(strategyKeyOrName, versionId) {
  const json = await requestJson(
    `${apiStrategyPath(strategyKeyOrName)}/version/${encodeURIComponent(versionId)}`,
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
 * 恢复历史版本到工作台：无单独写库 restore；以 **V2-08** 快照正文为准。
 * 与 ``GET …/{strategy}/version/latest`` 正文同形（冷启动仅 latest 有合成行）。
 * @param {string} strategyKeyOrName
 * @param {string} versionId
 * @returns {Promise<{ restored: boolean, version_id: string, detail: object }>}
 */
export async function restoreStrategyVersion(strategyKeyOrName, versionId) {
  const detail = await fetchStrategyVersionDetail(strategyKeyOrName, versionId);
  return {
    restored: true,
    version_id: versionId,
    detail,
  };
}

/**
 * V2-05：启动 run（路径上的 ``step`` 为用户点击步；实际子步骤链见响应 ``steps`` / ``resolved_chain``，由后端 ``plan_schema`` 规划）。
 * @param {string} strategyName
 * @param {'enum'|'price'|'portfolio'} targetStep
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
 * V2-07b：枚举逐股 ref（``entity_list.json``）。成功时 ``message.stock_ref`` 可为 ``null``（磁盘已清理），
 * 此时 ``stock_ref_available === false``；仅快照不存在时 HTTP 非 2xx。
 * GET /api/v1/strategy/:strategy_key_or_name/report/:step/:version_id/ref
 * @param {string} strategyKeyOrName
 * @param {'enum'|'price'|'portfolio'} step
 * @param {string} versionId
 * @returns {Promise<object|null>}
 */
/**
 * V2-07c：单股 K 线 + 步骤 markers。
 * GET /api/v1/strategy/:strategy_key_or_name/report/:step/:version_id/stock/:stock_id
 */
export async function fetchStrategyStockDetail(strategyKeyOrName, step, versionId, stockId) {
  const base = apiStrategyPath(strategyKeyOrName);
  const vid = encodeURIComponent(String(versionId || '').trim());
  const code = encodeURIComponent(String(stockId || '').trim());
  if (!base || !vid || !code) {
    throw new Error('缺少 strategy_key_or_name、version_id 或 stock_id');
  }
  const url = `${base}/report/${encodeURIComponent(step)}/${vid}/stock/${code}`;
  const json = await requestJson(url, { method: 'GET' });
  return json?.message || {};
}

export async function fetchStrategyStepReportRef(strategyKeyOrName, step, versionId) {
  const base = apiStrategyPath(strategyKeyOrName);
  const vid = encodeURIComponent(String(versionId || '').trim());
  if (!base || !vid) {
    throw new Error('缺少 strategy_key_or_name 或 version_id');
  }
  const url = `${base}/report/${encodeURIComponent(step)}/${vid}/ref`;
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
  });
  let json = {};
  try {
    json = await response.json();
  } catch {
    throw new Error('报告 ref 响应不是合法 JSON');
  }
  if (!response.ok || json?.status !== 'ok') {
    const detail = String(json?.message || json?.error || '').trim();
    throw new Error(detail || `读取报告 ref 失败（HTTP ${response.status}）`);
  }
  return json?.message || {};
}

/**
 * V2-06b：整次 run 进度（``strategy_pipeline_v1``）。
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
 * 将 ``GET …/run/progress``（``strategy_pipeline_v1``）映射为执行面板字段。
 * @param {object|null} envelope
 */
export function mapWorkbenchRunProgressToPanel(envelope) {
  if (!envelope || typeof envelope !== 'object') {
    return {
      run_id: '',
      step_status_merge: {},
      step_progress: {},
      running_step: '',
      progress_pct: 0,
      progress_label: '',
      progress_stage_label: '',
      progress_counter_text: '',
      state: 'failed',
      version_id: '',
      fail_reason: '无编排进度数据',
    };
  }

  const pipeline = String(envelope.pipeline_name || '').trim();
  const status = String(envelope.status || envelope.phase || '').trim().toLowerCase();
  const pctRaw = Number(envelope.progress);
  const pct = Number.isFinite(pctRaw) ? Math.min(100, Math.max(0, pctRaw)) : 0;

  let panelStatus = 'idle';
  if (status === 'queued' || status === 'pending') panelStatus = 'pending';
  else if (status === 'running') panelStatus = 'running';
  else if (status === 'completed') panelStatus = 'done';
  else if (status === 'failed' || status === 'cancelled') panelStatus = 'failed';

  const step_status_merge = {};
  const step_progress = {};
  if (pipeline === 'enum' || pipeline === 'price' || pipeline === 'portfolio') {
    step_status_merge[pipeline] = panelStatus;
    step_progress[pipeline] = pct;
  }

  let state = 'running';
  if (panelStatus === 'failed') state = 'failed';
  else if (panelStatus === 'done') state = 'done';

  const curStep = envelope.step && typeof envelope.step === 'object' ? envelope.step : null;
  const progress_label = String(envelope.pipeline_description || '').trim()
    || ({
      enum: '枚举',
      price: '价格回测',
      portfolio: '投资模拟',
    }[pipeline] || '');
  const progress_stage_label = curStep
    ? String(curStep.description || curStep.name || '').trim()
    : '';

  let progress_counter_text = '';
  const counters = curStep?.counters;
  if (counters && typeof counters === 'object') {
    const done = counters.done;
    const total = counters.total;
    if (done != null && total != null && String(total) !== '') {
      progress_counter_text = `${done}/${total}`;
    }
  }

  const result = envelope.result && typeof envelope.result === 'object' ? envelope.result : {};
  const version_id = typeof result.version_id === 'string' ? result.version_id.trim() : '';
  let fail_reason = '';
  if (state === 'failed') {
    fail_reason = String(envelope.error || result.message || '').trim();
  }

  return {
    run_id: String(envelope.run_id || envelope.pipeline_id || envelope.job_id || '').trim(),
    step_status_merge,
    step_progress,
    running_step: (panelStatus === 'running' || panelStatus === 'pending') ? pipeline : '',
    progress_pct: state === 'done' ? 100 : pct,
    progress_label,
    progress_stage_label,
    progress_counter_text,
    state,
    version_id,
    fail_reason,
  };
}

/**
 * 轮询 run 进度（``strategy_pipeline_v1``）。
 * @param {string} strategyName
 * @param {string} jobId
 */
export async function fetchStrategyRunStatus(strategyName, jobId) {
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
 * 资金分配模式选项 + 联动字段 profile（`portfolio.allocation.mode`）。
 * @returns {Promise<{ options: StrategySettingOption[], profiles: Record<string, StrategySettingProfile> }>}
 */
export async function fetchCapitalAllocationModeConfig() {
  const json = await requestJson(API_SETTINGS_PORTFOLIO, { method: 'GET' });
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
 * 采样策略选项 + 联动字段 profile（`sampling.strategy`）。
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
 * 回测模板选项 + defaults（嵌套 ``{ tradability: {...} }``，供 assumption 合并）。
 * @returns {Promise<{ options: StrategySettingOption[], profiles: Record<string, object> }>}
 */
export async function fetchSimulationTemplateConfig() {
  const json = await requestJson(API_SETTINGS_SIMULATION, { method: 'GET' });
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
 * ``simulation.risk_control.skip_enter_when`` 可勾选标签（``st`` / ``star_st``）。
 * GET /api/v1/strategy/settings/risk-control
 * @returns {Promise<StrategySettingOption[]>}
 */
export async function fetchSkipInvestmentWhenOptions() {
  const json = await requestJson(API_SETTINGS_RISK_CONTROL, { method: 'GET' });
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
  const json = await requestJson(API_SETTINGS_MARKET_RULES, { method: 'GET' });
  const items = json?.message?.items ?? [];
  return items.map((row) => ({ value: row.value, label: row.label }));
}

const API_STRATEGY_PACKAGE_IMPORT = `${API_VERSION_PREFIX}/strategy/package/import`;
const API_STRATEGY_PACKAGE_IMPORT_PREVIEW = `${API_VERSION_PREFIX}/strategy/package/import/preview`;
const API_STRATEGY_PACKAGE_EXPORT = (strategyKeyOrName) =>
  `${apiStrategyPath(strategyKeyOrName)}/package/export`;

async function readFetchErrorDetail(response) {
  try {
    const json = await response.json();
    return json?.message?.detail || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

/**
 * 下载策略交流包（V2-13）：`GET /api/v1/strategy/:strategy_key_or_name/package/export`
 * @param {string} strategyKeyOrName ``settings.meta.key`` 或 path name
 * @param {{ scope?: 'bundle'|'strategy' }} [options]
 */
export async function downloadStrategyPackage(strategyKeyOrName, { scope = 'bundle' } = {}) {
  const params = new URLSearchParams({ scope });
  const url = `${API_STRATEGY_PACKAGE_EXPORT(strategyKeyOrName)}?${params.toString()}`;
  const response = await fetch(url, { method: 'GET' });
  if (!response.ok) {
    throw new Error(await readFetchErrorDetail(response));
  }
  const blob = await response.blob();
  let filename = `${strategyKeyOrName}-strategy.zip`;
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
