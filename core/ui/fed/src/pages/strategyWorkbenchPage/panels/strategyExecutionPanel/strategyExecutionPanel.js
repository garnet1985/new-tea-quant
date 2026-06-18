import React, { useEffect, useMemo, useRef, useState } from 'react';
import NtqIcon from 'components/ntqIcon/ntqIcon';
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
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Pagination,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import LoadingBars from 'components/loadingBars/loadingBars';
import NtqHelpTooltip from 'components/ntqHelpTooltip/ntqHelpTooltip';
import NtqRainbowRunButton from 'components/ntqRainbowRunButton/ntqRainbowRunButton';
import SettingsAccordionTitle from 'components/settingsAccordionTitle/settingsAccordionTitle';
import './strategyExecutionPanel.scss';
import {
  EXECUTION_PANEL_TITLE,
  EXECUTION_PANEL_TOOLTIP,
  EXEC_STEP_CAPITAL_TOOLTIP,
  EXEC_STEP_ENUM_TOOLTIP,
  EXEC_STEP_PRICE_TOOLTIP,
} from './executionSectionMeta';
import {
  fetchStrategyRunStatus,
  fetchStrategyVersionDetail,
  startStrategyRun,
} from '../../../../api/apis/strategyApi';
import {
  buildExecutionResultFromExecutionPanel,
  mergeStepStatusFromRunProgress,
  stepStatusFromRunPlanSteps,
} from '../../workbenchExecutionHydration';
import { useWorkbenchCompareVersionMenu } from '../../workbenchCompareVersionMenu';
import { clearStockKlineMemoryCache } from '../strategyReportPanel/lib/stockKlineMemoryCache';

const STEP_ENUM = 'enum';
const STEP_PRICE = 'price';
const STEP_CAPITAL = 'capital';

const ACTIVE_RUN_STORAGE_PREFIX = 'ntq-workbench-active-run';

function activeRunStorageKey(strategyName) {
  return `${ACTIVE_RUN_STORAGE_PREFIX}:${String(strategyName || '').trim()}`;
}

function persistActiveRun(strategyName, { activeRunId, progressPollStep }) {
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
  } catch {
    /* ignore quota / private mode */
  }
}

function clearPersistedActiveRun(strategyName) {
  const sn = String(strategyName || '').trim();
  if (!sn) return;
  try {
    sessionStorage.removeItem(activeRunStorageKey(sn));
  } catch {
    /* ignore */
  }
}

function loadPersistedActiveRun(strategyName) {
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
  } catch {
    return null;
  }
}

/** 下拉末项：打开完整历史版本选择；勿写入 ``compareVersion`` */
const EXEC_COMPARE_MORE_MENU_VALUE = '__exec_compare_more_versions__';
const VERSION_PICKER_PAGE_SIZE = 8;

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

function ExecStepRunButton({ done, disabled, onClick, ariaLabel }) {
  return (
    <NtqRainbowRunButton
      done={done}
      disabled={disabled}
      onClick={onClick}
      ariaLabel={ariaLabel}
    />
  );
}

/** 序号 + 名称（间距略大）+ 圆形运行钮（紧贴名称） */
function ExecStepLeadBlock({
  stepNo,
  title,
  tooltip,
  done,
  disabled,
  onClick,
  ariaLabel,
}) {
  return (
    <Stack direction="row" spacing={2} alignItems="center" className="ntq-exec-step-lead">
      <Box className="ntq-exec-step-no">{stepNo}</Box>
      <Stack
        direction="row"
        spacing={0}
        alignItems="center"
        className="ntq-exec-step-lead-main"
      >
        <ExecutionStepTitle title={title} tooltip={tooltip} />
        <ExecStepRunButton
          done={done}
          disabled={disabled}
          onClick={onClick}
          ariaLabel={ariaLabel}
        />
      </Stack>
    </Stack>
  );
}

function ExecutionStepTitle({ title, tooltip }) {
  return (
    <Stack direction="row" spacing={0.75} alignItems="center" sx={{ minWidth: 0 }}>
      <Typography component="span" fontWeight={600} noWrap>
        {title}
      </Typography>
      {tooltip ? <NtqHelpTooltip title={tooltip} shine /> : null}
    </Stack>
  );
}

const EXEC_COMPARE_ROW_SX = {
  display: 'flex',
  alignItems: 'center',
  gap: 1,
  flexWrap: 'nowrap',
  minWidth: 0,
  overflowX: 'auto',
  overflowY: 'hidden',
  '&::-webkit-scrollbar': { height: 6 },
};

function ExecCompareDivider() {
  return <Box component="span" className="ntq-exec-compare-divider" aria-hidden />;
}

/** 仅标在对比版本数值后：相对当前版本更高 ↑ 绿、更低 ↓ 红 */
function ExecCompareDeltaArrow({ compareValue, baselineValue }) {
  if (!Number.isFinite(compareValue) || !Number.isFinite(baselineValue)) return null;
  if (compareValue === baselineValue) return null;
  const up = compareValue > baselineValue;
  return (
    <Typography
      component="span"
      variant="body2"
      sx={{
        ml: 0.35,
        color: up ? 'success.main' : 'error.main',
        fontWeight: 700,
        lineHeight: 1,
      }}
      aria-hidden
    >
      {up ? '↑' : '↓'}
    </Typography>
  );
}

function StrategyExecutionPanel({
  strategyName,
  settings,
  getSettingsForRun,
  onExecutionStateChange,
  /** 工作台版本列表中的最近 5 条 ``version_id``（与 GET …/versions 顺序一致，新→旧） */
  executionCompareRecentVersionIds = [],
  /** 完整工作台快照列表（与设置区「更多版本」同源） */
  configVersions = [],
  /** 单步 run 成功结束；用于报告 Tab 切到对应回测器 */
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
  const [stepProgress, setStepProgress] = useState({ enum: 0, price: 0, capital: 0 });
  const [progressDetail, setProgressDetail] = useState({
    label: '',
    stageLabel: '',
    counterText: '',
  });
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
  /** 打开「更多版本」时记录 enum / price / capital，选中后写入对应 ``compareVersion`` */
  const [executionMoreVersionsStepKey, setExecutionMoreVersionsStepKey] = useState('');
  const [versionSearch, setVersionSearch] = useState('');
  const [versionPickerPage, setVersionPickerPage] = useState(1);
  /** ``version_id`` → 该快照 ``execution_panel`` 解析后的执行摘要 */
  const [compareLinesByVersionId, setCompareLinesByVersionId] = useState({});
  const [activeRunId, setActiveRunId] = useState('');
  /** 与 V2-06 ``GET …/{step}/progress`` 路径一致；锁定为本次点击的 step，避免 ``runningStep`` 被状态推导清空后误用 ``enum`` 轮询导致 404 */
  const [progressPollStep, setProgressPollStep] = useState('');
  const [latestRunId, setLatestRunId] = useState('');
  const [runError, setRunError] = useState('');
  const [lastCompletedWorkbenchVersionId, setLastCompletedWorkbenchVersionId] = useState('');
  /** 同一 run + 同一 running 步内进度只增不减，避免轮询回退（如 5% → 2%） */
  const progressRunKeyRef = useRef('');
  const progressPctHighWaterRef = useRef(0);

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
    progressRunKeyRef.current = '';
    progressPctHighWaterRef.current = 0;
  }, [strategyName]);

  /** 刷新页面后恢复仍在后端的 run 轮询，避免 UI 假空闲或重复触发 */
  useEffect(() => {
    if (!strategyName || activeRunId) return undefined;

    const saved = loadPersistedActiveRun(strategyName);
    if (!saved?.activeRunId) return undefined;

    let cancelled = false;
    (async () => {
      try {
        const status = await fetchStrategyRunStatus(strategyName, saved.activeRunId);
        if (cancelled) return;
        if (status?.state === 'running') {
          const pollStep = saved.progressPollStep || status?.running_step || STEP_ENUM;
          setActiveRunId(saved.activeRunId);
          setLatestRunId(saved.activeRunId);
          setProgressPollStep(pollStep);
          setRunningStep(status?.running_step || pollStep);
          if (status?.step_status_merge && typeof status.step_status_merge === 'object') {
            setStepStatus((prev) => mergeStepStatusFromRunProgress(prev, status.step_status_merge));
          }
          if (status?.step_progress && typeof status.step_progress === 'object') {
            setStepProgress((prev) => ({ ...prev, ...status.step_progress }));
          }
          setProgressDetail({
            label: String(status?.progress_label || '').trim(),
            stageLabel: String(status?.progress_stage_label || '').trim(),
            counterText: String(status?.progress_counter_text || '').trim(),
          });
          const nextPct = Number(status?.progress_pct || 0);
          if (Number.isFinite(nextPct) && nextPct > 0) {
            setProgress(nextPct);
            progressPctHighWaterRef.current = nextPct;
          }
          return;
        }
        clearPersistedActiveRun(strategyName);
      } catch {
        if (!cancelled) clearPersistedActiveRun(strategyName);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [activeRunId, strategyName]);

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
    clearStockKlineMemoryCache();
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
      progressRunKeyRef.current = '';
      progressPctHighWaterRef.current = 0;
      setLastCompletedWorkbenchVersionId('');
      const resolvedSettings = getSettingsForRun ? getSettingsForRun() : settings;
      if (!resolvedSettings) throw new Error('当前参数不可用，无法执行');
      const started = await startStrategyRun(strategyName, target, resolvedSettings, { force_refresh: isForce });
      const runId = started?.run_id;
      if (!runId) throw new Error('启动执行失败：缺少 run_id');
      setActiveRunId(runId);
      setLatestRunId(runId);
      persistActiveRun(strategyName, { activeRunId: runId, progressPollStep: target });
      setRunningStep(started?.resolved_chain?.[0] || target);
      setProgress(0);
      const planSteps = Array.isArray(started?.steps) ? started.steps : [];
      setStepStatus((prev) => stepStatusFromRunPlanSteps(planSteps, prev));
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
    /* 本步正在重跑时勿画完成满条（且避免 done→running 复用同一节点触发 width 回退动画） */
    if (st === 'done') {
      if (activeRunId && progressPollStep === stepKey) return null;
      return (
        <Box
          key={`${stepKey}-done`}
          className="exec-step-card__progress exec-step-card__progress--done"
          style={{ width: '100%' }}
          aria-hidden
        />
      );
    }
    const visuallyRunning = st === 'running';
    if (!visuallyRunning) return null;
    if (progress > 0) {
      const raw = stepProgress[stepKey];
      const pct = Math.min(100, Math.max(0, Number(raw != null ? raw : progress)));
      return (
        <Box
          key={`${stepKey}-run-pct-${activeRunId || 'local'}`}
          className="exec-step-card__progress exec-step-card__progress--run"
          style={{ width: `${pct}%` }}
          aria-hidden
        />
      );
    }
    return (
      <Box
        key={`${stepKey}-run-indeterminate-${activeRunId || 'local'}`}
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

  /** 对比下拉仅在 done 时启用，但占位始终保留，避免完成瞬间行高跳变 */
  const renderCompareSlot = (stepKey) => {
    if (!showVersionCompare) return null;
    const compareDone = stepStatus[stepKey] === 'done';
    const selectProps = {
      size: 'small',
      displayEmpty: true,
      value: compareVersion[stepKey],
      renderValue: renderExecutionCompareValue,
      onChange: (e) => handleExecutionCompareChange(stepKey, e.target.value),
      className: 'ntq-exec-compare__select',
    };
    return (
      <Stack
        direction="row"
        spacing={1}
        alignItems="center"
        justifyContent="flex-end"
        className="ntq-exec-compare ntq-exec-compare-slot"
      >
        {compareDone ? (
          <Select {...selectProps}>
            <MenuItem value="">{compareBaselineMenuLabel}</MenuItem>
            {compareDropdownVersionIds.map((id) => (
              <MenuItem key={id} value={id}>{id}</MenuItem>
            ))}
            <MenuItem value={EXEC_COMPARE_MORE_MENU_VALUE}>更多版本…</MenuItem>
          </Select>
        ) : (
          <Box className="ntq-exec-compare__placeholder" aria-hidden />
        )}
      </Stack>
    );
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

  const executionComparePickerVersions = useMemo(() => {
    const cur = String(lastCompletedWorkbenchVersionId || '').trim();
    const rows = Array.isArray(configVersions) ? configVersions : [];
    if (!cur) return rows;
    return rows.filter((v) => v.id !== cur);
  }, [configVersions, lastCompletedWorkbenchVersionId]);

  const versionPickerFiltered = useMemo(() => {
    const keyword = versionSearch.trim().toLowerCase();
    if (!keyword) return executionComparePickerVersions;
    return executionComparePickerVersions.filter((version) => (
      version.id.toLowerCase().includes(keyword)
      || version.createdAt.toLowerCase().includes(keyword)
      || version.updatedAt.toLowerCase().includes(keyword)
    ));
  }, [executionComparePickerVersions, versionSearch]);

  const versionPickerTotalPages = Math.max(
    1,
    Math.ceil(versionPickerFiltered.length / VERSION_PICKER_PAGE_SIZE) || 1,
  );

  const versionPickerSlice = useMemo(() => {
    const page = Math.min(versionPickerPage, versionPickerTotalPages);
    const start = (page - 1) * VERSION_PICKER_PAGE_SIZE;
    return versionPickerFiltered.slice(start, start + VERSION_PICKER_PAGE_SIZE);
  }, [versionPickerFiltered, versionPickerPage, versionPickerTotalPages]);

  useEffect(() => {
    setVersionPickerPage(1);
  }, [versionSearch]);

  useEffect(() => {
    setVersionPickerPage((p) => Math.min(p, versionPickerTotalPages));
  }, [versionPickerTotalPages]);

  const openExecutionMoreVersions = (stepKey) => {
    setExecutionMoreVersionsStepKey(stepKey);
    setVersionSearch('');
    setVersionPickerPage(1);
    setExecutionMoreVersionsOpen(true);
  };

  const handleExecutionCompareChange = (stepKey, nextValue) => {
    if (nextValue === EXEC_COMPARE_MORE_MENU_VALUE) {
      window.setTimeout(() => openExecutionMoreVersions(stepKey), 0);
      return;
    }
    setCompareVersion((prev) => ({ ...prev, [stepKey]: nextValue }));
  };

  const handlePickExecutionCompareVersion = (versionId) => {
    const stepKey = executionMoreVersionsStepKey;
    if (stepKey && versionId) {
      setCompareVersion((prev) => ({ ...prev, [stepKey]: versionId }));
    }
    setExecutionMoreVersionsOpen(false);
    setExecutionMoreVersionsStepKey('');
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
          const execLine = buildExecutionResultFromExecutionPanel(res?.execution_panel);
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

    if (vid && loading) {
      return (
        <Box sx={EXEC_COMPARE_ROW_SX}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            机会总数：{Number.isFinite(currentOpportunities) ? `${currentOpportunities} 个` : '--'}
          </Typography>
          <ExecCompareDivider />
          <LoadingBars className="ntq-loading-bars--sm" barCount={4} aria-label="读取中" />
        </Box>
      );
    }

    if (vid && errMsg) {
      return (
        <Box sx={EXEC_COMPARE_ROW_SX}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            机会总数：{Number.isFinite(currentOpportunities) ? `${currentOpportunities} 个` : '--'}
          </Typography>
          <ExecCompareDivider />
          <Typography variant="body2" color="error">{errMsg}</Typography>
        </Box>
      );
    }

    if (vid && row?.execLine && !Number.isFinite(compareOpportunities)) {
      return (
        <Box sx={EXEC_COMPARE_ROW_SX}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            机会总数：{Number.isFinite(currentOpportunities) ? `${currentOpportunities} 个` : '--'}
          </Typography>
          <ExecCompareDivider />
          <Typography variant="body2" color="text.secondary">该快照无枚举摘要</Typography>
        </Box>
      );
    }

    if (Number.isFinite(currentOpportunities) && Number.isFinite(compareOpportunities)) {
      return (
        <Box sx={EXEC_COMPARE_ROW_SX}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            机会总数：{currentOpportunities} 个
          </Typography>
          <ExecCompareDivider />
          <Typography variant="body2" component="span" sx={{ fontWeight: 600 }}>
            机会总数：{compareOpportunities} 个
            <ExecCompareDeltaArrow
              compareValue={compareOpportunities}
              baselineValue={currentOpportunities}
            />
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

    if (vid && loading) {
      return (
        <Box sx={EXEC_COMPARE_ROW_SX}>
          <Typography variant="body2" sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
            {formatPriceLine(currentPrice)}
          </Typography>
          <ExecCompareDivider />
          <LoadingBars className="ntq-loading-bars--sm" barCount={4} aria-label="读取中" />
        </Box>
      );
    }

    if (vid && errMsg) {
      return (
        <Box sx={EXEC_COMPARE_ROW_SX}>
          <Typography variant="body2" sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
            {formatPriceLine(currentPrice)}
          </Typography>
          <ExecCompareDivider />
          <Typography variant="body2" color="error">{errMsg}</Typography>
        </Box>
      );
    }

    if (vid && row?.execLine && currentPrice && !comparePrice) {
      return (
        <Box sx={EXEC_COMPARE_ROW_SX}>
          <Typography variant="body2" sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
            {formatPriceLine(currentPrice)}
          </Typography>
          <ExecCompareDivider />
          <Typography variant="body2" color="text.secondary">该快照无价格回测摘要</Typography>
        </Box>
      );
    }

    if (currentPrice && comparePrice) {
      return (
        <Box sx={EXEC_COMPARE_ROW_SX}>
          <Typography variant="body2" sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
            {formatPriceLine(currentPrice)}
          </Typography>
          <ExecCompareDivider />
          <Typography variant="body2" component="span" sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
            {formatPriceLine(comparePrice)}
            <ExecCompareDeltaArrow
              compareValue={comparePrice.roi}
              baselineValue={currentPrice.roi}
            />
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
      ...EXEC_COMPARE_ROW_SX,
      alignItems: 'flex-start',
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
          <ExecCompareDivider />
          <LoadingBars className="ntq-loading-bars--sm" barCount={4} aria-label="读取中" />
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
          <ExecCompareDivider />
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
          <ExecCompareDivider />
          <Typography variant="body2" color="text.secondary">该快照无资金摘要</Typography>
        </Box>
      );
    }

    return (
      <Box sx={gridSx}>
        <Stack spacing={0.25}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            收益：{`${cur.profit >= 0 ? '+' : ''}${formatCapitalMoney(cur.profit)} (${formatCapitalPct(cur.retPct)}%)`}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {`${formatCapitalMoney(cur.initialCapital)} -> ${formatCapitalMoney(cur.endCapital)}`}
          </Typography>
        </Stack>

        <ExecCompareDivider />

        <Stack spacing={0.25}>
          <Typography variant="body2" component="span" sx={{ fontWeight: 600 }}>
            收益：{`${cmp.profit >= 0 ? '+' : ''}${formatCapitalMoney(cmp.profit)} (${formatCapitalPct(cmp.retPct)}%)`}
            <ExecCompareDeltaArrow compareValue={cmp.profit} baselineValue={cur.profit} />
          </Typography>
          <Typography variant="caption" color="text.secondary">
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
      setStepStatus((prev) => mergeStepStatusFromRunProgress(prev, patch));
      const nextRunningStep = status?.running_step || '';
      setRunningStep(nextRunningStep);
      if (status?.step_progress && typeof status.step_progress === 'object') {
        setStepProgress((prev) => ({ ...prev, ...status.step_progress }));
      }
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
      setProgress(nextPct);
      if (status?.state === 'done') {
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
        clearPersistedActiveRun(strategyName);
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
  }, [activeRunId, onRunStepComplete, progressPollStep, strategyName]);

  const startRunRef = useRef(startRun);
  startRunRef.current = startRun;

  useEffect(() => {
    if (!onRegisterForceHandlers) return undefined;
    onRegisterForceHandlers({
      forceEnum: () => startRunRef.current(STEP_ENUM, { isForce: true }),
    });
    return () => onRegisterForceHandlers(null);
  }, [onRegisterForceHandlers]);

  /** 该步已为完成态时点播放 = 强制重跑（与 V2-05 ``force_refresh`` 一致） */
  const runStep = (target) => {
    const st =
      target === STEP_ENUM ? stepStatus.enum
        : target === STEP_PRICE ? stepStatus.price
          : stepStatus.capital;
    const isForce = st === 'done';
    return startRun(target, { isForce });
  };

  const progressDetailText = [
    progressDetail.label,
    progressDetail.stageLabel,
    progressDetail.counterText,
  ].filter(Boolean).join(' · ');

  return (
    <>
    <Accordion defaultExpanded disableGutters>
      <AccordionSummary expandIcon={<NtqIcon name="expandMore" size={24} />}>
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          spacing={1}
          sx={{ width: '100%', minWidth: 0, pr: 0.5 }}
        >
          <SettingsAccordionTitle
            title={EXECUTION_PANEL_TITLE}
            tooltip={EXECUTION_PANEL_TOOLTIP}
            context={{ defaultTooltipShine: true }}
          />
          {activeRunId && progressDetailText ? (
            <Typography
              variant="caption"
              color="text.secondary"
              noWrap
              sx={{ flexShrink: 0, maxWidth: '48%', textAlign: 'right' }}
            >
              {progressDetailText}
            </Typography>
          ) : null}
        </Stack>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1.25}>
          {runError ? (
            <Typography variant="caption" color="error">{runError}</Typography>
          ) : null}

          <Stack spacing={1}>
            <Box
              className={[
                'exec-step-card',
                getStepClass(stepStatus.enum),
                showVersionCompare ? 'exec-step-card--has-compare' : '',
              ].filter(Boolean).join(' ')}
              sx={{
                border: 1,
                borderRadius: 1,
                p: 1.25,
                ...getStepSx(stepStatus.enum),
              }}
            >
              {renderStepProgressOverlay('enum')}
              <Box
                className="ntq-exec-step-grid exec-step-card__body"
              >
                <ExecStepLeadBlock
                  stepNo={1}
                  title="枚举机会"
                  tooltip={EXEC_STEP_ENUM_TOOLTIP}
                  done={stepStatus.enum === 'done'}
                  disabled={executionBusy}
                  onClick={() => runStep(STEP_ENUM)}
                  ariaLabel={stepStatus.enum === 'done' ? '强制重跑枚举' : '运行枚举'}
                />
                {renderEnumSummary()}
                {renderCompareSlot('enum')}
              </Box>
            </Box>

            <Box
              className={[
                'exec-step-card',
                getStepClass(stepStatus.price),
                showVersionCompare ? 'exec-step-card--has-compare' : '',
              ].filter(Boolean).join(' ')}
              sx={{
                border: 1,
                borderRadius: 1,
                p: 1.25,
                ...getStepSx(stepStatus.price),
              }}
            >
              {renderStepProgressOverlay('price')}
              <Box
                className="ntq-exec-step-grid exec-step-card__body"
              >
                <ExecStepLeadBlock
                  stepNo={2}
                  title="价格回测"
                  tooltip={EXEC_STEP_PRICE_TOOLTIP}
                  done={stepStatus.price === 'done'}
                  disabled={executionBusy}
                  onClick={() => runStep(STEP_PRICE)}
                  ariaLabel={stepStatus.price === 'done' ? '强制重跑价格回测' : '运行价格回测'}
                />
                <Box sx={{ overflowX: 'auto', overflowY: 'hidden', '&::-webkit-scrollbar': { height: 6 } }}>
                  {renderPriceSummary()}
                </Box>
                {renderCompareSlot('price')}
              </Box>
            </Box>

            <Box
              className={[
                'exec-step-card',
                getStepClass(stepStatus.capital),
                showVersionCompare ? 'exec-step-card--has-compare' : '',
              ].filter(Boolean).join(' ')}
              sx={{
                border: 1,
                borderRadius: 1,
                p: 1.25,
                ...getStepSx(stepStatus.capital),
              }}
            >
              {renderStepProgressOverlay('capital')}
              <Box
                className="ntq-exec-step-grid exec-step-card__body"
              >
                <ExecStepLeadBlock
                  stepNo={3}
                  title="资金模拟"
                  tooltip={EXEC_STEP_CAPITAL_TOOLTIP}
                  done={stepStatus.capital === 'done'}
                  disabled={executionBusy}
                  onClick={() => runStep(STEP_CAPITAL)}
                  ariaLabel={stepStatus.capital === 'done' ? '强制重跑资金模拟' : '运行资金模拟'}
                />
                {renderCapitalSummary()}
                {renderCompareSlot('capital')}
              </Box>
            </Box>
          </Stack>
        </Stack>
      </AccordionDetails>
    </Accordion>

    <Dialog
      open={executionMoreVersionsOpen}
      onClose={() => {
        setExecutionMoreVersionsOpen(false);
        setExecutionMoreVersionsStepKey('');
      }}
      maxWidth="xs"
      fullWidth
    >
      <DialogTitle>选择对比版本</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={1}>
          <TextField
            size="small"
            fullWidth
            placeholder="搜索版本 ID、创建或更新时间"
            value={versionSearch}
            onChange={(event) => setVersionSearch(event.target.value)}
          />
          <Typography variant="caption" color="text.secondary">
            {executionComparePickerVersions.length > 0
              ? `共 ${versionPickerFiltered.length} 条${versionPickerFiltered.length !== executionComparePickerVersions.length ? `（已筛选，可选 ${executionComparePickerVersions.length} 条）` : ''}`
              : '暂无可对比的历史版本'}
          </Typography>
          <List
            sx={{
              maxHeight: 340,
              overflow: 'auto',
              border: 1,
              borderColor: 'divider',
              borderRadius: 1,
            }}
          >
            {versionPickerSlice.length > 0 ? versionPickerSlice.map((version) => (
              <ListItemButton
                key={version.id}
                selected={version.id === compareVersion[executionMoreVersionsStepKey]}
                onClick={() => handlePickExecutionCompareVersion(version.id)}
              >
                <ListItemText
                  primary={version.id}
                  secondary={version.updatedAt || version.createdAt}
                />
              </ListItemButton>
            )) : (
              <Box sx={{ p: 1.5 }}>
                <Typography variant="body2" color="text.secondary">
                  {executionComparePickerVersions.length > 0
                    ? '没有匹配的版本。'
                    : '需要至少两条工作台快照才能对比；请先保存或运行生成新版本。'}
                </Typography>
              </Box>
            )}
          </List>
          {versionPickerFiltered.length > VERSION_PICKER_PAGE_SIZE ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', pt: 0.5 }}>
              <Pagination
                count={versionPickerTotalPages}
                page={Math.min(versionPickerPage, versionPickerTotalPages)}
                onChange={(_event, nextPage) => setVersionPickerPage(nextPage)}
                size="small"
                color="primary"
              />
            </Box>
          ) : null}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button
          onClick={() => {
            setExecutionMoreVersionsOpen(false);
            setExecutionMoreVersionsStepKey('');
          }}
        >
          关闭
        </Button>
      </DialogActions>
    </Dialog>
    </>
  );
}

export default StrategyExecutionPanel;
