import { STRATEGY_DESIGN_DEFAULT_STEP } from './constants/strategyDesignSteps';

const IDLE_STEP_STATUS = { enum: 'idle', price: 'idle', portfolio: 'idle' };

/** sessionStorage key 前缀；按策略名区分，便于恢复上次调试步 */
export const STRATEGY_DESIGN_SESSION_STORAGE_PREFIX = 'ntq-strategy-design-session';

export function strategyDesignSessionStorageKey(strategyName) {
  return `${STRATEGY_DESIGN_SESSION_STORAGE_PREFIX}:${String(strategyName || '').trim()}`;
}

function readSessionBlob(strategyName) {
  const sn = String(strategyName || '').trim();
  if (!sn) return null;
  try {
    const raw = sessionStorage.getItem(strategyDesignSessionStorageKey(sn));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : null;
  } catch {
    return null;
  }
}

function writeSessionBlob(strategyName, patch) {
  const sn = String(strategyName || '').trim();
  if (!sn || !patch || typeof patch !== 'object') return;
  try {
    const prev = readSessionBlob(sn) || {};
    sessionStorage.setItem(
      strategyDesignSessionStorageKey(sn),
      JSON.stringify({ ...prev, ...patch, savedAt: Date.now() }),
    );
  } catch {
    /* ignore quota */
  }
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
      result: { enum: null, price: null, portfolio: null },
      compareVersion: { enum: '', price: '', portfolio: '' },
      runningStep: '',
      runId: '',
      activeRunId: '',
      lastCompletedWorkbenchVersionId: '',
    },
    panelsResetEpoch: 0,
    stepProgress: { enum: 0, price: 0, portfolio: 0 },
    lastUpdatedAt: Date.now(),
  };
}

/**
 * 读取本地缓存的上次活跃步（无则默认 enum）。
 * @param {string} strategyName
 */
export function readCachedStrategyDesignStep(strategyName) {
  const parsed = readSessionBlob(strategyName);
  const step = String(parsed?.activeStep || '').trim();
  if (step === 'enum' || step === 'price' || step === 'portfolio') return step;
  return STRATEGY_DESIGN_DEFAULT_STEP;
}

/** @param {string} strategyName @param {string} activeStep */
export function writeCachedStrategyDesignStep(strategyName, activeStep) {
  const step = String(activeStep || '').trim();
  if (!step) return;
  writeSessionBlob(strategyName, { activeStep: step });
}

/**
 * 面包屑短名缓存（避免 settings 返回前用路径名闪一下）。
 * @returns {{ displayName: string, key: string }}
 */
export function readCachedStrategyLabel(strategyName) {
  const parsed = readSessionBlob(strategyName);
  return {
    displayName: String(parsed?.displayName || '').trim(),
    key: String(parsed?.key || '').trim(),
  };
}

/** @param {string} strategyName @param {{ displayName?: string, key?: string }} label */
export function writeCachedStrategyLabel(strategyName, label = {}) {
  const displayName = String(label.displayName || '').trim();
  const key = String(label.key || '').trim();
  if (!displayName && !key) return;
  writeSessionBlob(strategyName, {
    ...(displayName ? { displayName } : {}),
    ...(key ? { key } : {}),
  });
}

/** 列表/扫描页进入制定策略时写入的 location.state。 */
export function buildStrategyDesignNavState(row) {
  if (!row || typeof row !== 'object') return undefined;
  const displayName = String(row.display_name || '').trim();
  const key = String(row.key || '').trim();
  if (!displayName && !key) return undefined;
  return {
    ...(displayName ? { displayName } : {}),
    ...(key ? { strategyKey: key } : {}),
  };
}

/** 从 location.state 取进入时的展示名种子。 */
export function readStrategyLabelFromLocationState(state) {
  if (!state || typeof state !== 'object') return { displayName: '', key: '' };
  return {
    displayName: String(state.displayName || state.display_name || '').trim(),
    key: String(state.strategyKey || state.key || '').trim(),
  };
}
