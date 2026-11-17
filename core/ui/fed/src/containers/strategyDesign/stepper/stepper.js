import React, { useCallback, useMemo } from 'react';
import { Stepper } from 'ui';
import { useLocation, useNavigate } from 'react-router-dom';
import { getStrategyDesignPath } from '../../../api/strategyApi';
import { STRATEGY_DESIGN_STEPS } from '../constants/strategyDesignSteps';
import { useStrategyDesignSession } from '../strategyDesignContext';
import './style.scss';

const EMPTY_OBJECT = {};

function mapStepStatus(raw, activeRunId) {
  const st = String(raw || 'idle');
  if (st === 'pending' && !activeRunId) return 'idle';
  if (st === 'failed' || st === 'running' || st === 'pending' || st === 'done') {
    return st;
  }
  return 'idle';
}

function StrategyDesignStepper() {
  const navigate = useNavigate();
  const location = useLocation();
  const { strategyName, session } = useStrategyDesignSession();
  const activeStep = session.activeStep;
  const stepStatus = session.executionState?.stepStatus ?? EMPTY_OBJECT;
  const stepProgress = session.stepProgress ?? EMPTY_OBJECT;
  const activeRunId = session.executionState?.activeRunId || '';

  const handleStepClick = useCallback((stepKey) => {
    if (!strategyName || !stepKey) return;
    navigate(getStrategyDesignPath(strategyName, stepKey), { state: location.state });
  }, [location.state, navigate, strategyName]);

  const items = useMemo(() => (
    STRATEGY_DESIGN_STEPS.map((step) => {
      const status = mapStepStatus(stepStatus[step.key], activeRunId);
      const pct = Number(stepProgress[step.key]);
      return {
        id: step.key,
        no: step.no,
        label: step.label,
        status,
        progress: Number.isFinite(pct) ? pct : 0,
        onClick: () => handleStepClick(step.key),
      };
    })
  ), [activeRunId, handleStepClick, stepProgress, stepStatus]);

  return (
    <Stepper
      className="ntq-design-stepper"
      activeId={activeStep}
      items={items}
      aria-label="制定策略步骤"
    />
  );
}

export default StrategyDesignStepper;
