import {
  FAKE_PROGRESS_CAP,
  IMPORT_DOWNLOAD_WITHIN_SHARE,
  SETUP_CHOICE_COPY,
  clampFakeProgress,
  demoPackageHintFromStatus,
  fakeProgressTickSize,
  importWithinStepRatio,
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
  it('offers demo import vs later member pack on the import pause', () => {
    const copy = SETUP_CHOICE_COPY.import_data;
    expect(copy.layout).toBe('cards');
    expect(copy.introLinkLabel).toBe('注册会员');
    expect(copy.introAfterLink).toContain('设置 → 安装与维护');
    expect(copy.choices.map((item) => item.id)).toEqual(['demo', 'later']);
    expect(copy.choices[0].skip).toBe(false);
    expect(copy.choices[1].skip).toBe(true);
    expect(copy.choices[0].description).toContain('300');
    expect(copy.choices[1].description).toContain('5800');
  });

  it('identifies import and ML pause steps', () => {
    expect(isChoicePauseStep('import_data')).toBe(true);
    expect(isChoicePauseStep('resolve_ml_deps')).toBe(true);
    expect(isChoicePauseStep('db_connection')).toBe(false);
  });

  it('explains whether a local demo package is already cached', () => {
    expect(demoPackageHintFromStatus(null)).toBe('');
    expect(demoPackageHintFromStatus({
      dataPackages: { packages: { demo: { present: true, sizeLabel: '120 MB' } } },
    })).toContain('本地已有');
    expect(demoPackageHintFromStatus({
      dataPackages: { packages: { demo: { present: false } } },
    })).toContain('尚无');
  });

  it('maps download into a small slice so table import can continue without falling back', () => {
    expect(importWithinStepRatio({
      running: true,
      phase: 'downloading',
      ratio: 1,
      totalBytes: 100,
    })).toBeCloseTo(IMPORT_DOWNLOAD_WITHIN_SHARE);
    expect(importWithinStepRatio({
      running: true,
      phase: 'preparing',
      ratio: 0,
    })).toBe(0);
    expect(importWithinStepRatio({
      running: true,
      phase: 'importing',
      ratio: 0,
      totalTables: 10,
    })).toBeCloseTo(IMPORT_DOWNLOAD_WITHIN_SHARE);
    expect(importWithinStepRatio({
      running: true,
      phase: 'importing',
      ratio: 1,
      totalTables: 10,
    })).toBeCloseTo(1);
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
