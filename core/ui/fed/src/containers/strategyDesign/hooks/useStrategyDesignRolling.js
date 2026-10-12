import { useCallback, useEffect, useRef, useState } from 'react';
import {
  fetchRollingReport,
  fetchRollingRunStatus,
  fetchRollingStatus,
  startRollingRun,
} from '../../../api/strategyApi';
import { notifyTaskSuccess } from '../../../service/feedbackPromptBus';
import logClientError from '../../../service/logClientError';

const EMPTY_STATUS = {
  enabled: false,
  reason: '',
  tooltip: '',
  has_report: false,
  parent_version_id: '',
  window_count: 0,
};

const SETTINGS_CHANGED = '设置已变更。恢复设置或版本后，才能滚动测试。';

/**
 * 投资组合面板的滚动测试：按钮状态、进度和报告。
 */
export function useStrategyDesignRolling({
  strategyName,
  isLoadingSettings,
  executionBusy = false,
  attributeBusy = false,
  stepStatus = null,
  versionId = '',
  settingsApplied = true,
  setReportViewTab,
}) {
  const [status, setStatus] = useState(EMPTY_STATUS);
  const [rollingError, setRollingError] = useState('');
  const [activeJobId, setActiveJobId] = useState('');
  const [rollingStarting, setRollingStarting] = useState(false);
  const [progressDetail, setProgressDetail] = useState({
    label: '',
    stageLabel: '',
    counterText: '',
  });
  const [progressPct, setProgressPct] = useState(0);
  const [report, setReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const pctHighWaterRef = useRef(0);
  const startLockRef = useRef(false);

  const rollingBusy = Boolean(activeJobId) || rollingStarting;
  const stepsKey = [
    stepStatus?.enum,
    stepStatus?.price,
    stepStatus?.portfolio,
  ].join('|');

  const loadReport = useCallback(async () => {
    if (!strategyName) {
      setReport(null);
      return;
    }
    setReportLoading(true);
    try {
      const payload = await fetchRollingReport(strategyName);
      setReport(payload && typeof payload === 'object' ? payload : null);
    } catch (err) {
      logClientError('design.rollingReport', err);
      setReport(null);
    } finally {
      setReportLoading(false);
    }
  }, [strategyName]);

  const refreshStatus = useCallback(async () => {
    if (!settingsApplied) {
      setStatus({ ...EMPTY_STATUS, tooltip: SETTINGS_CHANGED });
      setReport(null);
      return;
    }
    if (!strategyName || isLoadingSettings) {
      setStatus(EMPTY_STATUS);
      setReport(null);
      return;
    }
    try {
      const next = await fetchRollingStatus(strategyName);
      setStatus(next);
      if (next.has_report) {
        await loadReport();
      } else {
        setReport(null);
      }
    } catch (err) {
      logClientError('design.rollingStatus', err);
      setStatus(EMPTY_STATUS);
      setReport(null);
    }
  }, [isLoadingSettings, loadReport, settingsApplied, strategyName]);

  useEffect(() => {
    setReport(null);
    setStatus(EMPTY_STATUS);
    if (typeof setReportViewTab === 'function') {
      setReportViewTab('backtest');
    }
  }, [setReportViewTab, settingsApplied, versionId]);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus, stepsKey, versionId, settingsApplied]);

  const handleRollingRun = useCallback(async () => {
    if (startLockRef.current) return;
    if (!strategyName || rollingBusy || executionBusy || attributeBusy) return;
    if (!settingsApplied || !status.enabled) return;
    startLockRef.current = true;
    setRollingStarting(true);
    setRollingError('');
    pctHighWaterRef.current = 0;
    setProgressPct(0);
    setProgressDetail({ label: '', stageLabel: '', counterText: '' });
    try {
      const started = await startRollingRun(strategyName, {
        force_refresh: Boolean(status.has_report || report),
      });
      const jobId = started?.job_id || started?.run_id;
      if (!jobId) throw new Error('启动滚动对照失败：缺少 job_id');
      setActiveJobId(jobId);
      if (typeof setReportViewTab === 'function') {
        setReportViewTab('rolling');
      }
    } catch (err) {
      setRollingError(err?.message || '启动滚动对照失败');
      setActiveJobId('');
    } finally {
      startLockRef.current = false;
      setRollingStarting(false);
    }
  }, [
    attributeBusy,
    executionBusy,
    report,
    rollingBusy,
    setReportViewTab,
    settingsApplied,
    status.enabled,
    status.has_report,
    strategyName,
  ]);

  useEffect(() => {
    if (!strategyName || !activeJobId) return undefined;
    let stopped = false;

    const applyStatus = (mapped) => {
      setProgressDetail({
        label: String(mapped?.progress_label || '').trim(),
        stageLabel: String(mapped?.progress_stage_label || '').trim(),
        counterText: String(mapped?.progress_counter_text || '').trim(),
      });
      let nextPct = Number(mapped?.progress_pct || 0);
      if (mapped?.state === 'done') {
        nextPct = 100;
        pctHighWaterRef.current = 0;
      } else {
        nextPct = Math.min(100, Math.max(0, nextPct));
        nextPct = Math.max(pctHighWaterRef.current, nextPct);
        pctHighWaterRef.current = nextPct;
      }
      setProgressPct(nextPct);

      if (mapped?.state === 'done') {
        setActiveJobId('');
        notifyTaskSuccess('strategy_rolling');
        refreshStatus();
      } else if (mapped?.state === 'failed' || mapped?.state === 'cancelled') {
        setActiveJobId('');
        setRollingError(mapped?.fail_reason || '滚动对照失败，请检查后端日志。');
      }
    };

    const poll = async () => {
      try {
        const mapped = await fetchRollingRunStatus(strategyName, activeJobId);
        if (stopped) return;
        applyStatus(mapped);
      } catch (err) {
        if (stopped) return;
        setRollingError(err?.message || '读取滚动进度失败');
        setActiveJobId('');
      }
    };

    poll();
    const timer = window.setInterval(poll, 800);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [activeJobId, refreshStatus, strategyName]);

  return {
    rollingEnabled: Boolean(settingsApplied && status.enabled),
    rollingTooltip: String(status.tooltip || ''),
    rollingHasReport: Boolean(settingsApplied && (status.has_report || report)),
    rollingBusy,
    rollingError,
    rollingProgressDetail: progressDetail,
    rollingProgressPct: progressPct,
    rollingReport: settingsApplied ? report : null,
    rollingReportLoading: reportLoading,
    handleRollingRun,
  };
}
