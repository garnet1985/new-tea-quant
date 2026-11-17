import React, { useMemo } from 'react';
import { Stepper } from 'ui';
import './setupStepper.scss';

function SetupStepper({ definition, completedIds, activeStep }) {
  const completed = useMemo(() => new Set(completedIds), [completedIds]);
  const activeId = activeStep >= 0 && definition[activeStep]
    ? definition[activeStep].id
    : null;

  const items = useMemo(
    () => (definition || []).map((step, index) => {
      let status = 'idle';
      if (completed.has(step.id)) status = 'done';
      else if (index === activeStep) status = 'running';
      return {
        id: step.id,
        no: index + 1,
        label: step.name,
        status,
      };
    }),
    [activeStep, completed, definition],
  );

  return (
    <div
      className="setup-page__stepper"
      style={{ '--ntq-stepper-count': items.length || 1 }}
    >
      <Stepper
        className="setup-page__stepper-track"
        activeId={activeId}
        items={items}
        showProgress={false}
        aria-label="安装步骤"
      />
      <div className="setup-page__stepper-labels" aria-hidden="true">
        {items.map((item) => (
          <span key={item.id} className="setup-page__stepper-label">
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export default React.memo(SetupStepper);
