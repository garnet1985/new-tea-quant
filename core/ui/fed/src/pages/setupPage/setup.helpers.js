import {
  FAKE_PROGRESS_CAP,
  FAKE_PROGRESS_STEP,
  clampFakeProgress,
  nextFakeProgress,
} from 'service/progress/fakeProgress';
import { progressRatio } from 'service/progress/ratio';

export {
  FAKE_PROGRESS_CAP,
  FAKE_PROGRESS_STEP,
  clampFakeProgress,
  nextFakeProgress,
};

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
    title: '选择演示数据',
    layout: 'cards',
    introBeforeLink: '在官网',
    introLinkLabel: '注册会员',
    introAfterLink:
      '后可使用更多演示数据。若您只是想快速安装并体验一下，推荐选择「导入演示数据」；若您需要更多数据（全市场三年数据），请在此跳过，稍候注册会员后到「设置 → 安装与维护」再导入。',
    choices: [
      {
        id: 'demo',
        skip: false,
        title: '导入演示数据',
        description: '适用于非会员：约 300 只股票 × 三年数据，安装完成即可体验软件所有功能。',
      },
      {
        id: 'later',
        skip: true,
        title: '稍后再导入',
        description: '注册会员后可导入：全 A 股 5800+ 只股票 × 三年数据（2021年 - 2023年）。',
      },
    ],
  },
  resolve_ml_deps: {
    title: '您想现在安装机器学习的插件吗？',
    layout: 'buttons',
    body: '安装机器学习的插件可能需要几分钟。如果跳过，您仍然可以随时在「设置 → 安装与维护」中手动安装。',
    confirmLabel: '安装（可能需要几分钟）',
    skipLabel: '跳过',
  },
};

export const FAKE_PROGRESS_WITHIN_STEP_RATIO = 0.9;
/** 下载只占 import_data 步骤权重的前一段，避免下载 100% 顶满整步后再因切到导表回落。 */
export const IMPORT_DOWNLOAD_WITHIN_SHARE = 0.25;
export const DEFAULT_STEP_PROGRESS_WEIGHT = 1;

export const EMPTY_IMPORT_PROGRESS = {
  running: false,
  phase: '',
  statusText: '',
  totalTables: 0,
  completedCount: 0,
  currentTable: '',
  ratio: 0,
  downloadedBytes: 0,
  totalBytes: 0,
};

export const DB_SERVER_FIELD_KEYS = new Set(['host', 'port', 'database', 'user', 'password']);

export function isChoicePauseStep(stepId) {
  return CHOICE_STEP_IDS.has(String(stepId || ''));
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

/**
 * 把导入子阶段映射到 import_data 步骤内的 0..1。
 * 下载最多占前 {@link IMPORT_DOWNLOAD_WITHIN_SHARE}；导表占剩余。
 * preparing 返回 0，由 UI 侧高水位衔接，避免下载结束回落。
 */
export function importWithinStepRatio(importProgress) {
  if (!importProgress?.running) return 0;
  const phase = String(importProgress.phase || '');
  const downloadShare = IMPORT_DOWNLOAD_WITHIN_SHARE;
  if (phase === 'downloading') {
    if (!(Number(importProgress.totalBytes) > 0)) return 0;
    return downloadShare * progressRatio(importProgress.ratio);
  }
  if (phase === 'importing' && Number(importProgress.totalTables) > 0) {
    const tableRatio = progressRatio(importProgress.ratio);
    return downloadShare + (1 - downloadShare) * tableRatio;
  }
  return 0;
}

export function setupStatusSignature(status) {
  const steps = status?.stepStates || [];
  const parts = steps.map((item) => `${item.stepId}:${item.status}`);
  return `${status?.isReady ? '1' : '0'}|${parts.join(',')}`;
}

export function demoPackageHintFromStatus(status) {
  const demo = status?.dataPackages?.packages?.demo;
  if (!demo) return '';
  if (demo.present) {
    const size = demo.sizeLabel ? `（${demo.sizeLabel}）` : '';
    return `本地已有演示数据包${size}，导入时无需重新下载。`;
  }
  return '本地尚无演示数据包，选择导入后将从官网下载。';
}

export function fakeProgressTickSize(basePercent, capPercent) {
  const span = Math.max(0, (Number(capPercent) || 0) - (Number(basePercent) || 0));
  if (span <= 0) return 0;
  return Math.min(FAKE_PROGRESS_STEP, Math.max(0.15, span * 0.02));
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
  const fieldLabels = { host: '主机地址', database: '数据库名称', user: '用户名' };
  const missing = ['host', 'database', 'user']
    .filter((key) => !String(submitValues[key] || '').trim())
    .map((key) => fieldLabels[key]);
  if (missing.length > 0) {
    return `请填写 ${missing.join('、')} 后再继续。`;
  }
  return '';
}
