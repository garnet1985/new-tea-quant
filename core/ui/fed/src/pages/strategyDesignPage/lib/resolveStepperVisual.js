/**
 * Stepper 圆圈视觉状态（优先级：failed > running > done > active-idle > inactive-idle）。
 * @returns {'failed'|'running'|'pending'|'done'|'active-idle'|'inactive-idle'}
 */
export function resolveStepperVisual(stepKey, {
  activeStep,
  stepStatus = {},
  stepProgress = {},
  activeRunId = '',
}) {
  const st = String(stepStatus[stepKey] || 'idle');
  const selected = activeStep === stepKey;
  const pct = Number(stepProgress[stepKey] ?? 0);

  if (st === 'failed') return 'failed';
  if (st === 'running') return { kind: 'running', pct: Number.isFinite(pct) ? pct : 0 };
  if (st === 'pending' && activeRunId) return 'pending';
  if (st === 'done') return selected ? 'done-active' : 'done';
  if (selected) return 'active-idle';
  return 'inactive-idle';
}
