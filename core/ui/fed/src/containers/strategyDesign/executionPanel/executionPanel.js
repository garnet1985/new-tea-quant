import React, { useCallback, useMemo } from 'react';
import { Message, ProgressBar } from 'ui';
import { RainbowButton } from 'ntq-ui';
import { useLocation, useNavigate } from 'react-router-dom';
import { getStrategyDesignPath } from '../../../api/strategyApi';
import {
  STRATEGY_DESIGN_RUN_STEP_KEYS,
  STRATEGY_DESIGN_STEPS,
} from '../constants/strategyDesignSteps';
import { EXECUTION_PANEL_TITLE } from 'containers/strategyExecution';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';
import './style.scss';

const ATTRIBUTE_IDLE_TOOLTIP = '请先完成本层回测。需要在策略目录配置 attribution.py 才能开始归因。';
const ROLLING_IDLE_TOOLTIP = '请先完成机会盘点、价格回测与投资模拟。需要在策略目录配置 rolling.py 才能开始滚动对照。';

function disabledTip(button, howTo) {
  if (!button || !howTo) return button;
  return (
    <span className="ntq-design-exec-panel__attr-tip-wrap" title={howTo}>
      {button}
    </span>
  );
}

function resolveExecutionStatusCopy({
  activeStep,
  stepStatus,
  executionBusy,
  attributeBusy,
  rollingBusy,
  runningStep,
  stepProgress,
  progressDetail,
  attributeProgressDetail,
  attributeProgressPct,
  rollingProgressDetail,
  rollingProgressPct,
}) {
  const step = STRATEGY_DESIGN_STEPS.find((item) => item.key === activeStep);
  const stepLabel = step?.label || activeStep;

  if (rollingBusy) {
    const detailText = [
      rollingProgressDetail?.label,
      rollingProgressDetail?.stageLabel,
      rollingProgressDetail?.counterText,
    ].filter(Boolean).join(' · ');
    const pct = Math.min(100, Math.max(0, Math.round(Number(rollingProgressPct ?? 0))));
    return {
      primary: '正在滚动对照',
      secondary: detailText || (pct > 0 ? `进度 ${pct}%` : '准备中…'),
      showProgress: true,
      progress: pct,
    };
  }

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
    secondary: '点击左侧「开始模拟」运行本步回测',
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
  const rollingDone = Boolean(wb.rollingHasReport);
  const panelBusy = Boolean(wb.panelBusy);

  const statusCopy = useMemo(
    () => resolveExecutionStatusCopy({
      activeStep: wb.activeStep,
      stepStatus: wb.stepStatus,
      executionBusy: wb.executionBusy,
      attributeBusy: wb.attributeBusy,
      rollingBusy: wb.rollingBusy,
      runningStep: wb.runningStep,
      stepProgress: wb.stepProgress,
      progressDetail: wb.progressDetail,
      attributeProgressDetail: wb.attributeProgressDetail,
      attributeProgressPct: wb.attributeProgressPct,
      rollingProgressDetail: wb.rollingProgressDetail,
      rollingProgressPct: wb.rollingProgressPct,
    }),
    [
      wb.activeStep,
      wb.attributeBusy,
      wb.attributeProgressDetail,
      wb.attributeProgressPct,
      wb.executionBusy,
      wb.progressDetail,
      wb.rollingBusy,
      wb.rollingProgressDetail,
      wb.rollingProgressPct,
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

  const attributeControl = disabledTip(attributeButton, attributeHowTo);

  const showRollingButton = wb.activeStep === 'portfolio';
  const rollingHowTo = !wb.rollingEnabled
    ? (wb.rollingTooltip || ROLLING_IDLE_TOOLTIP)
    : '';
  const rollingButton = showRollingButton ? (
    <RainbowButton
      shape="pill"
      icon={rollingDone ? 'refresh' : 'play'}
      shimmer
      disabled={wb.disableMetaActions || panelBusy || !wb.rollingEnabled}
      onClick={wb.handleRollingRun}
      aria-label={rollingDone ? '重新滚动对照' : '开始滚动对照'}
      data-ntq-help="start-rolling"
    >
      {rollingDone ? '重新滚动对照' : '开始滚动对照'}
    </RainbowButton>
  ) : null;
  const rollingControl = disabledTip(rollingButton, rollingHowTo);

  const progressValue = statusCopy.showProgress
    ? (statusCopy.progress > 0 ? statusCopy.progress : null)
    : null;

  return (
    <section className="ntq-design-exec-panel" data-ntq-help="design-execution">
      <div className="ntq-design-exec-panel__title-row">
        <h3 className="ntq-design-exec-panel__title">{panelTitle}</h3>
      </div>

      {wb.runError ? (
        <Message status="error" className="ntq-design-exec-panel__error">{wb.runError}</Message>
      ) : null}
      {wb.attrError ? (
        <Message status="error" className="ntq-design-exec-panel__error">{wb.attrError}</Message>
      ) : null}
      {wb.rollingError ? (
        <Message status="error" className="ntq-design-exec-panel__error">{wb.rollingError}</Message>
      ) : null}

      <div className="ntq-design-exec-panel__body">
        <div className="ntq-design-exec-panel__actions">
          <RainbowButton
            shape="pill"
            icon={currentStepDone || wb.executionBusy ? 'refresh' : 'play'}
            shimmer
            disabled={
              wb.disableMetaActions
              || wb.attributeBusy
              || wb.rollingBusy
              || (panelBusy && !wb.executionBusy)
            }
            onClick={wb.handleRunCurrentStep}
            aria-label={
              wb.executionBusy
                ? '加入队列'
                : (currentStepDone ? '重新模拟' : '开始模拟')
            }
            data-ntq-help="start-simulation"
          >
            {wb.executionBusy
              ? '加入队列'
              : (currentStepDone ? '重新模拟' : '开始模拟')}
          </RainbowButton>
          {attributeControl}
          {rollingControl}
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
        </div>

        <div className="ntq-design-exec-panel__status">
          <div className="ntq-design-exec-panel__status-primary">
            {statusCopy.primary}
          </div>
          <div className="ntq-muted ntq-design-exec-panel__status-secondary">
            {statusCopy.secondary}
          </div>
          <div
            className="ntq-design-exec-panel__progress-slot"
            aria-hidden={!statusCopy.showProgress}
          >
            <ProgressBar
              size="sm"
              value={progressValue}
              className={[
                'ntq-design-exec-panel__progress',
                statusCopy.showProgress ? 'ntq-design-exec-panel__progress--visible' : '',
              ].filter(Boolean).join(' ')}
              aria-label="执行进度"
            />
          </div>
        </div>
      </div>
    </section>
  );
}

export default StrategyDesignExecutionPanel;
