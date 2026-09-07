import { useEffect, useState } from 'react';
import {
  FAKE_PROGRESS_CAP,
  FAKE_PROGRESS_STEP,
  clampFakeProgress,
  nextFakeProgress,
} from '../pages/setupPage/setup.helpers';

/**
 * While `active`, nudge a percent from `basePercent` toward `cap` on a timer.
 * Cap should be the current step's share of the weighted bar (not a global 90%).
 */
export function useFakeProgress(active, basePercent = 0, options = {}) {
  const cap = options.cap ?? FAKE_PROGRESS_CAP;
  const step = options.step ?? FAKE_PROGRESS_STEP;
  const tickMs = options.tickMs ?? 800;
  const [percent, setPercent] = useState(basePercent);

  useEffect(() => {
    setPercent((prev) => clampFakeProgress(prev, { active, basePercent, cap }));
  }, [active, basePercent, cap]);

  useEffect(() => {
    if (!active) return undefined;
    const timerId = window.setInterval(() => {
      setPercent((prev) => nextFakeProgress(prev, cap, step));
    }, tickMs);
    return () => window.clearInterval(timerId);
  }, [active, cap, step, tickMs]);

  return active ? percent : basePercent;
}
