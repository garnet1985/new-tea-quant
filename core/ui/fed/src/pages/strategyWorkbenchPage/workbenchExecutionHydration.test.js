import {
  mergeHydratedStepStatus,
  mergeStepStatusFromRunProgress,
  mapWorkbenchStepStatusToExecutionCards,
  resetDownstreamStepStatus,
  stepStatusFromRunPlanSteps,
} from './workbenchExecutionHydration';

describe('mergeHydratedStepStatus', () => {
  it('uses snapshot hydration when version changes', () => {
    expect(mergeHydratedStepStatus(
      { enum: 'done', price: 'done', portfolio: 'done' },
      { enum: 'done', price: 'idle', portfolio: 'idle' },
      { versionChanged: true },
    )).toEqual({ enum: 'done', price: 'idle', portfolio: 'idle' });
  });

  it('applies D18 idle downgrade on the same version', () => {
    expect(mergeHydratedStepStatus(
      { enum: 'done', price: 'done', portfolio: 'done' },
      { enum: 'done', price: 'idle', portfolio: 'idle' },
      { versionChanged: false },
    )).toEqual({ enum: 'done', price: 'idle', portfolio: 'idle' });
  });
});

describe('resetDownstreamStepStatus', () => {
  it('idles price and portfolio when re-running enum', () => {
    expect(resetDownstreamStepStatus(
      { enum: 'done', price: 'done', portfolio: 'done' },
      'enum',
    )).toEqual({ enum: 'running', price: 'idle', portfolio: 'idle' });
  });
});

describe('stepStatusFromRunPlanSteps', () => {
  it('idles downstream of the running planned step', () => {
    expect(stepStatusFromRunPlanSteps(
      [{ step_name: 'enum', status: 'running' }],
      { enum: 'done', price: 'done', portfolio: 'done' },
    )).toEqual({ enum: 'running', price: 'idle', portfolio: 'idle' });
  });
});

describe('mergeStepStatusFromRunProgress', () => {
  it('does not let an idle poll overwrite a completed step', () => {
    expect(mergeStepStatusFromRunProgress(
      { enum: 'done', price: 'done', portfolio: 'idle' },
      { price: 'idle', portfolio: 'running' },
    )).toEqual({ enum: 'done', price: 'done', portfolio: 'running' });
  });
});

describe('mapWorkbenchStepStatusToExecutionCards', () => {
  it('treats price and price_factor as the same slot', () => {
    expect(mapWorkbenchStepStatusToExecutionCards({
      enum: { done: true },
      price: { done: true },
      portfolio: { done: false },
    })).toEqual({ enum: 'done', price: 'done', portfolio: 'idle' });
  });
});
