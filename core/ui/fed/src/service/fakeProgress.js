export const FAKE_PROGRESS_CAP = 90;
/** Default nudge per timer tick (~1%/s at 800ms interval). */
export const FAKE_PROGRESS_STEP = 0.8;

export function nextFakeProgress(current, cap = FAKE_PROGRESS_CAP, step = FAKE_PROGRESS_STEP) {
  const value = Number(current) || 0;
  if (value >= cap) return cap;
  return Math.min(cap, value + step);
}

export function clampFakeProgress(prev, options = {}) {
  const base = Number(options.basePercent) || 0;
  const cap = Number(options.cap);
  const top = Number.isFinite(cap) ? cap : FAKE_PROGRESS_CAP;
  if (!options.active) return base;
  const value = Number(prev) || 0;
  if (value < base) return base;
  // Ignore sub-percent cap jitter from polling; only clamp when clearly past the slice.
  if (value > top + 1) return Math.max(base, top);
  return value;
}
