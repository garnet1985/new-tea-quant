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

export const DB_SERVER_FIELD_KEYS = new Set(['host', 'port', 'database', 'user', 'password']);

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
