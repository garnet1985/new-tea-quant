import { useCallback, useEffect, useRef, useState } from 'react';
import {
  fetchStrategyRunStatus,
  startStrategyRun,
} from '../../../api/apis/strategyApi';
import {
  mergeStepStatusFromRunProgress,
  stepStatusFromRunPlanSteps,
} from '../../strategyWorkbenchPage/workbenchExecutionHydration';
import { clearStockKlineMemoryCache } from '../../strategyWorkbenchPage/panels/strategyReportPanel/lib/stockKlineMemoryCache';
import {
  clearDesignActiveRun,
  loadDesignActiveRun,
  persistDesignActiveRun,
} from '../lib/strategyDesignActiveRunPersistence';

const RUN_STEPS = new Set(['enum', 'price', 'portfolio']);

function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

/**
 * 制定策略：单步执行 + 轮询 + 刷新后恢复 run（逻辑对齐策略实验室执行面板）。
 */
export function useStrategyDesignExecution({
  strategyName,
  activeStep,
  getDraftSettingsForSubmit,
  setAppliedSettings,
  isLoadingSettings,
  onRunStarted,
  setSession,
  getExecutionState,
}) {
  const [runError, setRunError] = useState('');
  const [progressDetail, setProgressDetail] = useState({
    label: '',
    stageLabel: '',
    counterText: '',
  });

  const progressPollStepRef = useRef('');
  const progressRunKeyRef = useRef('');
  const progressPctHighWaterRef = useRef(0);

  const activeRunId = String(getExecutionState()?.activeRunId || '').trim();
  const executionBusy = Boolean(activeRunId || getExecutionState()?.runningStep);

  const patchExecutionSession = useCallback((executionPatch, extraPatch = {}) => {
    setSession((prev) => ({
      ...prev,
      ...extraPatch,
      executionState: {
        ...prev.executionState,
        ...executionPatch,
      },
      lastUpdatedAt: Date.now(),
    }));
  }, [setSession]);

  const startRun = useCallback(async (target, { isForce = false, _retryAfterBusy = false } = {}) => {
    if (!strategyName || !RUN_STEPS.has(target)) return;
    clearStockKlineMemoryCache();

    if (executionBusy && !_retryAfterBusy) {
      queueMicrotask(() => startRun(target, { isForce, _retryAfterBusy: true }));
      return;
    }

    try {
      setRunError('');
      progressPollStepRef.current = target;
      progressRunKeyRef.current = '';
      progressPctHighWaterRef.current = 0;
      setProgressDetail({ label: '', stageLabel: '', counterText: '' });

      onRunStarted?.();

      patchExecutionSession({
        runningStep: target,
        activeRunId: '',
        runId: '',
        lastCompletedWorkbenchVersionId: '',
      }, {
        stepProgress: { enum: 0, price: 0, portfolio: 0 },
      });

      const resolvedSettings = getDraftSettingsForSubmit?.();
      if (!resolvedSettings) throw new Error('当前参数不可用，无法执行');

      const started = await startStrategyRun(strategyName, target, resolvedSettings, {
        force_refresh: isForce,
      });
      const runId = started?.run_id;
      if (!runId) throw new Error('启动执行失败：缺少 run_id');

      persistDesignActiveRun(strategyName, { activeRunId: runId, progressPollStep: target });

      const planSteps = Array.isArray(started?.steps) ? started.steps : [];
      const nextRunning = started?.resolved_chain?.[0] || target;
      const nextStepStatus = stepStatusFromRunPlanSteps(
        planSteps,
        getExecutionState()?.stepStatus || { enum: 'idle', price: 'idle', portfolio: 'idle' },
      );

      patchExecutionSession({
        activeRunId: runId,
        runId,
        runningStep: nextRunning,
        stepStatus: nextStepStatus,
      });
    } catch (err) {
      setRunError(err?.message || '启动执行失败');
      progressPollStepRef.current = '';
      patchExecutionSession({
        runningStep: '',
        activeRunId: '',
        runId: '',
      });
    }
  }, [
    executionBusy,
    getDraftSettingsForSubmit,
    onRunStarted,
    patchExecutionSession,
    getExecutionState,
    strategyName,
  ]);

  const handleRunCurrentStep = useCallback(() => {
    const st = getExecutionState()?.stepStatus?.[activeStep];
    const isForce = st === 'done';
    return startRun(activeStep, { isForce });
  }, [activeStep, getExecutionState, startRun]);

  const forceEnumerate = useCallback(() => startRun('enum', { isForce: true }), [startRun]);

  useEffect(() => {
    if (!strategyName || activeRunId || isLoadingSettings) return undefined;

    const saved = loadDesignActiveRun(strategyName);
    if (!saved?.activeRunId) return undefined;

    let cancelled = false;
    (async () => {
      try {
        const status = await fetchStrategyRunStatus(strategyName, saved.activeRunId);
        if (cancelled) return;
        if (status?.state === 'running') {
          const pollStep = saved.progressPollStep || status?.running_step || 'enum';
          progressPollStepRef.current = pollStep;
          setSession((prev) => {
            const stepStatus = mergeStepStatusFromRunProgress(
              prev.executionState?.stepStatus || { enum: 'idle', price: 'idle', portfolio: 'idle' },
              status?.step_status_merge,
            );
            return {
              ...prev,
              stepProgress: {
                ...(prev.stepProgress || {}),
                ...(status?.step_progress && typeof status.step_progress === 'object'
                  ? status.step_progress
                  : {}),
              },
              executionState: {
                ...prev.executionState,
                activeRunId: saved.activeRunId,
                runId: saved.activeRunId,
                runningStep: status?.running_step || pollStep,
                stepStatus,
              },
              lastUpdatedAt: Date.now(),
            };
          });
          setProgressDetail({
            label: String(status?.progress_label || '').trim(),
            stageLabel: String(status?.progress_stage_label || '').trim(),
            counterText: String(status?.progress_counter_text || '').trim(),
          });
          const nextPct = Number(status?.progress_pct || 0);
          if (Number.isFinite(nextPct) && nextPct > 0) {
            progressPctHighWaterRef.current = nextPct;
          }
          return;
        }
        clearDesignActiveRun(strategyName);
      } catch {
        if (!cancelled) clearDesignActiveRun(strategyName);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [activeRunId, isLoadingSettings, setSession, strategyName]);

  useEffect(() => {
    if (!strategyName || !activeRunId) return undefined;

    let stopped = false;

    const applyStatus = (status) => {
      const patch = status?.step_status_merge && typeof status.step_status_merge === 'object'
        ? status.step_status_merge
        : {};
      const nextRunningStep = status?.running_step || '';

      setProgressDetail({
        label: String(status?.progress_label || '').trim(),
        stageLabel: String(status?.progress_stage_label || '').trim(),
        counterText: String(status?.progress_counter_text || '').trim(),
      });

      const runKey = `${status?.run_id || activeRunId}:${nextRunningStep}`;
      if (runKey !== progressRunKeyRef.current) {
        progressRunKeyRef.current = runKey;
        progressPctHighWaterRef.current = 0;
      }

      let nextPct = Number(status?.progress_pct || 0);
      if (status?.state === 'done') {
        nextPct = 100;
        progressPctHighWaterRef.current = 0;
      } else if (nextRunningStep) {
        nextPct = Math.min(100, Math.max(0, nextPct));
        nextPct = Math.max(progressPctHighWaterRef.current, nextPct);
        progressPctHighWaterRef.current = nextPct;
      } else {
        nextPct = 0;
        progressPctHighWaterRef.current = 0;
      }

      const progressPatch = status?.step_progress && typeof status.step_progress === 'object'
        ? status.step_progress
        : {};

      setSession((prev) => {
        const nextStepStatus = mergeStepStatusFromRunProgress(
          prev.executionState?.stepStatus || { enum: 'idle', price: 'idle', portfolio: 'idle' },
          patch,
        );
        const mergedProgress = { ...(prev.stepProgress || {}), ...progressPatch };
        if (nextRunningStep && RUN_STEPS.has(nextRunningStep)) {
          mergedProgress[nextRunningStep] = nextPct;
        }

        const executionPatch = {
          stepStatus: nextStepStatus,
          runningStep: nextRunningStep,
          runId: status?.run_id || activeRunId,
        };

        if (status?.state === 'done' && status?.version_id) {
          executionPatch.lastCompletedWorkbenchVersionId = String(status.version_id);
        }

        if (status?.state === 'done' || status?.state === 'cancelled' || status?.state === 'failed') {
          clearDesignActiveRun(strategyName);
          executionPatch.activeRunId = '';
          executionPatch.runningStep = '';
          if (status?.state === 'failed') {
            setRunError(status?.fail_reason || '执行失败，请检查后端日志。');
          }
        }

        return {
          ...prev,
          stepProgress: mergedProgress,
          executionState: {
            ...prev.executionState,
            ...executionPatch,
          },
          lastUpdatedAt: Date.now(),
        };
      });

      if (status?.state === 'done') {
        const finishedStep = (progressPollStepRef.current || '').trim();
        if (RUN_STEPS.has(finishedStep)) {
          const draft = getDraftSettingsForSubmit?.();
          if (draft && typeof draft === 'object') {
            const cloned = deepClone(draft);
            setAppliedSettings(cloned);
            setSession((prev) => ({
              ...prev,
              appliedSettings: cloned,
              lastUpdatedAt: Date.now(),
            }));
          }
        }
      }
    };

    const poll = async () => {
      try {
        const status = await fetchStrategyRunStatus(strategyName, activeRunId);
        if (stopped) return;
        applyStatus(status);
      } catch (err) {
        if (stopped) return;
        setRunError(err?.message || '读取执行状态失败');
        patchExecutionSession({
          activeRunId: '',
          runningStep: '',
        });
        progressPollStepRef.current = '';
        clearDesignActiveRun(strategyName);
      }
    };

    poll();
    const timer = window.setInterval(poll, 800);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [
    activeRunId,
    getDraftSettingsForSubmit,
    patchExecutionSession,
    setAppliedSettings,
    setSession,
    strategyName,
  ]);

  useEffect(() => {
    if (!strategyName) {
      setRunError('');
      progressPollStepRef.current = '';
    }
  }, [strategyName]);

  return {
    runError,
    progressDetail,
    handleRunCurrentStep,
    forceEnumerate,
    executionBusy,
  };
}
