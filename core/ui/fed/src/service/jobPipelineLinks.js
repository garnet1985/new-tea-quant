import { getStrategyDesignPath } from 'api/strategyApi';
import { STRATEGY_DESIGN_STEPS } from 'containers/strategyDesign/constants/strategyDesignSteps';

const STRATEGY_KINDS = new Set([
  'strategy_run',
  'strategy_scan',
  'strategy_attribute',
  'strategy_rolling',
]);

const KIND_TITLE = {
  strategy_run: '制定策略',
  strategy_scan: '策略扫描',
  strategy_attribute: '策略归因',
  strategy_rolling: '滚动测试',
  tag_run: '标签任务',
  data_renew: '数据更新',
  import_data: '导入数据',
};

const STEP_TITLE = Object.fromEntries(
  STRATEGY_DESIGN_STEPS.map((step) => [step.key, step.label]),
);

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
  if (kind === 'import_data') return '/settings/system';
  return '';
}

/**
 * 人类可读任务名（坞 / toast）。
 * 优先 ``display_title``；否则从 kind / resource / label 拼。
 */
export function jobDisplayName(job) {
  if (!job || typeof job !== 'object') return '长任务';
  const explicit = String(job.display_title || '').trim();
  if (explicit) return explicit;

  const kind = String(job.kind || '').trim();
  const resource = String(job.resource_key || '').trim();
  const label = String(job.label || '').trim();
  const step = strategyStepFromJobLabel(label);
  const stepTitle = step ? (STEP_TITLE[step] || step) : '';

  if (kind === 'strategy_run' && resource) {
    return stepTitle ? `${resource} · ${stepTitle}` : resource;
  }
  if (kind === 'strategy_attribute' && resource) {
    const attrStep = (() => {
      const m = /^strategy_attribute:(.+):([a-z_]+)$/.exec(label);
      return m ? String(m[2] || '').trim() : '';
    })();
    const attrTitle = attrStep ? (STEP_TITLE[attrStep] || attrStep) : '';
    return attrTitle ? `${resource} · ${attrTitle}归因` : `${resource} · 策略归因`;
  }
  if (STRATEGY_KINDS.has(kind) && resource) {
    const kindTitle = KIND_TITLE[kind] || kind;
    return `${resource} · ${kindTitle}`;
  }
  if (kind === 'tag_run') {
    return resource ? `标签 · ${resource}` : (KIND_TITLE.tag_run || '标签任务');
  }
  if (kind === 'data_renew') {
    if (!resource || resource === '*') return KIND_TITLE.data_renew || '数据更新';
    return `数据更新 · ${resource}`;
  }
  if (kind === 'import_data') {
    return label || KIND_TITLE.import_data || '导入数据';
  }
  if (resource && KIND_TITLE[kind]) return `${resource} · ${KIND_TITLE[kind]}`;
  if (resource && kind) return `${resource} · ${kind}`;
  return resource || KIND_TITLE[kind] || label || '长任务';
}
