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

const STEP_ENUM = 'enum';
const STEP_PRICE = 'price';
const STEP_CAPITAL = 'capital';

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function getRunChain(target, stepStatus) {
  if (target === STEP_ENUM) return [STEP_ENUM];
  if (stepStatus.enum === 'done') return [target];
  return [STEP_ENUM, target];
}

function simulateEnumResult(settings) {
  const base = Number(settings?.sampling?.sampling_amount || 10);
  return {
    opportunities: Math.max(1, Math.round(base * (4 + Math.random() * 5))),
  };
}

function simulatePriceResult() {
  const winRate = Number((40 + Math.random() * 40).toFixed(1));
  const roi = Number((Math.random() * 50 - 10).toFixed(1));
  const avgHoldDays = Number((5 + Math.random() * 25).toFixed(1));
  return { winRate, roi, avgHoldDays };
}

function simulateCapitalResult(settings) {
  const initialCapital = Number(settings?.capital_simulator?.initial_capital || 1000000);
  const retPct = Number((Math.random() * 40 - 8).toFixed(1));
  const endCapital = Math.round(initialCapital * (1 + retPct / 100));
  const profit = endCapital - initialCapital;
  return { initialCapital, endCapital, profit, retPct };
}

const mockCompareSummaries = {
  latest: {
    enum: { opportunities: 100 },
    price: { winRate: 56.2, roi: 18.4 },
    capital: { initialCapital: 1000000, endCapital: 1031800, profit: 31800, retPct: 31.8 },
  },
  v3: {
    enum: { opportunities: 108 },
    price: { winRate: 52.8, roi: 12.6 },
    capital: { initialCapital: 1000000, endCapital: 1065000, profit: 65000, retPct: 6.5 },
  },
  v2: {
    enum: { opportunities: 103 },
    price: { winRate: 49.6, roi: 9.3 },
    capital: { initialCapital: 1000000, endCapital: 1042000, profit: 42000, retPct: 4.2 },
  },
  v1: {
    enum: { opportunities: 115 },
    price: { winRate: 44.1, roi: 6.7 },
    capital: { initialCapital: 1000000, endCapital: 1020000, profit: 20000, retPct: 2.0 },
  },
};

function StrategyExecutionPanel({ settings, onExecutionStateChange }) {
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

  useEffect(() => {
    if (!onExecutionStateChange) return;
    onExecutionStateChange({ stepStatus, result, compareVersion, runningStep });
  }, [compareVersion, onExecutionStateChange, result, runningStep, stepStatus]);

  const isRunning = Boolean(runningStep);

  const runLabel = useMemo(() => {
    if (!runningStep) return '等待开始';
    if (runningStep === STEP_ENUM) return '正在执行：枚举机会';
    if (runningStep === STEP_PRICE) return '正在执行：价格回测';
    return '正在执行：资金模拟';
  }, [runningStep]);

  const getStepClass = (status) => {
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
      ? mockCompareSummaries?.[compareVersion.enum]?.enum?.opportunities
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
      ? mockCompareSummaries?.[compareVersion.price]?.price
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

  const runStep = async (step) => {
    setRunningStep(step);
    setStepStatus((prev) => ({ ...prev, [step]: 'running' }));
    setProgress(0);

    await wait(200);
    setProgress(25);
    await wait(220);
    setProgress(60);
    await wait(240);
    setProgress(100);
    await wait(120);

    if (step === STEP_ENUM) {
      setResult((prev) => ({
        ...prev,
        enum: simulateEnumResult(settings),
        // 重新跑枚举会使下游两层结果失效
        price: null,
        capital: null,
      }));
      setStepStatus({
        enum: 'done',
        price: 'idle',
        capital: 'idle',
      });
    } else if (step === STEP_PRICE) {
      setResult((prev) => ({ ...prev, price: simulatePriceResult() }));
      setStepStatus((prev) => ({ ...prev, price: 'done' }));
    } else if (step === STEP_CAPITAL) {
      setResult((prev) => ({ ...prev, capital: simulateCapitalResult(settings) }));
      setStepStatus((prev) => ({ ...prev, capital: 'done' }));
    }

    setRunningStep('');
    setProgress(0);
  };

  const handleRun = async (target) => {
    if (isRunning) return;
    const chain = getRunChain(target, stepStatus);
    for (let i = 0; i < chain.length; i += 1) {
      // eslint-disable-next-line no-await-in-loop
      await runStep(chain[i]);
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
                      <MenuItem value="latest">latest</MenuItem>
                      <MenuItem value="v3">v3</MenuItem>
                      <MenuItem value="v2">v2</MenuItem>
                      <MenuItem value="v1">v1</MenuItem>
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
                      <MenuItem value="latest">latest</MenuItem>
                      <MenuItem value="v3">v3</MenuItem>
                      <MenuItem value="v2">v2</MenuItem>
                      <MenuItem value="v1">v1</MenuItem>
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
                            mockCompareSummaries?.[compareVersion.capital]?.capital?.profit,
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
                            mockCompareSummaries?.[compareVersion.capital]?.capital?.endCapital,
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
                            mockCompareSummaries?.[compareVersion.capital]?.capital?.profit,
                            result.capital.profit,
                          ),
                          fontWeight: 600,
                        }}
                      >
                        (对比版本) 收益：{`${mockCompareSummaries?.[compareVersion.capital]?.capital?.profit >= 0 ? '+' : ''}${mockCompareSummaries?.[compareVersion.capital]?.capital?.profit?.toLocaleString() || '--'} (${mockCompareSummaries?.[compareVersion.capital]?.capital?.retPct ?? '--'}%)`}
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{
                          color: getCompareResultColor(
                            mockCompareSummaries?.[compareVersion.capital]?.capital?.endCapital,
                            result.capital.endCapital,
                          ),
                          fontWeight: 600,
                        }}
                      >
                        {`${mockCompareSummaries?.[compareVersion.capital]?.capital?.initialCapital?.toLocaleString() || '--'} -> ${mockCompareSummaries?.[compareVersion.capital]?.capital?.endCapital?.toLocaleString() || '--'}`}
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
                      <MenuItem value="latest">latest</MenuItem>
                      <MenuItem value="v3">v3</MenuItem>
                      <MenuItem value="v2">v2</MenuItem>
                      <MenuItem value="v1">v1</MenuItem>
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
