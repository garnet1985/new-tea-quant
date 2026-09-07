import {
  FAKE_PROGRESS_CAP,
  clampFakeProgress,
  fakeProgressTickSize,
  isChoicePauseStep,
  nextFakeProgress,
  setupFakeProgressBounds,
  setupStatusSignature,
  setupWeightedPercent,
} from './setup.helpers';

const STEPS = [
  { id: 'resolve_deps', progressWeight: 50 },
  { id: 'init_userspace', progressWeight: 8 },
  { id: 'db_connection', progressWeight: 8 },
  { id: 'import_data', progressWeight: 20 },
  { id: 'resolve_ml_deps', progressWeight: 14 },
];

describe('setup.helpers fake progress and choice steps', () => {
  it('identifies import and ML pause steps', () => {
    expect(isChoicePauseStep('import_data')).toBe(true);
    expect(isChoicePauseStep('resolve_ml_deps')).toBe(true);
    expect(isChoicePauseStep('db_connection')).toBe(false);
  });

  it('nudges percent toward the cap and then holds', () => {
    expect(nextFakeProgress(0, 90, 3)).toBe(3);
    expect(nextFakeProgress(88, 90, 3)).toBe(90);
    expect(nextFakeProgress(90, 90, 3)).toBe(90);
    expect(nextFakeProgress(FAKE_PROGRESS_CAP)).toBe(FAKE_PROGRESS_CAP);
  });

  it('keeps fake progress inside the current step weight slice', () => {
    const duringDeps = setupFakeProgressBounds(STEPS, {
      completedIds: [],
      runningStepId: 'resolve_deps',
    });
    expect(duringDeps.floorPercent).toBe(0);
    expect(duringDeps.stepEndPercent).toBe(50);
    expect(duringDeps.capPercent).toBe(45);

    const afterDeps = setupWeightedPercent(STEPS, { completedIds: ['resolve_deps'] });
    expect(afterDeps).toBe(50);

    const duringUserspace = setupFakeProgressBounds(STEPS, {
      completedIds: ['resolve_deps'],
      runningStepId: 'init_userspace',
    });
    expect(duringUserspace.floorPercent).toBe(50);
    expect(duringUserspace.capPercent).toBeCloseTo(57.2);
    expect(duringUserspace.capPercent).toBeLessThan(duringUserspace.stepEndPercent);
  });

  it('does not drop fake progress on small cap jitter', () => {
    expect(clampFakeProgress(45, { active: true, basePercent: 0, cap: 44.8 })).toBe(45);
    expect(clampFakeProgress(45, { active: true, basePercent: 50, cap: 57.2 })).toBe(50);
    expect(clampFakeProgress(52, { active: true, basePercent: 50, cap: 57.2 })).toBe(52);
    expect(clampFakeProgress(90, { active: true, basePercent: 50, cap: 57.2 })).toBe(57.2);
    expect(clampFakeProgress(52, { active: false, basePercent: 50, cap: 57.2 })).toBe(50);
  });

  it('treats unchanged step statuses as the same snapshot', () => {
    const a = {
      isReady: false,
      version: 3,
      stepStates: [
        { stepId: 'resolve_deps', status: 'running' },
        { stepId: 'init_userspace', status: 'not_started' },
      ],
    };
    const b = { ...a, version: 4 };
    expect(setupStatusSignature(a)).toBe(setupStatusSignature(b));
    expect(setupStatusSignature({ ...a, stepStates: [{ stepId: 'resolve_deps', status: 'success' }] }))
      .not.toBe(setupStatusSignature(a));
  });

  it('scales tick size with the current slice', () => {
    expect(fakeProgressTickSize(0, 45)).toBeCloseTo(0.8);
    expect(fakeProgressTickSize(50, 57.2)).toBeCloseTo(0.15);
  });
});
