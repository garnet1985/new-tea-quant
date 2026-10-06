import { useCallback, useEffect, useRef, useState } from 'react';
import {
  fetchAttributeReport,
  fetchAttributeRunStatus,
  fetchAttributeStatus,
  startAttributeRun,
} from '../../../api/strategyApi';
import { notifyTaskSuccess } from '../../../utils/feedbackPromptBus';
import logClientError from '../../../utils/logClientError';

const ATTR_STEPS = new Set(['enum', 'price', 'portfolio']);

const EMPTY_STATUS = {
  visible: false,
  enabled: false,
  reason: '',
  tooltip: '',
  example_path: '',
  last_group_id: '',
};

/**
 * 制定策略：本层归因按钮状态 + 启动 / 轮询 / 拉报告。
 */
export function useStrategyDesignAttribution({
  strategyName,
  activeStep,
  isLoadingSettings,
  /** 回测忙时禁止再开归因（后端也单飞） */
  executionBusy = false,
  /** 回测刚完成时可触发重新 probe */
  stepStatus = null,
  /** 当前策略版本。换版本后只显示这一版的归因。 */
  versionId = '',
}) {
  const [status, setStatus] = useState(EMPTY_STATUS);
  const [statusLoading, setStatusLoading] = useState(false);
  const [attrError, setAttrError] = useState('');
  const [activeJobId, setActiveJobId] = useState('');
  const [progressDetail, setProgressDetail] = useState({
    label: '',
    stageLabel: '',
    counterText: '',
  });
  const [progressPct, setProgressPct] = useState(0);
  const [report, setReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportTab, setReportTab] = useState('backtest');

  const pollStepRef = useRef('');
  const pctHighWaterRef = useRef(0);

  const attributeBusy = Boolean(activeJobId);
  const panelBusy = Boolean(executionBusy || attributeBusy);

  const loadReport = useCallback(async (step, groupId) => {
    const gid = String(groupId || '').trim();
    if (!strategyName || !ATTR_STEPS.has(step) || !gid) {
      setReport(null);
      return;
    }
    setReportLoading(true);
    try {
      const payload = await fetchAttributeReport(strategyName, step, gid);
      setReport(payload && typeof payload === 'object' ? payload : null);
    } catch (err) {
      logClientError('design.attributeReport', err);
      setReport(null);
      setAttrError(err?.message || '读取归因报告失败');
    } finally {
      setReportLoading(false);
    }
  }, [strategyName]);

  const refreshStatus = useCallback(async () => {
    if (!strategyName || !ATTR_STEPS.has(activeStep) || isLoadingSettings) {
      setStatus(EMPTY_STATUS);
      setReport(null);
      return;
    }
    setStatusLoading(true);
    try {
      const next = await fetchAttributeStatus(strategyName, activeStep);
      setStatus(next);
      if (next.last_group_id) {
        await loadReport(activeStep, next.last_group_id);
      } else {
        setReport(null);
      }
    } catch (err) {
      logClientError('design.attributeStatus', err);
      setStatus(EMPTY_STATUS);
      setReport(null);
    } finally {
      setStatusLoading(false);
    }
  }, [activeStep, isLoadingSettings, loadReport, strategyName]);

  useEffect(() => {
    setReport(null);
    setStatus((prev) => ({ ...prev, last_group_id: '' }));
  }, [versionId]);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus, stepStatus?.[activeStep], versionId]);

  useEffect(() => {
    setReportTab('backtest');
    setAttrError('');
    setProgressDetail({ label: '', stageLabel: '', counterText: '' });
    setProgressPct(0);
  }, [activeStep, strategyName]);

  const handleAttributeRun = useCallback(async () => {
    if (!strategyName || !ATTR_STEPS.has(activeStep) || panelBusy) return;
    if (!status.enabled) return;
    const isForce = Boolean(status.last_group_id || report);
    setAttrError('');
    pctHighWaterRef.current = 0;
    setProgressPct(0);
    setProgressDetail({ label: '', stageLabel: '', counterText: '' });
    pollStepRef.current = activeStep;
    try {
      const started = await startAttributeRun(strategyName, activeStep, {
        force_refresh: isForce,
      });
      const jobId = started?.job_id || started?.run_id;
      if (!jobId) throw new Error('启动归因失败：缺少 job_id');
      setActiveJobId(jobId);
      setReportTab('attribute');
    } catch (err) {
      setAttrError(err?.message || '启动归因失败');
      setActiveJobId('');
    }
  }, [
    activeStep,
    panelBusy,
    report,
    status.enabled,
    status.last_group_id,
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
        const gid = String(mapped?.group_id || '').trim();
        setActiveJobId('');
        setStatus((prev) => ({
          ...prev,
          last_group_id: gid || prev.last_group_id,
        }));
        if (gid) {
          loadReport(pollStepRef.current || activeStep, gid);
        }
        notifyTaskSuccess('strategy_attribute');
        refreshStatus();
      } else if (mapped?.state === 'failed' || mapped?.state === 'cancelled') {
        setActiveJobId('');
        setAttrError(mapped?.fail_reason || '归因失败，请检查后端日志。');
      }
    };

    const poll = async () => {
      try {
        const mapped = await fetchAttributeRunStatus(strategyName, activeJobId);
        if (stopped) return;
        applyStatus(mapped);
      } catch (err) {
        if (stopped) return;
        setAttrError(err?.message || '读取归因进度失败');
        setActiveJobId('');
      }
    };

    poll();
    const timer = window.setInterval(poll, 800);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [activeJobId, activeStep, loadReport, refreshStatus, strategyName]);

  return {
    attributeVisible: Boolean(status.visible),
    attributeEnabled: Boolean(status.enabled),
    attributeTooltip: String(status.tooltip || ''),
    attributeExamplePath: String(status.example_path || ''),
    attributeLastGroupId: String(status.last_group_id || ''),
    attributeBusy,
    attributeStatusLoading: statusLoading,
    attrError,
    attributeProgressDetail: progressDetail,
    attributeProgressPct: progressPct,
    attributeReport: report,
    attributeReportLoading: reportLoading,
    reportViewTab: reportTab,
    setReportViewTab: setReportTab,
    handleAttributeRun,
    refreshAttributeStatus: refreshStatus,
    panelBusy,
  };
}
