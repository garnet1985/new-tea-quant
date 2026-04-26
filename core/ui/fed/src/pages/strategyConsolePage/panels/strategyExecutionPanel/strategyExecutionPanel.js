import React, { useMemo, useState } from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Chip,
  LinearProgress,
  Stack,
  Typography,
} from '@mui/material';

const STEP_ENUM = 'enum';
const STEP_PRICE = 'price';
const STEP_CAPITAL = 'capital';

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function formatStatusLabel(status) {
  if (status === 'running') return '执行中';
  if (status === 'done') return '已完成';
  return '未开始';
}

function formatStatusColor(status) {
  if (status === 'running') return 'warning';
  if (status === 'done') return 'success';
  return 'default';
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

function StrategyExecutionPanel({ settings }) {
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

  const isRunning = Boolean(runningStep);

  const runLabel = useMemo(() => {
    if (!runningStep) return '等待开始';
    if (runningStep === STEP_ENUM) return '正在执行：枚举机会';
    if (runningStep === STEP_PRICE) return '正在执行：价格回测';
    return '正在执行：资金模拟';
  }, [runningStep]);

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
            <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1 }}>
              <Stack direction="row" alignItems="center" justifyContent="space-between">
                <Typography fontWeight={600}>1. 枚举机会</Typography>
                <Chip size="small" label={formatStatusLabel(stepStatus.enum)} color={formatStatusColor(stepStatus.enum)} />
              </Stack>
              <Typography variant="body2" sx={{ mt: 0.75 }}>
                机会总数：{result.enum ? `${result.enum.opportunities} 个` : '--'}
              </Typography>
              <Button size="small" variant="outlined" sx={{ mt: 1 }} onClick={() => handleRun(STEP_ENUM)} disabled={isRunning}>
                运行枚举
              </Button>
            </Box>

            <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1 }}>
              <Stack direction="row" alignItems="center" justifyContent="space-between">
                <Typography fontWeight={600}>2. 价格回测</Typography>
                <Chip size="small" label={formatStatusLabel(stepStatus.price)} color={formatStatusColor(stepStatus.price)} />
              </Stack>
              <Typography variant="body2" sx={{ mt: 0.75 }}>
                胜率：{result.price ? `${result.price.winRate}%` : '--'} · ROI：{result.price ? `${result.price.roi}%` : '--'} · 平均持有：{result.price ? `${result.price.avgHoldDays} 天` : '--'}
              </Typography>
              <Button size="small" variant="outlined" sx={{ mt: 1 }} onClick={() => handleRun(STEP_PRICE)} disabled={isRunning}>
                运行价格回测
              </Button>
            </Box>

            <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1 }}>
              <Stack direction="row" alignItems="center" justifyContent="space-between">
                <Typography fontWeight={600}>3. 资金模拟</Typography>
                <Chip size="small" label={formatStatusLabel(stepStatus.capital)} color={formatStatusColor(stepStatus.capital)} />
              </Stack>
              <Typography variant="body2" sx={{ mt: 0.75 }}>
                收益率：{result.capital ? `${result.capital.retPct}%` : '--'} · 收益：{result.capital ? `${result.capital.profit >= 0 ? '+' : ''}${result.capital.profit.toLocaleString()}` : '--'} · 资金：{result.capital ? `${result.capital.initialCapital.toLocaleString()} -> ${result.capital.endCapital.toLocaleString()}` : '--'}
              </Typography>
              <Button size="small" variant="outlined" sx={{ mt: 1 }} onClick={() => handleRun(STEP_CAPITAL)} disabled={isRunning}>
                运行资金模拟
              </Button>
            </Box>
          </Stack>
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}

export default StrategyExecutionPanel;
