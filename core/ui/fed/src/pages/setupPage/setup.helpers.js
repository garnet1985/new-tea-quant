export const STEP_STATUS = {
  NOT_STARTED: 'not_started',
  WAITING_INPUT: 'waiting_input',
  RUNNING: 'running',
  SUCCESS: 'success',
  FAILED: 'failed',
};

export const DEFAULT_STEP_ID = 'db_connection';

export const EMPTY_IMPORT_PROGRESS = {
  running: false,
  totalTables: 0,
  completedCount: 0,
  currentTable: '',
  percent: 0,
};

export function applyDbTypeDefaults(formValues, key, value) {
  const next = { ...formValues, [key]: value };
  if (key === 'dbType') {
    if (value === 'postgresql') {
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
  // 默认路径场景：按后端返回的 showByDefault 控制；
  // 自定义路径场景：只看 blur 预检查结果，避免默认路径状态“串”到自定义路径。
  if (userspacePathEditable) {
    return Boolean(userspacePathExists);
  }
  return Boolean(field.showByDefault);
}
