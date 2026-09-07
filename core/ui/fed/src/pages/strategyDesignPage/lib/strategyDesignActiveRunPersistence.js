import logClientError from '../../../utils/logClientError';

const ACTIVE_RUN_STORAGE_PREFIX = 'ntq-design-active-run';

function activeRunStorageKey(strategyName) {
  return `${ACTIVE_RUN_STORAGE_PREFIX}:${String(strategyName || '').trim()}`;
}

export function persistDesignActiveRun(strategyName, { activeRunId, progressPollStep }) {
  const sn = String(strategyName || '').trim();
  const rid = String(activeRunId || '').trim();
  if (!sn || !rid) return;
  try {
    sessionStorage.setItem(
      activeRunStorageKey(sn),
      JSON.stringify({
        activeRunId: rid,
        progressPollStep: String(progressPollStep || '').trim(),
        savedAt: Date.now(),
      }),
    );
  } catch (error) {
    logClientError('design.activeRunStorage.write', error, sn);
  }
}

export function clearDesignActiveRun(strategyName) {
  const sn = String(strategyName || '').trim();
  if (!sn) return;
  try {
    sessionStorage.removeItem(activeRunStorageKey(sn));
  } catch (error) {
    logClientError('design.activeRunStorage.clear', error, sn);
  }
}

export function loadDesignActiveRun(strategyName) {
  const sn = String(strategyName || '').trim();
  if (!sn) return null;
  try {
    const raw = sessionStorage.getItem(activeRunStorageKey(sn));
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return null;
    const activeRunId = String(parsed.activeRunId || '').trim();
    if (!activeRunId) return null;
    return {
      activeRunId,
      progressPollStep: String(parsed.progressPollStep || '').trim(),
    };
  } catch (error) {
    logClientError('design.activeRunStorage.read', error, sn);
    return null;
  }
}
