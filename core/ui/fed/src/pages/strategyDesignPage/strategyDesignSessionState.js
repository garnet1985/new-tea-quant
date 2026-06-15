import { STRATEGY_DESIGN_DEFAULT_STEP } from './constants/strategyDesignSteps';

const IDLE_STEP_STATUS = { enum: 'idle', price: 'idle', capital: 'idle' };

/** sessionStorage key 前缀；按策略名区分，便于恢复上次调试步 */
export const STRATEGY_DESIGN_SESSION_STORAGE_PREFIX = 'ntq-strategy-design-session';

export function strategyDesignSessionStorageKey(strategyName) {
  return `${STRATEGY_DESIGN_SESSION_STORAGE_PREFIX}:${String(strategyName || '').trim()}`;
}

/**
 * 制定策略 Layout 层持有的会话状态（后续接 API / 持久化）。
 * @param {string} strategyName
 * @param {string} [activeStep]
 */
export function createEmptyStrategyDesignSession(strategyName, activeStep = STRATEGY_DESIGN_DEFAULT_STEP) {
  return {
    strategyName: String(strategyName || '').trim(),
    activeStep,
    workbenchSnapshot: null,
    draftSettings: null,
    appliedSettings: null,
    executionState: {
      stepStatus: { ...IDLE_STEP_STATUS },
      result: { enum: null, price: null, capital: null },
      compareVersion: { enum: '', price: '', capital: '' },
      runningStep: '',
      runId: '',
      activeRunId: '',
      lastCompletedWorkbenchVersionId: '',
    },
    panelsResetEpoch: 0,
    stepProgress: { enum: 0, price: 0, capital: 0 },
    lastUpdatedAt: Date.now(),
  };
}

/**
 * 读取本地缓存的上次活跃步（无则默认 enum）。
 * @param {string} strategyName
 */
export function readCachedStrategyDesignStep(strategyName) {
  const sn = String(strategyName || '').trim();
  if (!sn) return STRATEGY_DESIGN_DEFAULT_STEP;
  try {
    const raw = sessionStorage.getItem(strategyDesignSessionStorageKey(sn));
    if (!raw) return STRATEGY_DESIGN_DEFAULT_STEP;
    const parsed = JSON.parse(raw);
    const step = String(parsed?.activeStep || '').trim();
    if (step === 'enum' || step === 'price' || step === 'capital') return step;
  } catch {
    /* ignore */
  }
  return STRATEGY_DESIGN_DEFAULT_STEP;
}

/** @param {string} strategyName @param {string} activeStep */
export function writeCachedStrategyDesignStep(strategyName, activeStep) {
  const sn = String(strategyName || '').trim();
  const step = String(activeStep || '').trim();
  if (!sn || !step) return;
  try {
    sessionStorage.setItem(
      strategyDesignSessionStorageKey(sn),
      JSON.stringify({ activeStep: step, savedAt: Date.now() }),
    );
  } catch {
    /* ignore quota */
  }
}
