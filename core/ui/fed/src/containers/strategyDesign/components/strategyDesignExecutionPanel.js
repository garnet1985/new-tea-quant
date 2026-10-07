import React, { useCallback, useMemo } from 'react';
import { Box, LinearProgress, Tooltip, Typography } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { getStrategyDesignPath } from '../../../api/strategyApi';
import {
  STRATEGY_DESIGN_RUN_STEP_KEYS,
  STRATEGY_DESIGN_STEPS,
} from '../constants/strategyDesignSteps';
import { EXECUTION_PANEL_TITLE } from 'containers/strategyExecution';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';
import RainbowButton from 'views/rainbowButton';
import './strategyDesignExecutionPanel.scss';

const ATTRIBUTE_IDLE_TOOLTIP = '请先完成本层回测。需要在策略目录配置 attribution.py 才能开始归因。';

function resolveExecutionStatusCopy({
  activeStep,
  stepStatus,
  executionBusy,
  attributeBusy,
  runningStep,
  stepProgress,
  progressDetail,
  attributeProgressDetail,
  attributeProgressPct,
}) {
  const step = STRATEGY_DESIGN_STEPS.find((item) => item.key === activeStep);
  const stepLabel = step?.label || activeStep;

  if (attributeBusy) {
    const detailText = [
      attributeProgressDetail?.label,
      attributeProgressDetail?.stageLabel,
      attributeProgressDetail?.counterText,
    ].filter(Boolean).join(' · ');
    const pct = Math.min(100, Math.max(0, Math.round(Number(attributeProgressPct ?? 0))));
    return {
      primary: `正在归因「${stepLabel}」`,
      secondary: detailText || (pct > 0 ? `进度 ${pct}%` : '准备中…'),
      showProgress: true,
      progress: pct,
    };
  }

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
  const location = useLocation();
  const wb = useStrategyDesignWorkbenchContext();

  const prevStep = useMemo(() => {
    const idx = STRATEGY_DESIGN_STEPS.findIndex((step) => step.key === wb.activeStep);
    if (idx <= 0) return null;
    return STRATEGY_DESIGN_STEPS[idx - 1];
  }, [wb.activeStep]);

  const nextStep = useMemo(() => {
    const idx = STRATEGY_DESIGN_STEPS.findIndex((step) => step.key === wb.activeStep);
    if (idx < 0 || idx >= STRATEGY_DESIGN_STEPS.length - 1) return null;
    return STRATEGY_DESIGN_STEPS[idx + 1];
  }, [wb.activeStep]);

  const currentStepDone = wb.stepStatus?.[wb.activeStep] === 'done';
  const attributeDone = Boolean(wb.attributeLastGroupId || wb.attributeReport);
  const panelBusy = Boolean(wb.panelBusy);

  const statusCopy = useMemo(
    () => resolveExecutionStatusCopy({
      activeStep: wb.activeStep,
      stepStatus: wb.stepStatus,
      executionBusy: wb.executionBusy,
      attributeBusy: wb.attributeBusy,
      runningStep: wb.runningStep,
      stepProgress: wb.stepProgress,
      progressDetail: wb.progressDetail,
      attributeProgressDetail: wb.attributeProgressDetail,
      attributeProgressPct: wb.attributeProgressPct,
    }),
    [
      wb.activeStep,
      wb.attributeBusy,
      wb.attributeProgressDetail,
      wb.attributeProgressPct,
      wb.executionBusy,
      wb.progressDetail,
      wb.runningStep,
      wb.stepProgress,
      wb.stepStatus,
    ],
  );

  const handleGoPrevStep = useCallback(() => {
    if (!prevStep || !wb.strategyName || panelBusy) return;
    navigate(getStrategyDesignPath(wb.strategyName, prevStep.key), { state: location.state });
  }, [location.state, navigate, panelBusy, prevStep, wb.strategyName]);

  const handleGoNextStep = useCallback(() => {
    if (!nextStep || !wb.strategyName || !currentStepDone || panelBusy) return;
    navigate(getStrategyDesignPath(wb.strategyName, nextStep.key), { state: location.state });
  }, [currentStepDone, location.state, navigate, nextStep, panelBusy, wb.strategyName]);

  const panelTitle = useMemo(() => {
    const step = STRATEGY_DESIGN_STEPS.find((item) => item.key === wb.activeStep);
    const stepTitle = step?.executionPanelTitle || step?.label || '';
    return stepTitle ? `${EXECUTION_PANEL_TITLE} - ${stepTitle}` : EXECUTION_PANEL_TITLE;
  }, [wb.activeStep]);

  const showAttributeButton = STRATEGY_DESIGN_RUN_STEP_KEYS.has(wb.activeStep);
  const attributeHowTo = !wb.attributeEnabled
    ? (wb.attributeTooltip || ATTRIBUTE_IDLE_TOOLTIP)
    : '';
  const attributeButton = showAttributeButton ? (
    <RainbowButton
      shape="pill"
      icon={attributeDone ? 'refresh' : 'play'}
      shimmer
      disabled={wb.disableMetaActions || panelBusy || !wb.attributeEnabled}
      onClick={wb.handleAttributeRun}
      aria-label={attributeDone ? '重新归因' : '开始归因'}
      data-ntq-help="start-attribution"
    >
      {attributeDone ? '重新归因' : '开始归因'}
    </RainbowButton>
  ) : null;

  const attributeControl = attributeButton && attributeHowTo ? (
    <Tooltip title={attributeHowTo} placement="top">
      <span className="ntq-design-exec-panel__attr-tip-wrap">
        {attributeButton}
      </span>
    </Tooltip>
  ) : attributeButton;

  return (
    <Box className="ntq-design-exec-panel" data-ntq-help="design-execution">
      <Box className="ntq-design-exec-panel__title-row">
        <Typography variant="subtitle2" fontWeight={600} className="ntq-design-exec-panel__title">
          {panelTitle}
        </Typography>
      </Box>

      {wb.runError ? (
        <Typography variant="caption" color="error" className="ntq-design-exec-panel__error">
          {wb.runError}
        </Typography>
      ) : null}
      {wb.attrError ? (
        <Typography variant="caption" color="error" className="ntq-design-exec-panel__error">
          {wb.attrError}
        </Typography>
      ) : null}

      <Box className="ntq-design-exec-panel__body">
        <Box className="ntq-design-exec-panel__actions">
          <RainbowButton
            shape="pill"
            icon={currentStepDone ? 'refresh' : 'play'}
            shimmer
            disabled={wb.disableMetaActions || panelBusy}
            onClick={wb.handleRunCurrentStep}
            aria-label={currentStepDone ? '重新模拟' : '开始模拟'}
            data-ntq-help="start-simulation"
          >
            {currentStepDone ? '重新模拟' : '开始模拟'}
          </RainbowButton>
          {attributeControl}
          {prevStep ? (
            <RainbowButton
              shape="pill"
              ring="plain"
              disabled={wb.disableMetaActions || panelBusy}
              onClick={handleGoPrevStep}
            >
              上一步
            </RainbowButton>
          ) : null}
          {nextStep ? (
            <RainbowButton
              shape="pill"
              ring="plain"
              disabled={!currentStepDone || panelBusy}
              onClick={handleGoNextStep}
            >
              下一步
            </RainbowButton>
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
