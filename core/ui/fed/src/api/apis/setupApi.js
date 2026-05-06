import { requestJson } from '../global/httpClient';
import { API_VERSION_PREFIX } from '../conf/apiConfig';

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

  const emitRunning = async () => {
    if (!onProgress || stopped) return;
    try {
      const snapshot = await getSetupStatus();
      const stepId = runningStepId(snapshot) || preferredStepId || firstPendingStepId(snapshot);
      if (stepId) {
        onProgress({ stepId, status: 'running', snapshot });
      }
    } catch (_error) {
      // ignore poll error
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
  const json = await requestJson(`${API_BASE}/definition`, { method: 'GET' });
  return normalizeDefinition(json?.message?.steps || []);
}

export async function getSetupStatus() {
  const json = await requestJson(`${API_BASE}/status`, { method: 'GET' });
  return json.message || null;
}

export async function resetSetupStatus() {
  const json = await requestJson(`${API_BASE}/reset`, { method: 'POST', body: '{}' });
  return json.message || null;
}

export async function startSetupWorkflow(_onProgress) {
  const pre = await getSetupStatus();
  const preferredStepId = firstPendingStepId(pre);
  return executePipelineRequest(
    () => requestJson(`${API_BASE}/start`, { method: 'POST', body: '{}' }),
    _onProgress,
    preferredStepId,
  );
}

export async function submitInteractiveStep(stepId, inputValues, _onProgress) {
  return executePipelineRequest(
    () => requestJson(`${API_BASE}/steps/${encodeURIComponent(stepId)}/submit`, {
      method: 'POST',
      body: JSON.stringify({ inputs: inputValues || {} }),
    }),
    _onProgress,
    stepId,
  );
}

export async function retryFailedStep(_onProgress) {
  const pre = await getSetupStatus();
  const preferredStepId = failedStepId(pre) || firstPendingStepId(pre);
  return executePipelineRequest(
    () => requestJson(`${API_BASE}/retry`, { method: 'POST', body: '{}' }),
    _onProgress,
    preferredStepId,
  );
}

export async function precheckDbConnection(inputs) {
  const json = await requestJson(`${API_BASE}/steps/db_connection/precheck`, {
    method: 'POST',
    body: JSON.stringify({ inputs: inputs || {} }),
  });
  return {
    dbExists: Boolean(json?.message?.dbExists),
    dbType: json?.message?.dbType || '',
    database: json?.message?.database || '',
  };
}

export async function precheckUserspacePath(inputs) {
  const json = await requestJson(`${API_BASE}/steps/init_userspace/precheck-path`, {
    method: 'POST',
    body: JSON.stringify({ inputs: inputs || {} }),
  });
  return {
    userspacePath: json?.message?.userspacePath || '',
    pathExists: Boolean(json?.message?.pathExists),
  };
}

export async function getImportDataProgress() {
  const json = await requestJson(`${API_BASE}/steps/import_data/progress`, { method: 'GET' });
  return {
    running: Boolean(json?.message?.running),
    totalTables: Number(json?.message?.totalTables || 0),
    completedCount: Number(json?.message?.completedCount || 0),
    currentTable: json?.message?.currentTable || '',
    percent: Number(json?.message?.percent || 0),
    updatedAt: Number(json?.message?.updatedAt || 0),
  };
}
