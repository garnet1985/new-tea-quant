import React, { useCallback, useMemo } from 'react';
import { Box, Button, LinearProgress, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { getStrategyDesignPath } from '../../../api/apis/strategyApi';
import { STRATEGY_DESIGN_STEPS } from '../constants/strategyDesignSteps';
import { EXECUTION_PANEL_TITLE } from '../../strategyWorkbenchPage/panels/strategyExecutionPanel/executionSectionMeta';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';
import StrategyDesignSimulateButton from './strategyDesignSimulateButton';
import './strategyDesignExecutionPanel.scss';

function resolveExecutionStatusCopy({
  activeStep,
  stepStatus,
  executionBusy,
  runningStep,
  stepProgress,
  progressDetail,
}) {
  const step = STRATEGY_DESIGN_STEPS.find((item) => item.key === activeStep);
  const stepLabel = step?.label || activeStep;
  const status = stepStatus?.[activeStep] || 'idle';
  const pct = Math.min(100, Math.max(0, Math.round(Number(stepProgress?.[activeStep] ?? 0))));
  const isRunning = executionBusy
    && (status === 'running' || runningStep === activeStep || Boolean(runningStep));

  if (isRunning) {
    const detailText = [
      progressDetail?.label,
      progressDetail?.stageLabel,
      progressDetail?.counterText,
    ].filter(Boolean).join(' · ');
    const secondary = detailText || (pct > 0 ? `进度 ${pct}%` : '准备中…');
    return {
      primary: `正在执行「${stepLabel}」`,
      secondary,
      showProgress: true,
      progress: pct,
    };
  }

  if (status === 'done') {
    return {
      primary: `「${stepLabel}」已完成`,
      secondary: '可查看下方报告，或进入下一步',
      showProgress: false,
      progress: 0,
    };
  }

  return {
    primary: `当前步骤：${stepLabel}`,
    secondary: '点击左侧开始模拟运行本步回测',
    showProgress: false,
    progress: 0,
  };
}

function StrategyDesignExecutionPanel() {
  const navigate = useNavigate();
  const wb = useStrategyDesignWorkbenchContext();

  const nextStep = useMemo(() => {
    const idx = STRATEGY_DESIGN_STEPS.findIndex((step) => step.key === wb.activeStep);
    if (idx < 0 || idx >= STRATEGY_DESIGN_STEPS.length - 1) return null;
    return STRATEGY_DESIGN_STEPS[idx + 1];
  }, [wb.activeStep]);

  const currentStepDone = wb.stepStatus?.[wb.activeStep] === 'done';

  const statusCopy = useMemo(
    () => resolveExecutionStatusCopy({
      activeStep: wb.activeStep,
      stepStatus: wb.stepStatus,
      executionBusy: wb.executionBusy,
      runningStep: wb.runningStep,
      stepProgress: wb.stepProgress,
      progressDetail: wb.progressDetail,
    }),
    [
      wb.activeStep,
      wb.executionBusy,
      wb.progressDetail,
      wb.runningStep,
      wb.stepProgress,
      wb.stepStatus,
    ],
  );

  const handleGoNextStep = useCallback(() => {
    if (!nextStep || !wb.strategyName || !currentStepDone) return;
    navigate(getStrategyDesignPath(wb.strategyName, nextStep.key));
  }, [currentStepDone, navigate, nextStep, wb.strategyName]);

  return (
    <Box className="ntq-design-exec-panel">
      <Typography variant="subtitle2" fontWeight={600} className="ntq-design-exec-panel__title">
        {EXECUTION_PANEL_TITLE}
      </Typography>

      {wb.runError ? (
        <Typography variant="caption" color="error" className="ntq-design-exec-panel__error">
          {wb.runError}
        </Typography>
      ) : null}

      <Box className="ntq-design-exec-panel__body">
        <Box className="ntq-design-exec-panel__actions">
          <StrategyDesignSimulateButton
            done={currentStepDone}
            disabled={wb.disableMetaActions || wb.executionBusy}
            onClick={wb.handleRunCurrentStep}
            compact
          />
          {nextStep ? (
            <Button
              type="button"
              variant="outlined"
              size="small"
              className="ntq-design-exec-panel__next-btn"
              disabled={!currentStepDone}
              onClick={handleGoNextStep}
            >
              下一步
            </Button>
          ) : null}
        </Box>

        <Box className="ntq-design-exec-panel__status">
          <Typography variant="body2" className="ntq-design-exec-panel__status-primary">
            {statusCopy.primary}
          </Typography>
          <Typography variant="caption" color="text.secondary" className="ntq-design-exec-panel__status-secondary">
            {statusCopy.secondary}
          </Typography>
          <Box className="ntq-design-exec-panel__progress-slot" aria-hidden={!statusCopy.showProgress}>
            <LinearProgress
              variant={statusCopy.showProgress && statusCopy.progress > 0 ? 'determinate' : 'indeterminate'}
              value={statusCopy.showProgress ? statusCopy.progress : 0}
              className={[
                'ntq-design-exec-panel__progress',
                statusCopy.showProgress ? 'ntq-design-exec-panel__progress--visible' : '',
              ].filter(Boolean).join(' ')}
            />
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

export default StrategyDesignExecutionPanel;
