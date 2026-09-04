import React, { useCallback, useMemo } from 'react';
import { Box, Button, LinearProgress, Typography } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import VersionPinToggle from 'components/versionPickLabel/versionPinToggle';
import { lookupVersionById } from 'components/versionPickLabel/versionPickMarks';
import { getStrategyDesignPath } from '../../../api/strategyApi';
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

  const handleGoPrevStep = useCallback(() => {
    if (!prevStep || !wb.strategyName || wb.executionBusy) return;
    navigate(getStrategyDesignPath(wb.strategyName, prevStep.key), { state: location.state });
  }, [location.state, navigate, prevStep, wb.executionBusy, wb.strategyName]);

  const handleGoNextStep = useCallback(() => {
    if (!nextStep || !wb.strategyName || !currentStepDone) return;
    navigate(getStrategyDesignPath(wb.strategyName, nextStep.key), { state: location.state });
  }, [currentStepDone, location.state, navigate, nextStep, wb.strategyName]);

  const panelTitle = useMemo(() => {
    const step = STRATEGY_DESIGN_STEPS.find((item) => item.key === wb.activeStep);
    const stepTitle = step?.executionPanelTitle || step?.label || '';
    return stepTitle ? `${EXECUTION_PANEL_TITLE} - ${stepTitle}` : EXECUTION_PANEL_TITLE;
  }, [wb.activeStep]);

  const currentVersion = lookupVersionById(wb.configVersions, wb.currentVersionDisplay);
  const showPinToggle = Boolean(wb.hasPersistedSnapshot && String(wb.currentVersionDisplay || '').startsWith('v'));

  return (
    <Box className="ntq-design-exec-panel">
      <Box className="ntq-design-exec-panel__title-row">
        <Typography variant="subtitle2" fontWeight={600} className="ntq-design-exec-panel__title">
          {panelTitle}
        </Typography>
        {showPinToggle ? (
          <VersionPinToggle
            version={{
              ...currentVersion,
              id: wb.currentVersionDisplay,
              pinned: wb.currentVersionPinned,
            }}
            versions={wb.configVersions}
            disabled={wb.disablePinActions}
            onToggle={wb.toggleVersionPinned}
            showLabel
          />
        ) : null}
      </Box>

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
          {prevStep ? (
            <Button
              type="button"
              variant="outlined"
              size="small"
              className="ntq-design-exec-panel__step-nav-btn"
              disabled={wb.disableMetaActions || wb.executionBusy}
              onClick={handleGoPrevStep}
            >
              上一步
            </Button>
          ) : null}
          {nextStep ? (
            <Button
              type="button"
              variant="outlined"
              size="small"
              className="ntq-design-exec-panel__step-nav-btn"
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
