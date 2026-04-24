const WAIT_MS = 500;
const MIN_STEP_DURATION_MS = 2000;

function wait(ms = WAIT_MS) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

const STORAGE_KEY = 'ntq.setup.mock.status';

export const STEP_STATUS = {
  NOT_STARTED: 'not_started',
  WAITING_INPUT: 'waiting_input',
  RUNNING: 'running',
  SUCCESS: 'success',
  FAILED: 'failed',
};

export const SETUP_DEFINITION = [
  {
    id: 'resolve_deps',
    name: '依赖安装',
    description: '对应 setup/steps/resolve_deps 步骤。',
    requiredUserInputs: [],
  },
  {
    id: 'init_userspace',
    name: 'Init Userspace',
    description: '对应 setup/steps/init_userspace 步骤。',
    requiredUserInputs: [
      {
        key: 'userspaceTargetPath',
        label: 'Userspace Target Path',
        type: 'text',
        required: false,
        defaultValue: '',
      },
    ],
  },
  {
    id: 'db_connection',
    name: 'DB 配置检查/填写',
    description: '对应 setup/steps/db_connection 的前置配置检查。',
    requiredUserInputs: [
      {
        key: 'dbType',
        label: 'Database Type',
        type: 'select',
        required: true,
        options: [
          { label: 'postgresql', value: 'postgresql' },
          { label: 'mysql', value: 'mysql' },
        ],
        defaultValue: 'postgresql',
      },
      { key: 'host', label: 'Host', type: 'text', required: true },
      { key: 'port', label: 'Port', type: 'text', required: true },
      { key: 'database', label: 'Database Name', type: 'text', required: true },
      { key: 'user', label: 'User', type: 'text', required: true },
      { key: 'password', label: 'Password', type: 'password', required: true },
      { key: 'defaultPgsqlSchema', label: 'Schema', type: 'text', required: false },
    ],
  },
  {
    id: 'import_data',
    name: 'Init Data Import',
    description: '对应 setup/steps/import_data 步骤。',
    requiredUserInputs: [],
  },
];

const DB_DEFAULTS = {
  postgresql: {
    dbType: 'postgresql',
    host: 'localhost',
    port: '5432',
    database: 'new_tea_quant',
    user: 'postgres',
    password: '',
    defaultPgsqlSchema: 'public',
  },
  mysql: {
    dbType: 'mysql',
    host: 'localhost',
    port: '3306',
    database: 'new_tea_quant',
    user: 'root',
    password: '',
    defaultPgsqlSchema: '',
  },
};

function getDbDefaults(dbType) {
  return DB_DEFAULTS[dbType] || DB_DEFAULTS.postgresql;
}

function applyDbDefaults(values) {
  const base = getDbDefaults(values?.dbType || 'postgresql');
  return {
    ...base,
    ...(values || {}),
  };
}

function createDefaultStepStates() {
  return SETUP_DEFINITION.map((step) => ({
    stepId: step.id,
    status: STEP_STATUS.NOT_STARTED,
    errorMessage: '',
  }));
}

const defaultStatus = {
  isReady: false,
  stepStates: createDefaultStepStates(),
  inputsByStep: {
    init_userspace: {
      userspaceTargetPath: '',
    },
    db_connection: applyDbDefaults({}),
  },
  debug: {
    pgsqlDepsFailedOnce: false,
  },
};

function normalizeStepStates(inputStates) {
  const byId = new Map((inputStates || []).map((item) => [item.stepId, item]));
  return SETUP_DEFINITION.map((step) => ({
    stepId: step.id,
    status: byId.get(step.id)?.status || STEP_STATUS.NOT_STARTED,
    errorMessage: byId.get(step.id)?.errorMessage || '',
  }));
}

function deriveStatus(base) {
  const isReady = base.stepStates.every((step) => step.status === STEP_STATUS.SUCCESS);
  return { ...base, isReady };
}

function patchStatus(current, patch) {
  const next = {
    ...current,
    ...(patch || {}),
    stepStates: normalizeStepStates(patch?.stepStates || current.stepStates),
    inputsByStep: {
      ...(current.inputsByStep || {}),
      ...(patch?.inputsByStep || {}),
    },
  };
  if (next.inputsByStep.db_connection) {
    next.inputsByStep.db_connection = applyDbDefaults(next.inputsByStep.db_connection);
  }
  return deriveStatus(next);
}

function readStatus() {
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) return defaultStatus;
  try {
    return patchStatus(defaultStatus, JSON.parse(raw));
  } catch (_error) {
    return defaultStatus;
  }
}

function writeStatus(status) {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(status));
}

function updateStepState(stepId, updater) {
  const current = readStatus();
  const next = patchStatus(current, {
    stepStates: current.stepStates.map((step) => (
      step.stepId === stepId ? updater(step) : step
    )),
  });
  writeStatus(next);
  return next;
}

function findStepById(stepId) {
  return SETUP_DEFINITION.find((step) => step.id === stepId);
}

function findFailedStep(status) {
  return (status.stepStates || []).find((step) => step.status === STEP_STATUS.FAILED);
}

function firstPendingStep(status) {
  const done = new Set(
    (status.stepStates || [])
      .filter((step) => step.status === STEP_STATUS.SUCCESS)
      .map((step) => step.stepId),
  );
  return SETUP_DEFINITION.find((step) => !done.has(step.id));
}

function validateStepInput(step, values) {
  const missing = [];
  step.requiredUserInputs.forEach((field) => {
    if (!field.required) return;
    if (field.key === 'password' && values?.dbType === 'mysql') return;
    if (!String(values?.[field.key] || '').trim()) {
      missing.push(field.label || field.key);
    }
  });
  if (missing.length > 0) {
    return `输入不完整，缺少字段: ${missing.join(', ')}`;
  }
  return '';
}

async function ensureMinDuration(startMs) {
  const elapsed = Date.now() - startMs;
  if (elapsed < MIN_STEP_DURATION_MS) {
    await wait(MIN_STEP_DURATION_MS - elapsed);
  }
}

async function executeAutoStep(step, onProgress) {
  const start = Date.now();
  let running = updateStepState(step.id, (prev) => ({ ...prev, status: STEP_STATUS.RUNNING, errorMessage: '' }));
  if (onProgress) onProgress({ stepId: step.id, status: 'running', snapshot: running });

  await wait(700);
  const current = readStatus();
  const isPgsqlDepsFirstFailure = (
    step.id === 'resolve_deps' &&
    current.inputsByStep.db_connection?.dbType === 'postgresql' &&
    !current.debug?.pgsqlDepsFailedOnce
  );

  await ensureMinDuration(start);

  if (isPgsqlDepsFirstFailure) {
    const failed = patchStatus(current, {
      debug: { ...(current.debug || {}), pgsqlDepsFailedOnce: true },
      stepStates: current.stepStates.map((state) => (
        state.stepId === step.id
          ? { ...state, status: STEP_STATUS.FAILED, errorMessage: '依赖安装失败（模拟网络问题）' }
          : state
      )),
    });
    writeStatus(failed);
    if (onProgress) onProgress({ stepId: step.id, status: 'failed', snapshot: failed });
    return {
      ok: false,
      kind: 'failed',
      failedStepId: step.id,
      message: '依赖安装失败（模拟网络问题）',
      status: failed,
    };
  }

  running = updateStepState(step.id, (prev) => ({ ...prev, status: STEP_STATUS.SUCCESS, errorMessage: '' }));
  if (onProgress) onProgress({ stepId: step.id, status: 'done', snapshot: running });
  return { ok: true, status: running };
}

function pauseAtInteractionStep(step) {
  const paused = updateStepState(step.id, (prev) => ({ ...prev, status: STEP_STATUS.WAITING_INPUT, errorMessage: '' }));
  return {
    ok: false,
    kind: 'paused',
    pausedStepId: step.id,
    status: paused,
  };
}

async function runPipeline(onProgress) {
  let current = readStatus();
  let nextStep = firstPendingStep(current);

  while (nextStep) {
    const currentStepId = nextStep.id;
    if (nextStep.requiredUserInputs.length > 0) {
      const stepState = current.stepStates.find((item) => item.stepId === currentStepId);
      if (stepState?.status !== STEP_STATUS.RUNNING) {
        return pauseAtInteractionStep(nextStep);
      }
    }

    const result = await executeAutoStep(nextStep, onProgress);
    if (!result.ok) return result;
    current = result.status;
    nextStep = firstPendingStep(current);
  }

  return { ok: true, status: current };
}

function resetFromStep(status, stepId) {
  const index = SETUP_DEFINITION.findIndex((step) => step.id === stepId);
  if (index < 0) return status;
  const keep = new Set(SETUP_DEFINITION.slice(0, index).map((step) => step.id));
  return patchStatus(status, {
    stepStates: status.stepStates.map((state) => {
      if (keep.has(state.stepId)) return state;
      return { ...state, status: STEP_STATUS.NOT_STARTED, errorMessage: '' };
    }),
  });
}

export async function getSetupDefinition() {
  await wait();
  try {
    const resp = await fetch('/api/v1/setup/definition');
    if (!resp.ok) throw new Error(`http_${resp.status}`);
    const json = await resp.json();
    if (json?.status === 'ok' && Array.isArray(json?.message?.steps)) {
      return json.message.steps.map((step) => ({
        ...step,
        requiredUserInputs: step.requiredUserInputs || step.inputSchema || [],
      }));
    }
  } catch (_error) {
    // Fallback to local mock when BFF is unavailable.
  }
  return SETUP_DEFINITION;
}

export async function getSetupStatus() {
  await wait();
  return readStatus();
}

export async function resetSetupStatus() {
  await wait(100);
  writeStatus(defaultStatus);
  return defaultStatus;
}

export async function startSetupWorkflow(onProgress) {
  const current = readStatus();
  const reset = patchStatus(current, { stepStates: createDefaultStepStates() });
  writeStatus(reset);
  return runPipeline(onProgress);
}

export async function submitInteractiveStep(stepId, inputValues, onProgress) {
  const step = findStepById(stepId);
  if (!step) {
    return { ok: false, kind: 'failed', failedStepId: stepId, message: '未知步骤', status: readStatus() };
  }
  const normalizedInput = stepId === 'db_connection' ? applyDbDefaults(inputValues || {}) : (inputValues || {});
  const error = validateStepInput(step, normalizedInput);
  if (error) {
    const failed = patchStatus(readStatus(), {
      inputsByStep: { [stepId]: normalizedInput },
      stepStates: readStatus().stepStates.map((state) => (
        state.stepId === stepId ? { ...state, status: STEP_STATUS.FAILED, errorMessage: error } : state
      )),
    });
    writeStatus(failed);
    return { ok: false, kind: 'failed', failedStepId: stepId, message: error, status: failed };
  }

  let current = patchStatus(readStatus(), {
    inputsByStep: { [stepId]: normalizedInput },
    stepStates: readStatus().stepStates.map((state) => (
      state.stepId === stepId ? { ...state, status: STEP_STATUS.SUCCESS, errorMessage: '' } : state
    )),
  });
  writeStatus(current);
  return runPipeline(onProgress);
}

export async function retryFailedStep(onProgress) {
  const current = readStatus();
  const failed = findFailedStep(current);
  if (!failed) return runPipeline(onProgress);

  const step = findStepById(failed.stepId);
  const reset = resetFromStep(current, failed.stepId);
  writeStatus(reset);

  if (step?.requiredUserInputs?.length > 0) {
    const paused = updateStepState(step.id, (prev) => ({ ...prev, status: STEP_STATUS.WAITING_INPUT, errorMessage: '' }));
    return {
      ok: false,
      kind: 'paused',
      pausedStepId: step.id,
      status: paused,
    };
  }

  return runPipeline(onProgress);
}
