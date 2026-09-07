import { buildStrategyAnalysisSchema } from './strategyAnalysis';

describe('buildStrategyAnalysisSchema', () => {
  it('locks the switch when ML extras are not installed', () => {
    const schema = buildStrategyAnalysisSchema({ mlInstalled: false });
    expect(schema.children[0].name).toBe('analysis.enabled');
    expect(schema.children[0].readonly).toBe(true);
  });

  it('unlocks the switch when ML extras are installed', () => {
    const schema = buildStrategyAnalysisSchema({ mlInstalled: true });
    expect(schema.children[0].readonly).toBe(false);
  });
});
