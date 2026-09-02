import {
  fingerprintSignature,
  isFingerprintEqual,
  stableStringify,
} from './strategySettingsFingerprint';

describe('strategySettingsFingerprint', () => {
  it('stableStringify ignores object key order', () => {
    expect(stableStringify({ b: 1, a: 2 })).toBe(stableStringify({ a: 2, b: 1 }));
  });

  it('ignores non-fingerprint fields such as price_simulator', () => {
    const base = {
      core: { n: 1 },
      simulation: { execution: { mode: 'entity_based' } },
    };
    const withPrice = {
      ...base,
      price_simulator: { lookback: 20 },
      enumerator: { max_workers: 4 },
      meta: { name: 'x' },
    };
    expect(isFingerprintEqual(base, withPrice)).toBe(true);
  });

  it('detects fingerprint field changes', () => {
    const a = { core: { n: 1 }, goal: { take_profit: { stages: [] } } };
    const b = { core: { n: 2 }, goal: { take_profit: { stages: [] } } };
    expect(isFingerprintEqual(a, b)).toBe(false);
    expect(fingerprintSignature(a)).not.toBe(fingerprintSignature(b));
  });

  it('treats editor draft and freeze with empty nested simulation the same', () => {
    const draft = {
      core: { n: 1 },
      simulation: {
        execution: { mode: 'entity_based' },
        assumption: { tradability: { slippage: {} } },
      },
      enumerator: { max_workers: 4 },
    };
    const freeze = {
      core: { n: 1 },
      simulation: { execution: { mode: 'entity_based' } },
    };
    expect(isFingerprintEqual(draft, freeze)).toBe(true);
  });

  it('ignores UI draft keys such as force_exit_when_draft', () => {
    const freeze = {
      core: { n: 1 },
      simulation: { risk_control: { skip_enter_when: ['limit_up'] } },
    };
    const draft = {
      core: { n: 1 },
      simulation: {
        risk_control: {
          skip_enter_when: ['limit_up'],
          force_exit_when_draft: { status: 'x' },
        },
      },
    };
    expect(isFingerprintEqual(draft, freeze)).toBe(true);
  });
});
