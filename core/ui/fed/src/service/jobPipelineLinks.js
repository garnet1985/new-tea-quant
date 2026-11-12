import { getStrategyDesignPath } from 'api/strategyApi';

const STRATEGY_KINDS = new Set([
  'strategy_run',
  'strategy_scan',
  'strategy_attribute',
  'strategy_rolling',
]);

/** 从 strategy_run label（``strategy_run:{name}:{step}``）解析工作台 step。 */
export function strategyStepFromJobLabel(label) {
  const raw = String(label || '').trim();
  const m = /^strategy_run:(.+):([a-z_]+)$/.exec(raw);
  if (!m) return '';
  const step = String(m[2] || '').trim();
  return (step === 'enum' || step === 'price' || step === 'portfolio') ? step : '';
}

/**
 * 完成后快捷跳转路径；无法映射时返回空串。
 * @param {{ kind?: string|null, resource_key?: string|null, label?: string|null }} job
 */
export function jobDeepLink(job) {
  if (!job || typeof job !== 'object') return '';
  const kind = String(job.kind || '').trim();
  const resource = String(job.resource_key || '').trim();
  if (STRATEGY_KINDS.has(kind) && resource) {
    const step = kind === 'strategy_run' ? strategyStepFromJobLabel(job.label) : '';
    return getStrategyDesignPath(resource, step);
  }
  if (kind === 'tag_run') return '/advanced/tags';
  if (kind === 'data_renew') return '/advanced/data-sources';
  return '';
}

/** 人类可读任务名（toast 用）。 */
export function jobDisplayName(job) {
  if (!job || typeof job !== 'object') return '长任务';
  const label = String(job.label || '').trim();
  if (label) return label;
  const kind = String(job.kind || '').trim();
  const resource = String(job.resource_key || '').trim();
  if (kind && resource) return `${kind} · ${resource}`;
  return kind || resource || '长任务';
}
