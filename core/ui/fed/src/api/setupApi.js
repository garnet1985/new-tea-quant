import request, { API_VERSION_PREFIX, HTTP_TIMEOUT_MS } from 'services/request';
import logClientError from '../utils/logClientError';

const API_BASE = `${API_VERSION_PREFIX}/setup`;
const STEP_STATUS_SUCCESS = 'success';

function normalizeDefinition(steps) {
  return (steps || []).map((step) => ({
    ...step,
    requiredUserInputs: step.requiredUserInputs || step.inputSchema || [],
  }));
}

function mapPipelineResult(json) {
  const payload = json?.message || {};
  const kind = payload.kind;
  const snapshot = payload.snapshot || null;
  if (kind === 'completed') {
    return { ok: true, status: snapshot };
  }
  if (kind === 'paused') {
    return {
      ok: false,
      kind: 'paused',
      pausedStepId: payload.pausedStepId,
      status: snapshot,
    };
  }
  return {
    ok: false,
    kind: 'failed',
    failedStepId: payload.failedStepId,
    message: payload.errorMessage || '安装失败，请检查配置后重试。',
    status: snapshot,
  };
}

function firstPendingStepId(snapshot) {
  const steps = snapshot?.stepStates || [];
  const pending = steps.find((step) => step?.status !== STEP_STATUS_SUCCESS);
  return pending?.stepId || '';
}

function failedStepId(snapshot) {
  const steps = snapshot?.stepStates || [];
  const failed = steps.find((step) => step?.status === 'failed');
  return failed?.stepId || '';
}

function runningStepId(snapshot) {
  const steps = snapshot?.stepStates || [];
  const running = steps.find((step) => step?.status === 'running');
  return running?.stepId || '';
}

async function executePipelineRequest(makeRequest, onProgress, preferredStepId = '') {
  let timerId = null;
  let stopped = false;
  let pollFailCount = 0;

  const emitRunning = async () => {
    if (!onProgress || stopped) return;
    try {
      const snapshot = await getSetupStatus();
      pollFailCount = 0;
      const stepId = runningStepId(snapshot) || preferredStepId || firstPendingStepId(snapshot);
      if (stepId) {
        onProgress({ stepId, status: 'running', snapshot });
      }
    } catch (error) {
      logClientError('setup.pipelinePoll', error);
      pollFailCount += 1;
      if (pollFailCount >= 3) {
        onProgress({
          pollWarning: '步骤进度暂时无法更新，安装可能仍在进行…',
        });
      }
    }
  };

  if (onProgress) {
    await emitRunning();
    timerId = setInterval(() => {
      emitRunning();
    }, 800);
  }

  try {
    const json = await makeRequest();
    const mapped = mapPipelineResult(json);
    if (onProgress && mapped?.status) {
      onProgress({ stepId: '', status: 'done', snapshot: mapped.status });
    }
    return mapped;
  } finally {
    stopped = true;
    if (timerId) clearInterval(timerId);
  }
}

export async function getSetupDefinition() {
  const json = await request.getJson(`${API_BASE}/definition`);
  return normalizeDefinition(json?.message?.steps || []);
}

export async function getSetupStatus() {
  const json = await request.getJson(`${API_BASE}/status`, {
    timeoutMs: HTTP_TIMEOUT_MS.POLL,
    silent: true,
  });
  return json.message || null;
}

export async function resetSetupStatus() {
  const json = await request.postJson(`${API_BASE}/reset`, { body: {} });
  return json.message || null;
}

export async function startSetupWorkflow(_onProgress) {
  const pre = await getSetupStatus();
  const preferredStepId = firstPendingStepId(pre);
  return executePipelineRequest(
    () => request.postJson(`${API_BASE}/start`, {
      body: {},
      timeoutMs: HTTP_TIMEOUT_MS.SETUP,
    }),
    _onProgress,
    preferredStepId,
  );
}

export async function submitInteractiveStep(stepId, inputValues, _onProgress) {
  const timeoutMs = stepId === 'resolve_ml_deps' ? HTTP_TIMEOUT_MS.SETUP_ML : HTTP_TIMEOUT_MS.SETUP;
  return executePipelineRequest(
    () => request.postJson(`${API_BASE}/steps/${encodeURIComponent(stepId)}/submit`, {
      body: { inputs: inputValues || {} },
      timeoutMs,
    }),
    _onProgress,
    stepId,
  );
}

export async function retryFailedStep(_onProgress) {
  const pre = await getSetupStatus();
  const preferredStepId = failedStepId(pre) || firstPendingStepId(pre);
  return executePipelineRequest(
    () => request.postJson(`${API_BASE}/retry`, {
      body: {},
      timeoutMs: HTTP_TIMEOUT_MS.SETUP,
    }),
    _onProgress,
    preferredStepId,
  );
}

export async function precheckDbConnection(inputs) {
  const json = await request.postJson(`${API_BASE}/steps/db_connection/precheck`, {
    body: { inputs: inputs || {} },
  });
  return {
    dbExists: Boolean(json?.message?.dbExists),
    dbType: json?.message?.dbType || '',
    database: json?.message?.database || '',
    isDuckdb: Boolean(json?.message?.isDuckdb),
  };
}

export async function precheckUserspacePath(inputs) {
  const json = await request.postJson(`${API_BASE}/steps/init_userspace/precheck-path`, {
    body: { inputs: inputs || {} },
  });
  return {
    userspacePath: json?.message?.userspacePath || '',
    pathExists: Boolean(json?.message?.pathExists),
  };
}

export async function getImportDataProgress() {
  const json = await request.getJson(`${API_BASE}/steps/import_data/progress`, {
    timeoutMs: HTTP_TIMEOUT_MS.POLL,
    silent: true,
  });
  return {
    running: Boolean(json?.message?.running),
    totalTables: Number(json?.message?.totalTables || 0),
    completedCount: Number(json?.message?.completedCount || 0),
    currentTable: json?.message?.currentTable || '',
    percent: Number(json?.message?.percent || 0),
    updatedAt: Number(json?.message?.updatedAt || 0),
  };
}

export async function getMlExtrasStatus() {
  const json = await request.getJson(`${API_BASE}/ml-extras`, {
    timeoutMs: HTTP_TIMEOUT_MS.POLL,
    silent: true,
  });
  return {
    installed: Boolean(json?.message?.installed),
    xgboost: Boolean(json?.message?.xgboost),
    shap: Boolean(json?.message?.shap),
  };
}

export async function installMlExtras() {
  const json = await request.postJson(`${API_BASE}/ml-extras`, {
    body: {},
    timeoutMs: HTTP_TIMEOUT_MS.SETUP_ML,
  });
  return {
    installed: Boolean(json?.message?.installed),
    xgboost: Boolean(json?.message?.xgboost),
    shap: Boolean(json?.message?.shap),
    installedNow: Boolean(json?.message?.installedNow),
  };
}
