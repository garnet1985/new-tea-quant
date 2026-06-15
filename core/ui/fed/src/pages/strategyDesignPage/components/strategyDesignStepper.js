import React, { useCallback, useMemo } from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { getStrategyDesignPath } from '../../../api/apis/strategyApi';
import { STRATEGY_DESIGN_STEPS } from '../constants/strategyDesignSteps';
import { useStrategyDesignSession } from '../strategyDesignContext';
import { resolveStepperVisual } from '../lib/resolveStepperVisual';
import './strategyDesignStepper.scss';

const STEPPER_RING_PX = 56;
const EMPTY_OBJECT = {};

function StepperCircle({ step, visual, isLast, connectorDone = false }) {
  const ringPct = visual?.kind === 'running' ? visual.pct : 0;
  const stateClass = typeof visual === 'string' ? visual : visual?.kind || 'inactive-idle';

  return (
    <Box className={`ntq-design-stepper__item${isLast ? ' ntq-design-stepper__item--last' : ''}`}>
      {!isLast ? (
        <Box
          className={[
            'ntq-design-stepper__connector',
            connectorDone ? 'ntq-design-stepper__connector--done' : '',
          ].filter(Boolean).join(' ')}
          aria-hidden
        />
      ) : null}
      <Box
        className={[
          'ntq-design-stepper__step',
          `ntq-design-stepper__step--${stateClass}`,
        ].join(' ')}
      >
        <Box className="ntq-design-stepper__ring-wrap">
          {stateClass === 'running' ? (
            <CircularProgress
              variant="determinate"
              value={Math.min(100, Math.max(0, ringPct))}
              size={STEPPER_RING_PX}
              thickness={2}
              className="ntq-design-stepper__ring"
            />
          ) : null}
          {stateClass === 'pending' ? (
            <CircularProgress
              variant="indeterminate"
              size={STEPPER_RING_PX}
              thickness={2}
              className="ntq-design-stepper__ring ntq-design-stepper__ring--pending"
            />
          ) : null}
          <Box className="ntq-design-stepper__circle" component="span">
            <Typography component="span" className="ntq-design-stepper__num">
              {step.no}
            </Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  );
}

function StrategyDesignStepper() {
  const navigate = useNavigate();
  const { strategyName, session } = useStrategyDesignSession();
  const activeStep = session.activeStep;
  const stepStatus = session.executionState?.stepStatus ?? EMPTY_OBJECT;
  const stepProgress = session.stepProgress ?? EMPTY_OBJECT;
  const activeRunId = session.executionState?.activeRunId || '';

  const visuals = useMemo(() => (
    STRATEGY_DESIGN_STEPS.map((step) => ({
      key: step.key,
      visual: resolveStepperVisual(step.key, {
        activeStep,
        stepStatus,
        stepProgress,
        activeRunId,
      }),
    }))
  ), [activeStep, stepStatus, stepProgress, activeRunId]);

  const handleStepClick = useCallback((stepKey) => {
    if (!strategyName) return;
    navigate(getStrategyDesignPath(strategyName, stepKey));
  }, [navigate, strategyName]);

  const stepCount = STRATEGY_DESIGN_STEPS.length;

  return (
    <Box
      className="ntq-design-stepper"
      role="navigation"
      aria-label="制定策略步骤"
      style={{ '--ntq-stepper-count': stepCount }}
    >
      {STRATEGY_DESIGN_STEPS.map((step, idx) => {
        const visual = visuals.find((v) => v.key === step.key)?.visual || 'inactive-idle';
        return (
          <Box
            key={step.key}
            className="ntq-design-stepper__click"
            role="button"
            tabIndex={0}
            aria-label={step.label}
            title={step.label}
            onClick={() => handleStepClick(step.key)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handleStepClick(step.key);
              }
            }}
          >
            <StepperCircle
              step={step}
              visual={visual}
              isLast={idx === STRATEGY_DESIGN_STEPS.length - 1}
              connectorDone={
                idx < STRATEGY_DESIGN_STEPS.length - 1
                && stepStatus[STRATEGY_DESIGN_STEPS[idx + 1].key] === 'done'
              }
            />
          </Box>
        );
      })}
    </Box>
  );
}

export default StrategyDesignStepper;
