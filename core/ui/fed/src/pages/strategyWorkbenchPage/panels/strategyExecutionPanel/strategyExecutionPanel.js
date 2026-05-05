import React, { useEffect, useMemo, useState } from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  IconButton,
  MenuItem,
  LinearProgress,
  Select,
  Stack,
  Typography,
} from '@mui/material';
import { ReactComponent as PlayCircleIcon } from '../../../../assets/icon/play_circle.svg';
import { ReactComponent as DoneIcon } from '../../../../assets/icon/task_alt.svg';
import {
  MOCK_EXECUTION_COMPARE_SUMMARIES_BY_VERSION,
} from '../../mocks/strategyWorkbenchMocks';
import {
  fetchStrategyVersionHistory,
  fetchStrategyRunStatus,
  startStrategyRun,
} from '../../../../api/apis/strategyApi';

const STEP_ENUM = 'enum';
const STEP_PRICE = 'price';
const STEP_CAPITAL = 'capital';

function StrategyExecutionPanel({
  strategyName,
  settings,
  getSettingsForRun,
  onExecutionStateChange,
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
  const [compareOptions, setCompareOptions] = useState(['latest']);
  const [activeRunId, setActiveRunId] = useState('');
  const [latestRunId, setLatestRunId] = useState('');
  const [runError, setRunError] = useState('');

  useEffect(() => {
    if (!onExecutionStateChange) return;
    onExecutionStateChange({
      stepStatus,
      result,
      compareVersion,
      runningStep,
      runId: latestRunId,
      activeRunId,
    });
  }, [activeRunId, compareVersion, latestRunId, onExecutionStateChange, result, runningStep, stepStatus]);

  useEffect(() => {
    let disposed = false;
    if (!strategyName) {
      setCompareOptions(['latest']);
      return undefined;
    }
    const loadCompareOptions = async () => {
      try {
        const data = await fetchStrategyVersionHistory(strategyName);
        if (disposed) return;
        const options = Array.isArray(data?.versions)
          ? data.versions.filter((item) => typeof item === 'string' && item.trim() !== '')
          : [];
        setCompareOptions(options.length > 0 ? options : ['latest']);
      } catch (err) {
        if (disposed) return;
        setCompareOptions(['latest']);
      }
    };
    loadCompareOptions();
    return () => {
      disposed = true;
    };
  }, [strategyName]);

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
    setActiveRunId('');
    setLatestRunId('');
    setRunError('');
  }, [strategyName]);

  const isRunning = Boolean(runningStep);

  const runLabel = useMemo(() => {
    if (!runningStep) return '等待开始';
    if (runningStep === STEP_ENUM) return '正在执行：枚举机会';
    if (runningStep === STEP_PRICE) return '正在执行：价格回测';
    return '正在执行：资金模拟';
  }, [runningStep]);

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

  const renderStepDoneIcon = (step) => {
    if (stepStatus[step] !== 'done') return null;
    return (
      <DoneIcon
        width={16}
        height={16}
        style={{ color: 'var(--mui-palette-success-main)' }}
      />
    );
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

  const renderEnumSummary = () => {
    const currentOpportunities = result.enum?.opportunities;
    const compareOpportunities = compareVersion.enum
      ? MOCK_EXECUTION_COMPARE_SUMMARIES_BY_VERSION?.[compareVersion.enum]?.enum?.opportunities
      : null;

    if (Number.isFinite(currentOpportunities) && Number.isFinite(compareOpportunities)) {
      return (
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 1fr) auto minmax(0, 1fr)',
            alignItems: 'center',
            columnGap: 1,
          }}
        >
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
    const comparePrice = compareVersion.price
      ? MOCK_EXECUTION_COMPARE_SUMMARIES_BY_VERSION?.[compareVersion.price]?.price
      : null;

    if (currentPrice && comparePrice) {
      return (
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 1fr) auto minmax(0, 1fr)',
            alignItems: 'center',
            columnGap: 1,
          }}
        >
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
      if (status?.state === 'done' || status?.state === 'cancelled' || status?.state === 'failed') {
        setActiveRunId('');
        if (status?.state === 'failed') setRunError('执行失败，请检查后端日志。');
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
      }
    };

    poll();
    const timer = window.setInterval(poll, 800);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [activeRunId, strategyName]);

  const handleRun = async (target) => {
    if (isRunning || !strategyName) return;
    try {
      setRunError('');
      const resolvedSettings = getSettingsForRun ? getSettingsForRun() : settings;
      if (!resolvedSettings) throw new Error('当前参数不可用，无法执行');
      const started = await startStrategyRun(strategyName, target, resolvedSettings);
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
    }
  };

  return (
    <Accordion defaultExpanded disableGutters>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography fontWeight={600}>执行面板</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1.25}>
          <Typography variant="body2" color="text.secondary">
            三层执行依赖：价格回测和资金模拟依赖枚举机会；重跑枚举会使下游结果失效。
          </Typography>

          {isRunning ? (
            <Box>
              <Typography variant="caption" color="text.secondary">
                {runLabel}
              </Typography>
              <LinearProgress variant="determinate" value={progress} sx={{ mt: 0.5 }} />
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
                  {renderStepDoneIcon(STEP_ENUM)}
                  <IconButton size="small" onClick={() => handleRun(STEP_ENUM)} disabled={isRunning}>
                    <PlayCircleIcon width={18} height={18} />
                  </IconButton>
                </Stack>
                {renderEnumSummary()}
                {stepStatus.enum === 'done' ? (
                  <Stack direction="row" spacing={1} alignItems="center" justifyContent="flex-end">
                    <Typography variant="caption" color="text.secondary">对比版本</Typography>
                    <Select
                      size="small"
                      value={compareVersion.enum}
                      onChange={(e) => setCompareVersion((prev) => ({ ...prev, enum: e.target.value }))}
                      sx={{ minWidth: 120 }}
                    >
                      <MenuItem value="">不对比</MenuItem>
                      {compareOptions.map((v) => (
                        <MenuItem key={v} value={v}>{v}</MenuItem>
                      ))}
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
                  {renderStepDoneIcon(STEP_PRICE)}
                  <IconButton size="small" onClick={() => handleRun(STEP_PRICE)} disabled={isRunning}>
                    <PlayCircleIcon width={18} height={18} />
                  </IconButton>
                </Stack>
                <Box sx={{ overflowX: 'auto', overflowY: 'hidden', '&::-webkit-scrollbar': { height: 6 } }}>
                  {renderPriceSummary()}
                </Box>
                {stepStatus.price === 'done' ? (
                  <Stack direction="row" spacing={1} alignItems="center" justifyContent="flex-end">
                    <Typography variant="caption" color="text.secondary">对比版本</Typography>
                    <Select
                      size="small"
                      value={compareVersion.price}
                      onChange={(e) => setCompareVersion((prev) => ({ ...prev, price: e.target.value }))}
                      sx={{ minWidth: 120 }}
                    >
                      <MenuItem value="">不对比</MenuItem>
                      {compareOptions.map((v) => (
                        <MenuItem key={v} value={v}>{v}</MenuItem>
                      ))}
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
                  {renderStepDoneIcon(STEP_CAPITAL)}
                  <IconButton size="small" onClick={() => handleRun(STEP_CAPITAL)} disabled={isRunning}>
                    <PlayCircleIcon width={18} height={18} />
                  </IconButton>
                </Stack>
                {result.capital && compareVersion.capital ? (
                  <Box
                    sx={{
                      display: 'grid',
                      gridTemplateColumns: 'minmax(0, 1fr) auto minmax(0, 1fr)',
                      alignItems: 'start',
                      columnGap: 1,
                    }}
                  >
                    <Stack spacing={0.25}>
                      <Typography
                        variant="body2"
                        sx={{
                          color: getCurrentResultColor(
                            result.capital.profit,
                            MOCK_EXECUTION_COMPARE_SUMMARIES_BY_VERSION?.[compareVersion.capital]?.capital?.profit,
                          ),
                          fontWeight: 600,
                        }}
                      >
                        收益：{`${result.capital.profit >= 0 ? '+' : ''}${result.capital.profit.toLocaleString()} (${result.capital.retPct}%)`}
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{
                          color: getCurrentResultColor(
                            result.capital.endCapital,
                            MOCK_EXECUTION_COMPARE_SUMMARIES_BY_VERSION?.[compareVersion.capital]?.capital?.endCapital,
                          ),
                          fontWeight: 600,
                        }}
                      >
                        {`${result.capital.initialCapital.toLocaleString()} -> ${result.capital.endCapital.toLocaleString()}`}
                      </Typography>
                    </Stack>

                    <Stack justifyContent="center" alignItems="center" sx={{ height: '100%' }}>
                      <Typography variant="body2" color="text.secondary">-&gt;</Typography>
                    </Stack>

                    <Stack spacing={0.25}>
                      <Typography
                        variant="body2"
                        sx={{
                          color: getCompareResultColor(
                            MOCK_EXECUTION_COMPARE_SUMMARIES_BY_VERSION?.[compareVersion.capital]?.capital?.profit,
                            result.capital.profit,
                          ),
                          fontWeight: 600,
                        }}
                      >
                        (对比版本) 收益：{`${MOCK_EXECUTION_COMPARE_SUMMARIES_BY_VERSION?.[compareVersion.capital]?.capital?.profit >= 0 ? '+' : ''}${MOCK_EXECUTION_COMPARE_SUMMARIES_BY_VERSION?.[compareVersion.capital]?.capital?.profit?.toLocaleString() || '--'} (${MOCK_EXECUTION_COMPARE_SUMMARIES_BY_VERSION?.[compareVersion.capital]?.capital?.retPct ?? '--'}%)`}
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{
                          color: getCompareResultColor(
                            MOCK_EXECUTION_COMPARE_SUMMARIES_BY_VERSION?.[compareVersion.capital]?.capital?.endCapital,
                            result.capital.endCapital,
                          ),
                          fontWeight: 600,
                        }}
                      >
                        {`${MOCK_EXECUTION_COMPARE_SUMMARIES_BY_VERSION?.[compareVersion.capital]?.capital?.initialCapital?.toLocaleString() || '--'} -> ${MOCK_EXECUTION_COMPARE_SUMMARIES_BY_VERSION?.[compareVersion.capital]?.capital?.endCapital?.toLocaleString() || '--'}`}
                      </Typography>
                    </Stack>
                  </Box>
                ) : (
                  <Stack spacing={0.25}>
                    <Typography variant="body2">
                      收益：{result.capital ? `${result.capital.profit >= 0 ? '+' : ''}${result.capital.profit.toLocaleString()} (${result.capital.retPct}%)` : '--'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {result.capital ? `${result.capital.initialCapital.toLocaleString()} -> ${result.capital.endCapital.toLocaleString()}` : '--'}
                    </Typography>
                  </Stack>
                )}
                {stepStatus.capital === 'done' ? (
                  <Stack direction="row" spacing={1} alignItems="center" justifyContent="flex-end">
                    <Typography variant="caption" color="text.secondary">对比版本</Typography>
                    <Select
                      size="small"
                      value={compareVersion.capital}
                      onChange={(e) => setCompareVersion((prev) => ({ ...prev, capital: e.target.value }))}
                      sx={{ minWidth: 120 }}
                    >
                      <MenuItem value="">不对比</MenuItem>
                      {compareOptions.map((v) => (
                        <MenuItem key={v} value={v}>{v}</MenuItem>
                      ))}
                    </Select>
                  </Stack>
                ) : null}
              </Box>
            </Box>
          </Stack>
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}

export default StrategyExecutionPanel;
