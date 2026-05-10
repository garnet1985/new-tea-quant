import React, { useEffect, useMemo, useRef, useState } from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  LinearProgress,
  Select,
  Stack,
  Typography,
} from '@mui/material';
import { ReactComponent as PlayCircleIcon } from '../../../../assets/icon/play_circle.svg';
import {
  fetchStrategyRunStatus,
  fetchStrategyVersionDetail,
  startStrategyRun,
} from '../../../../api/apis/strategyApi';
import { buildExecutionResultFromWorkbenchReport } from '../../workbenchExecutionHydration';

const STEP_ENUM = 'enum';
const STEP_PRICE = 'price';
const STEP_CAPITAL = 'capital';

/** 下拉末项：打开完整历史版本选择（占位）；勿写入 ``compareVersion`` */
const EXEC_COMPARE_MORE_MENU_VALUE = '__exec_compare_more_versions__';

const CAPITAL_NUM_FMT = { minimumFractionDigits: 2, maximumFractionDigits: 2 };

/** 执行卡片资金行：金额两位小数；与 ``toLocaleString`` 千分位一致 */
function formatCapitalMoney(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--';
  return Number(value).toLocaleString(undefined, CAPITAL_NUM_FMT);
}

function formatCapitalPct(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--';
  return Number(value).toFixed(2);
}

function StepRunButtonIcon({ done }) {
  return done ? (
    <RefreshRoundedIcon sx={{ fontSize: 18 }} />
  ) : (
    <PlayCircleIcon width={18} height={18} />
  );
}

function StrategyExecutionPanel({
  strategyName,
  settings,
  getSettingsForRun,
  onExecutionStateChange,
  /** 工作台版本列表中的最近 5 条 ``version_id``（与 GET …/versions 顺序一致，新→旧） */
  executionCompareRecentVersionIds = [],
  onProgressResultReport,
  /** 单步 run 成功结束（与 progress 的 ``result_report`` 合并后）；用于报告 Tab 切到对应回测器 */
  onRunStepComplete,
  onRegisterForceHandlers,
  /** V2-01 加载/恢复快照后注入；``key`` 变化时同步卡片状态与摘要行 */
  workbenchHydration = null,
  /** 至少两条快照时可对比；仅一条时隐藏「对比版本」下拉 */
  showVersionCompare = true,
}) {
  const [stepStatus, setStepStatus] = useState({
    enum: 'idle',
    price: 'idle',
    capital: 'idle',
  });
  const [runningStep, setRunningStep] = useState('');
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState({
    enum: null,
    price: null,
    capital: null,
  });
  const [compareVersion, setCompareVersion] = useState({
    enum: '',
    price: '',
    capital: '',
  });
  const [executionMoreVersionsOpen, setExecutionMoreVersionsOpen] = useState(false);
  /** ``version_id`` → 该快照 ``result_report`` 解析后的执行摘要（与 ``buildExecutionResultFromWorkbenchReport`` 一致） */
  const [compareLinesByVersionId, setCompareLinesByVersionId] = useState({});
  const [activeRunId, setActiveRunId] = useState('');
  /** 与 V2-06 ``GET …/{step}/progress`` 路径一致；锁定为本次点击的 step，避免 ``runningStep`` 被状态推导清空后误用 ``enum`` 轮询导致 404 */
  const [progressPollStep, setProgressPollStep] = useState('');
  const [latestRunId, setLatestRunId] = useState('');
  const [runError, setRunError] = useState('');
  const [lastCompletedWorkbenchVersionId, setLastCompletedWorkbenchVersionId] = useState('');

  useEffect(() => {
    if (!onExecutionStateChange) return;
    onExecutionStateChange({
      stepStatus,
      result,
      compareVersion,
      runningStep,
      runId: latestRunId,
      activeRunId,
      lastCompletedWorkbenchVersionId,
    });
  }, [
    activeRunId,
    compareVersion,
    lastCompletedWorkbenchVersionId,
    latestRunId,
    onExecutionStateChange,
    result,
    runningStep,
    stepStatus,
  ]);

  useEffect(() => {
    setStepStatus({
      enum: 'idle',
      price: 'idle',
      capital: 'idle',
    });
    setRunningStep('');
    setProgress(0);
    setResult({
      enum: null,
      price: null,
      capital: null,
    });
    setCompareVersion({
      enum: '',
      price: '',
      capital: '',
    });
    setCompareLinesByVersionId({});
    setActiveRunId('');
    setProgressPollStep('');
    setLatestRunId('');
    setRunError('');
    setLastCompletedWorkbenchVersionId('');
  }, [strategyName]);

  useEffect(() => {
    if (!workbenchHydration || typeof workbenchHydration.key !== 'string') return;
    const { stepStatus: nextStatus, result: nextResult, lastCompletedWorkbenchVersionId: wbVid } = workbenchHydration;
    if (nextStatus && typeof nextStatus === 'object') {
      setStepStatus(nextStatus);
    }
    if (nextResult && typeof nextResult === 'object') {
      setResult(nextResult);
    }
    if (typeof wbVid === 'string') {
      setLastCompletedWorkbenchVersionId(wbVid);
    }
  }, [workbenchHydration?.key, strategyName]);

  /** 已有任务 id、正在轮询进度（与标签文案用的 ``runningStep`` 解耦，避免后者被接口推导清空） */
  const isPollingRun = Boolean(activeRunId);
  const executionBusy = Boolean(activeRunId) || Boolean(runningStep);

  const startRun = async (target, { isForce = false, _retryAfterBusy = false } = {}) => {
    if (!strategyName) return;
    if (executionBusy) {
      // 与左侧草稿 reset 触发的 remount 同一瞬时使用：首帧可能仍认为 busy，下一微任务再试一次
      if (!_retryAfterBusy) {
        queueMicrotask(() => startRun(target, { isForce, _retryAfterBusy: true }));
      }
      return;
    }
    try {
      setRunError('');
      setProgressPollStep(target);
      setRunningStep(target);
      setProgress(0);
      setLastCompletedWorkbenchVersionId('');
      const resolvedSettings = getSettingsForRun ? getSettingsForRun() : settings;
      if (!resolvedSettings) throw new Error('当前参数不可用，无法执行');
      const started = await startStrategyRun(strategyName, target, resolvedSettings, { is_force: isForce });
      const runId = started?.run_id;
      if (!runId) throw new Error('启动执行失败：缺少 run_id');
      setActiveRunId(runId);
      setLatestRunId(runId);
      setRunningStep(started?.resolved_chain?.[0] || target);
      setProgress(0);
      setResult({
        enum: null,
        price: null,
        capital: null,
      });
    } catch (err) {
      setRunError(err?.message || '启动执行失败');
      setProgressPollStep('');
      setRunningStep('');
      setProgress(0);
    }
  };

  const displayRunStep = activeRunId ? (progressPollStep || runningStep) : runningStep;

  const runLabel = useMemo(() => {
    if (!displayRunStep) return '等待开始';
    if (displayRunStep === STEP_ENUM) return '正在执行：枚举机会';
    if (displayRunStep === STEP_PRICE) return '正在执行：价格回测';
    return '正在执行：资金模拟';
  }, [displayRunStep]);

  const getStepClass = (status) => {
    if (status === 'failed') return 'is-error';
    if (status === 'running') return 'is-running';
    if (status === 'done') return 'is-done';
    return 'is-idle';
  };

  const getStepSx = (status) => {
    if (status === 'done') {
      return {
        borderColor: 'success.main',
        backgroundColor: 'success.50',
      };
    }
    if (status === 'running') {
      return {
        borderColor: 'warning.main',
        backgroundColor: 'warning.50',
      };
    }
    if (status === 'failed') {
      return {
        borderColor: 'error.main',
        backgroundColor: 'error.50',
      };
    }
    return {
      borderColor: 'divider',
      backgroundColor: 'background.paper',
    };
  };

  const formatPriceLine = (price, withComparePrefix = false) => (
    price
      ? `${withComparePrefix ? '(对比版本) ' : ''}胜率：${price.winRate}% · ROI：${price.roi}%`
      : `${withComparePrefix ? '(对比版本) ' : ''}胜率：-- · ROI：--`
  );

  const getCompareResultColor = (currentValue, compareValue) => {
    if (!Number.isFinite(currentValue) || !Number.isFinite(compareValue)) return 'text.secondary';
    if (currentValue > compareValue) return 'success.main';
    if (currentValue < compareValue) return 'error.main';
    return 'text.secondary';
  };

  const getCurrentResultColor = (currentValue, compareValue) => {
    if (!Number.isFinite(currentValue) || !Number.isFinite(compareValue)) return 'text.primary';
    if (currentValue > compareValue) return 'success.main';
    if (currentValue < compareValue) return 'error.main';
    return 'text.primary';
  };

  const recentCompareIds = useMemo(() => {
    const raw = Array.isArray(executionCompareRecentVersionIds)
      ? executionCompareRecentVersionIds
      : [];
    return raw
      .map((id) => (typeof id === 'string' ? id.trim() : ''))
      .filter(Boolean)
      .slice(0, 5);
  }, [executionCompareRecentVersionIds]);

  /** 下拉可选对比版本：去掉当前工作台快照，避免与自身对比 */
  const compareDropdownVersionIds = useMemo(() => {
    const cur = String(lastCompletedWorkbenchVersionId || '').trim();
    if (!cur) return recentCompareIds;
    return recentCompareIds.filter((id) => id !== cur);
  }, [recentCompareIds, lastCompletedWorkbenchVersionId]);

  /** 未选对比版本时：展示当前工作台快照版本号 +「当前版本」 */
  const compareBaselineMenuLabel = useMemo(() => {
    const cur = String(lastCompletedWorkbenchVersionId || '').trim();
    return cur ? `${cur}（当前版本）` : '—（当前版本）';
  }, [lastCompletedWorkbenchVersionId]);

  useEffect(() => {
    const cur = String(lastCompletedWorkbenchVersionId || '').trim();
    if (!cur) return;
    setCompareVersion((prev) => {
      let touched = false;
      const next = { ...prev };
      ['enum', 'price', 'capital'].forEach((k) => {
        if (next[k] === cur) {
          next[k] = '';
          touched = true;
        }
      });
      return touched ? next : prev;
    });
  }, [lastCompletedWorkbenchVersionId]);

  const handleExecutionCompareChange = (stepKey, nextValue) => {
    if (nextValue === EXEC_COMPARE_MORE_MENU_VALUE) {
      setExecutionMoreVersionsOpen(true);
      return;
    }
    setCompareVersion((prev) => ({ ...prev, [stepKey]: nextValue }));
  };

  const renderCompareVersionSelectValue = (selected) => {
    if (selected === '' || selected == null) return compareBaselineMenuLabel;
    return String(selected);
  };

  useEffect(() => {
    if (!strategyName) return undefined;
    const ids = [...new Set(
      [compareVersion.enum, compareVersion.price, compareVersion.capital]
        .map((s) => String(s || '').trim())
        .filter(Boolean),
    )];
    if (ids.length === 0) return undefined;

    let cancelled = false;

    ids.forEach((vid) => {
      setCompareLinesByVersionId((prev) => {
        const hit = prev[vid];
        if (hit?.execLine != null && !hit?.error) return prev;
        if (hit?.loading) return prev;
        return { ...prev, [vid]: { loading: true, error: null } };
      });

      fetchStrategyVersionDetail(strategyName, vid)
        .then((res) => {
          if (cancelled) return;
          const rr = res?.result_report;
          const execLine = buildExecutionResultFromWorkbenchReport(
            rr && typeof rr === 'object' ? rr : {},
          );
          setCompareLinesByVersionId((prev) => ({
            ...prev,
            [vid]: { loading: false, execLine, error: null },
          }));
        })
        .catch((err) => {
          if (cancelled) return;
          setCompareLinesByVersionId((prev) => ({
            ...prev,
            [vid]: {
              loading: false,
              execLine: null,
              error: err?.message || '读取对比快照失败',
            },
          }));
        });
    });

    return () => {
      cancelled = true;
    };
  }, [strategyName, compareVersion.enum, compareVersion.price, compareVersion.capital]);

  const renderEnumSummary = () => {
    const currentOpportunities = result.enum?.opportunities;
    const vid = compareVersion.enum?.trim();
    const row = vid ? compareLinesByVersionId[vid] : null;
    const loading = Boolean(vid) && (!row || row.loading);
    const errMsg = row?.error;
    const compareOpportunities = row?.execLine?.enum?.opportunities;

    const gridSx = {
      display: 'grid',
      gridTemplateColumns: 'minmax(0, 1fr) auto minmax(0, 1fr)',
      alignItems: 'center',
      columnGap: 1,
    };

    if (vid && loading) {
      return (
        <Box sx={gridSx}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            机会总数：{Number.isFinite(currentOpportunities) ? `${currentOpportunities} 个` : '--'}
          </Typography>
          <Typography variant="body2" color="text.secondary">-&gt;</Typography>
          <Typography variant="body2" color="text.secondary">(对比版本) 读取中…</Typography>
        </Box>
      );
    }

    if (vid && errMsg) {
      return (
        <Box sx={gridSx}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            机会总数：{Number.isFinite(currentOpportunities) ? `${currentOpportunities} 个` : '--'}
          </Typography>
          <Typography variant="body2" color="text.secondary">-&gt;</Typography>
          <Typography variant="body2" color="error">(对比版本) {errMsg}</Typography>
        </Box>
      );
    }

    if (vid && row?.execLine && !Number.isFinite(compareOpportunities)) {
      return (
        <Box sx={gridSx}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            机会总数：{Number.isFinite(currentOpportunities) ? `${currentOpportunities} 个` : '--'}
          </Typography>
          <Typography variant="body2" color="text.secondary">-&gt;</Typography>
          <Typography variant="body2" color="text.secondary">(对比版本) 该快照无枚举摘要</Typography>
        </Box>
      );
    }

    if (Number.isFinite(currentOpportunities) && Number.isFinite(compareOpportunities)) {
      return (
        <Box sx={gridSx}>
          <Typography
            variant="body2"
            sx={{
              color: getCurrentResultColor(currentOpportunities, compareOpportunities),
              fontWeight: 600,
            }}
          >
            机会总数：{currentOpportunities} 个
          </Typography>
          <Typography variant="body2" color="text.secondary">-&gt;</Typography>
          <Typography
            variant="body2"
            sx={{
              color: getCompareResultColor(compareOpportunities, currentOpportunities),
              fontWeight: 600,
            }}
          >
            (对比版本) 机会总数：{compareOpportunities} 个
          </Typography>
        </Box>
      );
    }

    return (
      <Typography variant="body2">
        机会总数：{Number.isFinite(currentOpportunities) ? `${currentOpportunities} 个` : '--'}
      </Typography>
    );
  };

  const renderPriceSummary = () => {
    const currentPrice = result.price;
    const vid = compareVersion.price?.trim();
    const row = vid ? compareLinesByVersionId[vid] : null;
    const loading = Boolean(vid) && (!row || row.loading);
    const errMsg = row?.error;
    const comparePrice = row?.execLine?.price ?? null;

    const gridSx = {
      display: 'grid',
      gridTemplateColumns: 'minmax(0, 1fr) auto minmax(0, 1fr)',
      alignItems: 'center',
      columnGap: 1,
    };

    if (vid && loading) {
      return (
        <Box sx={gridSx}>
          <Typography variant="body2" sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
            {formatPriceLine(currentPrice)}
          </Typography>
          <Typography variant="body2" color="text.secondary">-&gt;</Typography>
          <Typography variant="body2" color="text.secondary">(对比版本) 读取中…</Typography>
        </Box>
      );
    }

    if (vid && errMsg) {
      return (
        <Box sx={gridSx}>
          <Typography variant="body2" sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
            {formatPriceLine(currentPrice)}
          </Typography>
          <Typography variant="body2" color="text.secondary">-&gt;</Typography>
          <Typography variant="body2" color="error">(对比版本) {errMsg}</Typography>
        </Box>
      );
    }

    if (vid && row?.execLine && currentPrice && !comparePrice) {
      return (
        <Box sx={gridSx}>
          <Typography variant="body2" sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
            {formatPriceLine(currentPrice)}
          </Typography>
          <Typography variant="body2" color="text.secondary">-&gt;</Typography>
          <Typography variant="body2" color="text.secondary">(对比版本) 该快照无价格回测摘要</Typography>
        </Box>
      );
    }

    if (currentPrice && comparePrice) {
      return (
        <Box sx={gridSx}>
          <Typography
            variant="body2"
            sx={{
              color: getCurrentResultColor(currentPrice.roi, comparePrice.roi),
              fontWeight: 600,
              whiteSpace: 'nowrap',
            }}
          >
            {formatPriceLine(currentPrice)}
          </Typography>
          <Typography variant="body2" color="text.secondary">-&gt;</Typography>
          <Typography
            variant="body2"
            sx={{
              color: getCompareResultColor(comparePrice.roi, currentPrice.roi),
              fontWeight: 600,
              whiteSpace: 'nowrap',
            }}
          >
            {formatPriceLine(comparePrice, true)}
          </Typography>
        </Box>
      );
    }

    return <Typography variant="body2">{formatPriceLine(currentPrice)}</Typography>;
  };

  const renderCapitalSummary = () => {
    const cur = result.capital;
    const vid = compareVersion.capital?.trim();
    const row = vid ? compareLinesByVersionId[vid] : null;
    const loading = Boolean(vid) && (!row || row.loading);
    const errMsg = row?.error;
    const cmp = row?.execLine?.capital ?? null;

    const gridSx = {
      display: 'grid',
      gridTemplateColumns: 'minmax(0, 1fr) auto minmax(0, 1fr)',
      alignItems: 'start',
      columnGap: 1,
    };

    if (!cur) {
      return (
        <Stack spacing={0.25}>
          <Typography variant="body2">收益：--</Typography>
          <Typography variant="caption" color="text.secondary">--</Typography>
        </Stack>
      );
    }

    if (!vid) {
      return (
        <Stack spacing={0.25}>
          <Typography variant="body2">
            收益：{`${cur.profit >= 0 ? '+' : ''}${formatCapitalMoney(cur.profit)} (${formatCapitalPct(cur.retPct)}%)`}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {`${formatCapitalMoney(cur.initialCapital)} -> ${formatCapitalMoney(cur.endCapital)}`}
          </Typography>
        </Stack>
      );
    }

    if (loading) {
      return (
        <Box sx={gridSx}>
          <Stack spacing={0.25}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              收益：{`${cur.profit >= 0 ? '+' : ''}${formatCapitalMoney(cur.profit)} (${formatCapitalPct(cur.retPct)}%)`}
            </Typography>
            <Typography variant="caption" sx={{ fontWeight: 600 }}>
              {`${formatCapitalMoney(cur.initialCapital)} -> ${formatCapitalMoney(cur.endCapital)}`}
            </Typography>
          </Stack>
          <Stack justifyContent="center" alignItems="center" sx={{ height: '100%' }}>
            <Typography variant="body2" color="text.secondary">-&gt;</Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary">(对比版本) 读取中…</Typography>
        </Box>
      );
    }

    if (errMsg) {
      return (
        <Box sx={gridSx}>
          <Stack spacing={0.25}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              收益：{`${cur.profit >= 0 ? '+' : ''}${formatCapitalMoney(cur.profit)} (${formatCapitalPct(cur.retPct)}%)`}
            </Typography>
            <Typography variant="caption" sx={{ fontWeight: 600 }}>
              {`${formatCapitalMoney(cur.initialCapital)} -> ${formatCapitalMoney(cur.endCapital)}`}
            </Typography>
          </Stack>
          <Stack justifyContent="center" alignItems="center" sx={{ height: '100%' }}>
            <Typography variant="body2" color="text.secondary">-&gt;</Typography>
          </Stack>
          <Typography variant="body2" color="error">(对比版本) {errMsg}</Typography>
        </Box>
      );
    }

    if (!cmp) {
      return (
        <Box sx={gridSx}>
          <Stack spacing={0.25}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              收益：{`${cur.profit >= 0 ? '+' : ''}${formatCapitalMoney(cur.profit)} (${formatCapitalPct(cur.retPct)}%)`}
            </Typography>
            <Typography variant="caption" sx={{ fontWeight: 600 }}>
              {`${formatCapitalMoney(cur.initialCapital)} -> ${formatCapitalMoney(cur.endCapital)}`}
            </Typography>
          </Stack>
          <Stack justifyContent="center" alignItems="center" sx={{ height: '100%' }}>
            <Typography variant="body2" color="text.secondary">-&gt;</Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary">(对比版本) 该快照无资金摘要</Typography>
        </Box>
      );
    }

    return (
      <Box sx={gridSx}>
        <Stack spacing={0.25}>
          <Typography
            variant="body2"
            sx={{
              color: getCurrentResultColor(cur.profit, cmp.profit),
              fontWeight: 600,
            }}
          >
            收益：{`${cur.profit >= 0 ? '+' : ''}${formatCapitalMoney(cur.profit)} (${formatCapitalPct(cur.retPct)}%)`}
          </Typography>
          <Typography
            variant="caption"
            sx={{
              color: getCurrentResultColor(cur.endCapital, cmp.endCapital),
              fontWeight: 600,
            }}
          >
            {`${formatCapitalMoney(cur.initialCapital)} -> ${formatCapitalMoney(cur.endCapital)}`}
          </Typography>
        </Stack>

        <Stack justifyContent="center" alignItems="center" sx={{ height: '100%' }}>
          <Typography variant="body2" color="text.secondary">-&gt;</Typography>
        </Stack>

        <Stack spacing={0.25}>
          <Typography
            variant="body2"
            sx={{
              color: getCompareResultColor(cmp.profit, cur.profit),
              fontWeight: 600,
            }}
          >
            (对比版本) 收益：{`${cmp.profit >= 0 ? '+' : ''}${formatCapitalMoney(cmp.profit)} (${formatCapitalPct(cmp.retPct)}%)`}
          </Typography>
          <Typography
            variant="caption"
            sx={{
              color: getCompareResultColor(cmp.endCapital, cur.endCapital),
              fontWeight: 600,
            }}
          >
            {`${formatCapitalMoney(cmp.initialCapital)} -> ${formatCapitalMoney(cmp.endCapital)}`}
          </Typography>
        </Stack>
      </Box>
    );
  };

  useEffect(() => {
    if (!strategyName || !activeRunId) return undefined;

    let stopped = false;
    const applyStatus = (status) => {
      const nextStepStatus = status?.step_status || {};
      const normalized = {
        enum: nextStepStatus.enum || 'idle',
        price: nextStepStatus.price || 'idle',
        capital: nextStepStatus.capital || 'idle',
      };
      if (status?.run_id) setLatestRunId(status.run_id);
      setStepStatus(normalized);
      setRunningStep(status?.running_step || '');
      setProgress(Number(status?.progress_pct || 0));
      const report = status?.result_report || {};
      setResult((prev) => ({
        enum: Object.prototype.hasOwnProperty.call(report, 'enum') ? report.enum : prev.enum,
        price: Object.prototype.hasOwnProperty.call(report, 'price') ? report.price : prev.price,
        capital: Object.prototype.hasOwnProperty.call(report, 'capital') ? report.capital : prev.capital,
      }));
      if (status?.state === 'done' && report && Object.keys(report).length > 0) {
        onProgressResultReport?.(report);
        const finishedStep = (progressPollStep || '').trim();
        if (
          finishedStep === STEP_ENUM
          || finishedStep === STEP_PRICE
          || finishedStep === STEP_CAPITAL
        ) {
          onRunStepComplete?.(finishedStep);
        }
      }
      if (status?.state === 'done' && status?.version_id) {
        setLastCompletedWorkbenchVersionId(String(status.version_id));
      }
      if (status?.state === 'done' || status?.state === 'cancelled' || status?.state === 'failed') {
        setActiveRunId('');
        setProgressPollStep('');
        if (status?.state === 'failed') setRunError('执行失败，请检查后端日志。');
      }
    };

    const poll = async () => {
      try {
        const status = await fetchStrategyRunStatus(
          strategyName,
          activeRunId,
          progressPollStep || STEP_ENUM,
        );
        if (stopped) return;
        applyStatus(status);
      } catch (err) {
        if (stopped) return;
        setRunError(err?.message || '读取执行状态失败');
        setActiveRunId('');
        setProgressPollStep('');
      }
    };

    poll();
    const timer = window.setInterval(poll, 800);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [activeRunId, onProgressResultReport, onRunStepComplete, progressPollStep, strategyName]);

  const startRunRef = useRef(startRun);
  startRunRef.current = startRun;

  useEffect(() => {
    if (!onRegisterForceHandlers) return undefined;
    onRegisterForceHandlers({
      forceEnum: () => startRunRef.current(STEP_ENUM, { isForce: true }),
    });
    return () => onRegisterForceHandlers(null);
  }, [onRegisterForceHandlers]);

  /** 该步已为完成态时点播放 = 强制重跑（与 V2-05 ``is_force`` 一致） */
  const runStep = (target) => {
    const st =
      target === STEP_ENUM ? stepStatus.enum
        : target === STEP_PRICE ? stepStatus.price
          : stepStatus.capital;
    const isForce = st === 'done';
    return startRun(target, { isForce });
  };

  return (
    <>
    <Accordion defaultExpanded disableGutters>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography fontWeight={600}>执行面板</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1.25}>
          <Typography variant="body2" color="text.secondary">
            三层执行依赖：价格回测和资金模拟依赖枚举机会；重跑枚举会使下游结果失效。
          </Typography>

          {isPollingRun ? (
            <Box>
              <Typography variant="caption" color="text.secondary">
                {runLabel}
              </Typography>
              <LinearProgress
                variant={progress > 0 ? 'determinate' : 'indeterminate'}
                value={progress > 0 ? progress : 0}
                sx={{ mt: 0.5 }}
              />
            </Box>
          ) : null}
          {runError ? (
            <Typography variant="caption" color="error">{runError}</Typography>
          ) : null}

          <Stack spacing={1}>
            <Box
              className={`exec-step-card ${getStepClass(stepStatus.enum)}`}
              sx={{
                border: 1,
                borderRadius: 1,
                p: 1,
                ...getStepSx(stepStatus.enum),
              }}
            >
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: '48px minmax(140px, 220px) minmax(280px, 1fr) minmax(200px, 260px)',
                  gap: 1,
                  alignItems: 'center',
                }}
              >
                <Box
                  sx={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    border: 1,
                    borderColor: 'text.secondary',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 12,
                    fontWeight: 700,
                  }}
                >
                  1
                </Box>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography fontWeight={600}>枚举机会</Typography>
                  <IconButton
                    size="small"
                    onClick={() => runStep(STEP_ENUM)}
                    disabled={executionBusy}
                    aria-label={stepStatus.enum === 'done' ? '强制重跑枚举' : '运行枚举'}
                  >
                    <StepRunButtonIcon done={stepStatus.enum === 'done'} />
                  </IconButton>
                </Stack>
                {renderEnumSummary()}
                {stepStatus.enum === 'done' && showVersionCompare ? (
                  <Stack direction="row" spacing={1} alignItems="center" justifyContent="flex-end">
                    <Typography variant="caption" color="text.secondary">对比版本</Typography>
                    <Select
                      size="small"
                      displayEmpty
                      value={compareVersion.enum}
                      renderValue={renderCompareVersionSelectValue}
                      onChange={(e) => handleExecutionCompareChange('enum', e.target.value)}
                      sx={{ minWidth: 168 }}
                    >
                      <MenuItem value="">{compareBaselineMenuLabel}</MenuItem>
                      {compareDropdownVersionIds.map((id) => (
                        <MenuItem key={id} value={id}>{id}</MenuItem>
                      ))}
                      <MenuItem value={EXEC_COMPARE_MORE_MENU_VALUE}>更多版本…</MenuItem>
                    </Select>
                  </Stack>
                ) : null}
              </Box>
            </Box>

            <Box
              className={`exec-step-card ${getStepClass(stepStatus.price)}`}
              sx={{
                border: 1,
                borderRadius: 1,
                p: 1,
                ...getStepSx(stepStatus.price),
              }}
            >
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: '48px minmax(140px, 220px) minmax(280px, 1fr) minmax(200px, 260px)',
                  gap: 1,
                  alignItems: 'center',
                }}
              >
                <Box
                  sx={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    border: 1,
                    borderColor: 'text.secondary',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 12,
                    fontWeight: 700,
                  }}
                >
                  2
                </Box>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography fontWeight={600}>价格回测</Typography>
                  <IconButton
                    size="small"
                    onClick={() => runStep(STEP_PRICE)}
                    disabled={executionBusy}
                    aria-label={stepStatus.price === 'done' ? '强制重跑价格回测' : '运行价格回测'}
                  >
                    <StepRunButtonIcon done={stepStatus.price === 'done'} />
                  </IconButton>
                </Stack>
                <Box sx={{ overflowX: 'auto', overflowY: 'hidden', '&::-webkit-scrollbar': { height: 6 } }}>
                  {renderPriceSummary()}
                </Box>
                {stepStatus.price === 'done' && showVersionCompare ? (
                  <Stack direction="row" spacing={1} alignItems="center" justifyContent="flex-end">
                    <Typography variant="caption" color="text.secondary">对比版本</Typography>
                    <Select
                      size="small"
                      displayEmpty
                      value={compareVersion.price}
                      renderValue={renderCompareVersionSelectValue}
                      onChange={(e) => handleExecutionCompareChange('price', e.target.value)}
                      sx={{ minWidth: 168 }}
                    >
                      <MenuItem value="">{compareBaselineMenuLabel}</MenuItem>
                      {compareDropdownVersionIds.map((id) => (
                        <MenuItem key={id} value={id}>{id}</MenuItem>
                      ))}
                      <MenuItem value={EXEC_COMPARE_MORE_MENU_VALUE}>更多版本…</MenuItem>
                    </Select>
                  </Stack>
                ) : null}
              </Box>
            </Box>

            <Box
              className={`exec-step-card ${getStepClass(stepStatus.capital)}`}
              sx={{
                border: 1,
                borderRadius: 1,
                p: 1,
                ...getStepSx(stepStatus.capital),
              }}
            >
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: '48px minmax(140px, 220px) minmax(280px, 1fr) minmax(200px, 260px)',
                  gap: 1,
                  alignItems: 'center',
                }}
              >
                <Box
                  sx={{
                    width: 28,
                    height: 28,
                    borderRadius: '50%',
                    border: 1,
                    borderColor: 'text.secondary',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 12,
                    fontWeight: 700,
                  }}
                >
                  3
                </Box>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography fontWeight={600}>资金模拟</Typography>
                  <IconButton
                    size="small"
                    onClick={() => runStep(STEP_CAPITAL)}
                    disabled={executionBusy}
                    aria-label={stepStatus.capital === 'done' ? '强制重跑资金模拟' : '运行资金模拟'}
                  >
                    <StepRunButtonIcon done={stepStatus.capital === 'done'} />
                  </IconButton>
                </Stack>
                {renderCapitalSummary()}
                {stepStatus.capital === 'done' && showVersionCompare ? (
                  <Stack direction="row" spacing={1} alignItems="center" justifyContent="flex-end">
                    <Typography variant="caption" color="text.secondary">对比版本</Typography>
                    <Select
                      size="small"
                      displayEmpty
                      value={compareVersion.capital}
                      renderValue={renderCompareVersionSelectValue}
                      onChange={(e) => handleExecutionCompareChange('capital', e.target.value)}
                      sx={{ minWidth: 168 }}
                    >
                      <MenuItem value="">{compareBaselineMenuLabel}</MenuItem>
                      {compareDropdownVersionIds.map((id) => (
                        <MenuItem key={id} value={id}>{id}</MenuItem>
                      ))}
                      <MenuItem value={EXEC_COMPARE_MORE_MENU_VALUE}>更多版本…</MenuItem>
                    </Select>
                  </Stack>
                ) : null}
              </Box>
            </Box>
          </Stack>
        </Stack>
      </AccordionDetails>
    </Accordion>

    <Dialog
      open={executionMoreVersionsOpen}
      onClose={() => setExecutionMoreVersionsOpen(false)}
      maxWidth="xs"
      fullWidth
    >
      <DialogTitle>选择历史版本</DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" color="text.secondary">
          完整版本列表将在此提供（占位）。后续可接入分页搜索或与设置区「更多版本」一致的选择器。
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setExecutionMoreVersionsOpen(false)}>关闭</Button>
      </DialogActions>
    </Dialog>
    </>
  );
}

export default StrategyExecutionPanel;
