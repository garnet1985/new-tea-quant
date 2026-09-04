export const STEP_STATUS = {
  NOT_STARTED: 'not_started',
  WAITING_INPUT: 'waiting_input',
  RUNNING: 'running',
  SUCCESS: 'success',
  FAILED: 'failed',
};

export const DEFAULT_STEP_ID = 'db_connection';

export const CHOICE_STEP_IDS = new Set(['import_data', 'resolve_ml_deps']);

export const SETUP_CHOICE_COPY = {
  import_data: {
    title: '数据库配置已经成功',
    body: '要不要导入演示数据？导入后可以直接在策略实验室里试用示例。不导入也可以稍后自行接入数据源。',
    confirmLabel: '导入演示数据',
    skipLabel: '跳过',
  },
  resolve_ml_deps: {
    title: '要安装机器学习依赖吗？',
    body: '归因分析里的 XGBoost / SHAP 解释需要额外依赖，安装可能需要几分钟。跳过后可随时在「设置 → 安装与维护」中补装。',
    confirmLabel: '安装（可能需要几分钟）',
    skipLabel: '跳过',
  },
};

export const FAKE_PROGRESS_CAP = 90;
export const FAKE_PROGRESS_STEP = 3;
export const FAKE_PROGRESS_WITHIN_STEP_RATIO = 0.9;
export const DEFAULT_STEP_PROGRESS_WEIGHT = 1;

export const EMPTY_IMPORT_PROGRESS = {
  running: false,
  totalTables: 0,
  completedCount: 0,
  currentTable: '',
  percent: 0,
};

export const DB_SERVER_FIELD_KEYS = new Set(['host', 'port', 'database', 'user', 'password']);

export function isChoicePauseStep(stepId) {
  return CHOICE_STEP_IDS.has(String(stepId || ''));
}

export function nextFakeProgress(current, cap = FAKE_PROGRESS_CAP, step = FAKE_PROGRESS_STEP) {
  const value = Number(current) || 0;
  if (value >= cap) return cap;
  return Math.min(cap, value + step);
}

export function setupStepProgressWeight(step) {
  const weight = Number(step?.progressWeight);
  return Number.isFinite(weight) && weight > 0 ? weight : DEFAULT_STEP_PROGRESS_WEIGHT;
}

export function setupWeightedPercent(definition, options = {}) {
  const steps = Array.isArray(definition) ? definition : [];
  if (steps.length === 0) return 0;
  const completedIds = new Set(options.completedIds || []);
  const runningStepId = String(options.runningStepId || '');
  const withinStepRatio = Math.max(0, Math.min(1, Number(options.withinStepRatio) || 0));
  const total = steps.reduce((sum, step) => sum + setupStepProgressWeight(step), 0) || 1;
  let acc = 0;
  steps.forEach((step) => {
    const weight = setupStepProgressWeight(step);
    if (completedIds.has(step.id)) {
      acc += weight;
      return;
    }
    if (step.id === runningStepId) {
      acc += weight * withinStepRatio;
    }
  });
  return (acc / total) * 100;
}

export function setupFakeProgressBounds(definition, options = {}) {
  const completedIds = options.completedIds || [];
  const runningStepId = options.runningStepId || '';
  const capRatio = options.capRatio ?? FAKE_PROGRESS_WITHIN_STEP_RATIO;
  const floorPercent = setupWeightedPercent(definition, { completedIds });
  const stepEndPercent = setupWeightedPercent(definition, {
    completedIds,
    runningStepId,
    withinStepRatio: 1,
  });
  const span = Math.max(0, stepEndPercent - floorPercent);
  return {
    floorPercent,
    capPercent: floorPercent + span * capRatio,
    stepEndPercent,
  };
}

export function clampFakeProgress(prev, options = {}) {
  const base = Number(options.basePercent) || 0;
  const cap = Number(options.cap);
  const top = Number.isFinite(cap) ? cap : FAKE_PROGRESS_CAP;
  if (!options.active) return base;
  const value = Number(prev) || 0;
  if (value < base) return base;
  // Ignore sub-percent cap jitter from polling; only clamp when clearly past the slice.
  if (value > top + 1) return Math.max(base, top);
  return value;
}

export function setupStatusSignature(status) {
  const steps = status?.stepStates || [];
  const parts = steps.map((item) => `${item.stepId}:${item.status}`);
  return `${status?.isReady ? '1' : '0'}|${parts.join(',')}`;
}

export function fakeProgressTickSize(basePercent, capPercent) {
  const span = Math.max(0, (Number(capPercent) || 0) - (Number(basePercent) || 0));
  if (span <= 0) return 0;
  return Math.max(0.3, span * 0.07);
}

export function shouldShowDbConnectionField(fieldKey, dbType) {
  if (fieldKey === 'defaultPgsqlSchema') return dbType === 'postgresql';
  if (DB_SERVER_FIELD_KEYS.has(fieldKey)) return dbType !== 'duckdb';
  return true;
}

export function applyDbTypeDefaults(formValues, key, value) {
  const next = { ...formValues, [key]: value };
  if (key === 'dbType') {
    if (value === 'duckdb') {
      next.host = '';
      next.port = '';
      next.database = '';
      next.user = '';
      next.password = '';
      next.defaultPgsqlSchema = '';
    } else if (value === 'postgresql') {
      next.host = next.host || 'localhost';
      next.port = '5432';
      next.user = next.user || 'postgres';
      next.defaultPgsqlSchema = next.defaultPgsqlSchema || 'public';
    } else if (value === 'mysql') {
      next.host = next.host || 'localhost';
      next.port = '3306';
      next.user = next.user || 'root';
      next.defaultPgsqlSchema = '';
    }
  }
  return next;
}

export function getFieldDisplayValue(formValues, field) {
  const current = formValues[field.key];
  if ((current === undefined || current === null || current === '') && field.defaultValue !== undefined) {
    return field.defaultValue;
  }
  return current ?? '';
}

export function getFieldInputId(pausedStep, field) {
  return `setup-${pausedStep || 'step'}-${field.key}`;
}

export function shouldShowUserspaceConflictPolicy(field, userspacePathEditable, userspacePathExists) {
  if (field.key !== 'userspaceConflictPolicy') return true;
  if (userspacePathEditable) {
    return Boolean(userspacePathExists);
  }
  return Boolean(field.showByDefault);
}

export function validateDbConnectionSubmit(submitValues) {
  const dbType = String(submitValues.dbType || 'duckdb').trim().toLowerCase();
  if (dbType === 'duckdb') {
    return '';
  }
  const missing = ['host', 'database', 'user'].filter((key) => !String(submitValues[key] || '').trim());
  if (missing.length > 0) {
    return `请填写 ${missing.join('、')} 后再继续。`;
  }
  return '';
}
