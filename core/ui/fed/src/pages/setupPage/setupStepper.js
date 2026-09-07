import React from 'react';
import { Step, StepLabel, Stepper } from '@mui/material';

function SetupStepper({ definition, completedIds, activeStep }) {
  const completed = new Set(completedIds);
  return (
    <Stepper
      className="setup-page__stepper"
      activeStep={activeStep < 0 ? definition.length : activeStep}
      alternativeLabel
    >
      {definition.map((step) => (
        <Step key={step.id} completed={completed.has(step.id)}>
          <StepLabel>{step.name}</StepLabel>
        </Step>
      ))}
    </Stepper>
  );
}

export default React.memo(SetupStepper);
