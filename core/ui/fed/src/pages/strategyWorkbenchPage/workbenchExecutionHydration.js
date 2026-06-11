/**
 * 将 V2-01 / V2-08 的 ``step_status`` / ``execution_panel`` 转为执行面板卡片状态与摘要行。
 * 摘要数值由后端 ``execution_panel`` 提供，前端不做指标换算。
 */

const IDLE = { enum: 'idle', price: 'idle', capital: 'idle' };
const RUN_STEP_NAMES = new Set(['enum', 'price', 'capital']);

/**
 * V2-05 POST ``steps[]`` → 执行面板 stepStatus。只更新计划内步骤，其余保留 ``prev``（依赖链由后端规划）。
 * @param {object} prev
 * @param {object[]} planSteps
 */
export function stepStatusFromRunPlanSteps(planSteps, prev = IDLE) {
  const next = { ...prev };
  if (!Array.isArray(planSteps) || planSteps.length === 0) return next;
  planSteps.forEach((row, idx) => {
    const nm = String(row?.step_name || '').trim();
    if (!RUN_STEP_NAMES.has(nm)) return;
    const backendSt = String(row?.status || '').toLowerCase();
    if (backendSt === 'completed') next[nm] = 'done';
    else if (backendSt === 'running') next[nm] = 'running';
    else if (backendSt === 'failed') next[nm] = 'failed';
    else if (backendSt === 'pending') next[nm] = 'pending';
    else next[nm] = idx === 0 ? 'running' : 'pending';
  });
  return next;
}

/**
 * V2-06b ``step_status_merge`` → 合并进当前 stepStatus（轮询唯一来源，不推断依赖）。
 * @param {object} prev
 * @param {object|null|undefined} progressMerge
 */
export function mergeStepStatusFromRunProgress(prev, progressMerge) {
  if (!progressMerge || typeof progressMerge !== 'object') return prev;
  return { ...prev, ...progressMerge };
}

function slotDone(entry) {
  if (!entry || typeof entry !== 'object') return false;
  return entry.done === true;
}

/**
 * @param {object|null|undefined} apiStepStatus BFF：``enum`` / ``price_factor`` / ``capital_allocation`` → ``{ done: boolean }``
 * @returns {{ enum: string, price: string, capital: string }}
 */
export function mapWorkbenchStepStatusToExecutionCards(apiStepStatus) {
  if (!apiStepStatus || typeof apiStepStatus !== 'object') {
    return { ...IDLE };
  }
  return {
    enum: slotDone(apiStepStatus.enum) ? 'done' : 'idle',
    price: slotDone(apiStepStatus.price_factor) ? 'done' : 'idle',
    capital: slotDone(apiStepStatus.capital_allocation) ? 'done' : 'idle',
  };
}

/**
 * 从 BFF ``execution_panel`` 读取执行面板三行摘要。
 * @param {object|null|undefined} executionPanel
 * @returns {{ enum: object|null, price: object|null, capital: object|null }}
 */
export function buildExecutionResultFromExecutionPanel(executionPanel) {
  const empty = { enum: null, price: null, capital: null };
  if (!executionPanel || typeof executionPanel !== 'object') {
    return empty;
  }
  return {
    enum: executionPanel.enum ?? null,
    price: executionPanel.price ?? null,
    capital: executionPanel.capital ?? null,
  };
}

/**
 * @param {string} strategyName
 * @param {{ versionId?: string, step_status?: object|null, execution_panel?: object|null }} snapshot
 */
export function buildWorkbenchExecutionHydrationFromSnapshot(strategyName, snapshot) {
  const wbVer = String(snapshot?.versionId || '').trim();
  const stepCards = mapWorkbenchStepStatusToExecutionCards(snapshot?.step_status);
  const execResult = buildExecutionResultFromExecutionPanel(snapshot?.execution_panel);
  return {
    key: `${strategyName}:${wbVer || 'none'}`,
    stepStatus: stepCards,
    result: execResult,
    lastCompletedWorkbenchVersionId: wbVer,
  };
}
