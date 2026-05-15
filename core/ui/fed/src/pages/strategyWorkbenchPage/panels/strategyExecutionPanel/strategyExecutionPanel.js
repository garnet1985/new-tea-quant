import React, { useEffect, useRef, useState } from 'react';
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
  Select,
  Stack,
  Typography,
} from '@mui/material';
import { ReactComponent as PlayCircleIcon } from '../../../../assets/icon/play_circle.svg';
import './strategyExecutionPanel.scss';
import {
  fetchStrategyRunStatus,
  fetchStrategyVersionDetail,
  startStrategyRun,
} from '../../../../api/apis/strategyApi';
import { buildExecutionResultFromWorkbenchReport } from '../../workbenchExecutionHydration';
import { useWorkbenchCompareVersionMenu } from '../../workbenchCompareVersionMenu';

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

const STEP_RUN_ICON_PX = 29;

function StepRunButtonIcon({ done }) {
  return done ? (
    <RefreshRoundedIcon sx={{ fontSize: STEP_RUN_ICON_PX }} />
  ) : (
    <PlayCircleIcon width={STEP_RUN_ICON_PX} height={STEP_RUN_ICON_PX} />
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
  }, [workbenchHydration, strategyName]);

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
      const planSteps = Array.isArray(started?.steps) ? started.steps : [];
      setStepStatus((prev) => {
        if (!planSteps.length) {
          return { enum: 'running', price: 'idle', capital: 'idle' };
        }
        const next = { ...prev };
        planSteps.forEach((row, idx) => {
          const nm = String(row.step_name || '').trim();
          if (nm !== STEP_ENUM && nm !== STEP_PRICE && nm !== STEP_CAPITAL) return;
          next[nm] = idx === 0 ? 'running' : 'pending';
        });
        return next;
      });
      /* 只清空「本次会重跑」的步骤及之后链上的结果；已完成的上一屏摘要保留 */
      setResult((prev) => {
        const order = [STEP_ENUM, STEP_PRICE, STEP_CAPITAL];
        const startIdx = order.indexOf(target);
        if (startIdx < 0) {
          return { enum: null, price: null, capital: null };
        }
        const next = {
          enum: prev.enum,
          price: prev.price,
          capital: prev.capital,
        };
        for (let i = startIdx; i < order.length; i += 1) {
          next[order[i]] = null;
        }
        return next;
      });
    } catch (err) {
      setRunError(err?.message || '启动执行失败');
      setProgressPollStep('');
      setRunningStep('');
      setProgress(0);
    }
  };

  const getStepClass = (status) => {
    if (status === 'failed') return 'is-error';
    if (status === 'running') return 'is-running';
    if (status === 'pending') return 'is-pending';
    if (status === 'done') return 'is-done';
    return 'is-idle';
  };

  const getStepSx = (status) => {
    if (status === 'done') {
      return {
        borderColor: 'rgba(34, 197, 94, 0.32)',
        /* 满幅绿色进度在 exec-step-card__progress--done */
        backgroundColor: 'rgba(255, 255, 255, 0.02)',
      };
    }
    if (status === 'running') {
      return {
        borderColor: 'rgba(34, 211, 238, 0.55)',
        /* 进度条为左→右 cyan 叠层 */
        backgroundColor: 'rgba(0, 0, 0, 0.22)',
      };
    }
    if (status === 'pending') {
      return {
        borderColor: 'rgba(34, 211, 238, 0.22)',
        backgroundColor: 'rgba(0, 0, 0, 0.12)',
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

  /** 每步卡片内左→右进度：完成满幅；执行中跟 progress_pct；未知进度时 indeterminate */
  const renderStepProgressOverlay = (stepKey) => {
    const st = stepStatus[stepKey];
    if (st === 'pending') return null;
    if (st === 'failed') return null;
    if (st === 'done') {
      return (
        <Box
          className="exec-step-card__progress exec-step-card__progress--done"
          style={{ width: '100%' }}
          aria-hidden
        />
      );
    }
    const visuallyRunning = st === 'running';
    if (!visuallyRunning) return null;
    if (progress > 0) {
      const pct = Math.min(100, Math.max(0, Number(progress)));
      return (
        <Box
          className="exec-step-card__progress exec-step-card__progress--run"
          style={{ width: `${pct}%` }}
          aria-hidden
        />
      );
    }
    return (
      <Box
        className="exec-step-card__progress exec-step-card__progress--indeterminate"
        aria-hidden
      />
    );
  };

  const formatPriceLine = (price) => (
    price
      ? `胜率：${price.winRate}% · ROI：${price.roi}%`
      : '胜率：-- · ROI：--'
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

  const {
    compareDropdownVersionIds,
    compareBaselineMenuLabel,
    renderCompareSelectValue,
  } = useWorkbenchCompareVersionMenu(
    executionCompareRecentVersionIds,
    lastCompletedWorkbenchVersionId,
  );

  const renderExecutionCompareValue = (selected) => {
    const s = String(selected ?? '').trim();
    if (!s) return '对比版本';
    return `对比版本：${renderCompareSelectValue(s)}`;
  };

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
      window.setTimeout(() => setExecutionMoreVersionsOpen(true), 0);
      return;
    }
    setCompareVersion((prev) => ({ ...prev, [stepKey]: nextValue }));
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
      display: 'flex',
      alignItems: 'center',
      gap: 1,
      flexWrap: 'nowrap',
      minWidth: 0,
      overflowX: 'auto',
      overflowY: 'hidden',
      '&::-webkit-scrollbar': { height: 6 },
    };

    if (vid && loading) {
      return (
        <Box sx={gridSx}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            机会总数：{Number.isFinite(currentOpportunities) ? `${currentOpportunities} 个` : '--'}
          </Typography>
          <Typography variant="body2" color="text.secondary">-&gt;</Typography>
          <Typography variant="body2" color="text.secondary">读取中…</Typography>
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
          <Typography variant="body2" color="error">{errMsg}</Typography>
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
          <Typography variant="body2" color="text.secondary">该快照无枚举摘要</Typography>
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
            机会总数：{compareOpportunities} 个
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
      display: 'flex',
      alignItems: 'center',
      gap: 1,
      flexWrap: 'nowrap',
      minWidth: 0,
      overflowX: 'auto',
      overflowY: 'hidden',
      '&::-webkit-scrollbar': { height: 6 },
    };

    if (vid && loading) {
      return (
        <Box sx={gridSx}>
          <Typography variant="body2" sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
            {formatPriceLine(currentPrice)}
          </Typography>
          <Typography variant="body2" color="text.secondary">-&gt;</Typography>
          <Typography variant="body2" color="text.secondary">读取中…</Typography>
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
          <Typography variant="body2" color="error">{errMsg}</Typography>
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
          <Typography variant="body2" color="text.secondary">该快照无价格回测摘要</Typography>
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
            {formatPriceLine(comparePrice)}
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
      display: 'flex',
      alignItems: 'flex-start',
      gap: 1,
      flexWrap: 'nowrap',
      minWidth: 0,
      overflowX: 'auto',
      overflowY: 'hidden',
      '&::-webkit-scrollbar': { height: 6 },
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
          <Typography variant="body2" color="text.secondary">读取中…</Typography>
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
          <Typography variant="body2" color="error">{errMsg}</Typography>
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
          <Typography variant="body2" color="text.secondary">该快照无资金摘要</Typography>
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
            收益：{`${cmp.profit >= 0 ? '+' : ''}${formatCapitalMoney(cmp.profit)} (${formatCapitalPct(cmp.retPct)}%)`}
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
      if (status?.run_id) setLatestRunId(status.run_id);
      const patch = status?.step_status_merge && typeof status.step_status_merge === 'object'
        ? status.step_status_merge
        : {};
      setStepStatus((prev) => ({ ...prev, ...patch }));
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
        if (status?.state === 'failed') {
          setRunError(status?.fail_reason || '执行失败，请检查后端日志。');
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
            三层回测：枚举机会 - 帮助您看到策略发现机会的能力。价格回测 - 初步验证策略可行性。资金模拟 - 加入资金管理，模拟实际交易。
          </Typography>

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
              {renderStepProgressOverlay('enum')}
              <Box
                className="ntq-exec-step-grid exec-step-card__body"
              >
                <Box className="ntq-exec-step-no">
                  1
                </Box>
                <Stack direction="row" spacing={1} alignItems="center" className="ntq-exec-step-title">
                  <Typography fontWeight={600} noWrap>枚举机会</Typography>
                  <IconButton
                    className="ntq-exec-step-run-btn"
                    onClick={() => runStep(STEP_ENUM)}
                    disabled={executionBusy}
                    aria-label={stepStatus.enum === 'done' ? '强制重跑枚举' : '运行枚举'}
                  >
                    <StepRunButtonIcon done={stepStatus.enum === 'done'} />
                  </IconButton>
                </Stack>
                {renderEnumSummary()}
                {stepStatus.enum === 'done' && showVersionCompare ? (
                  <Stack direction="row" spacing={1} alignItems="center" justifyContent="flex-end" className="ntq-exec-compare">
                    <Select
                      size="small"
                      displayEmpty
                      value={compareVersion.enum}
                      renderValue={renderExecutionCompareValue}
                      onChange={(e) => handleExecutionCompareChange('enum', e.target.value)}
                      className="ntq-exec-compare__select"
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
              {renderStepProgressOverlay('price')}
              <Box
                className="ntq-exec-step-grid exec-step-card__body"
              >
                <Box className="ntq-exec-step-no">
                  2
                </Box>
                <Stack direction="row" spacing={1} alignItems="center" className="ntq-exec-step-title">
                  <Typography fontWeight={600} noWrap>价格回测</Typography>
                  <IconButton
                    className="ntq-exec-step-run-btn"
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
                  <Stack direction="row" spacing={1} alignItems="center" justifyContent="flex-end" className="ntq-exec-compare">
                    <Select
                      size="small"
                      displayEmpty
                      value={compareVersion.price}
                      renderValue={renderExecutionCompareValue}
                      onChange={(e) => handleExecutionCompareChange('price', e.target.value)}
                      className="ntq-exec-compare__select"
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
              {renderStepProgressOverlay('capital')}
              <Box
                className="ntq-exec-step-grid exec-step-card__body"
              >
                <Box className="ntq-exec-step-no">
                  3
                </Box>
                <Stack direction="row" spacing={1} alignItems="center" className="ntq-exec-step-title">
                  <Typography fontWeight={600} noWrap>资金模拟</Typography>
                  <IconButton
                    className="ntq-exec-step-run-btn"
                    onClick={() => runStep(STEP_CAPITAL)}
                    disabled={executionBusy}
                    aria-label={stepStatus.capital === 'done' ? '强制重跑资金模拟' : '运行资金模拟'}
                  >
                    <StepRunButtonIcon done={stepStatus.capital === 'done'} />
                  </IconButton>
                </Stack>
                {renderCapitalSummary()}
                {stepStatus.capital === 'done' && showVersionCompare ? (
                  <Stack direction="row" spacing={1} alignItems="center" justifyContent="flex-end" className="ntq-exec-compare">
                    <Select
                      size="small"
                      displayEmpty
                      value={compareVersion.capital}
                      renderValue={renderExecutionCompareValue}
                      onChange={(e) => handleExecutionCompareChange('capital', e.target.value)}
                      className="ntq-exec-compare__select"
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
