import { STRATEGY_DESIGN_STEP_KEYS } from '../constants/strategyDesignSteps';

/**
 * 解析 ``/strategy-design/*`` splat：``{strategy}/enum`` 或仅 ``{strategy}``。
 * @param {string|undefined} splat
 * @returns {{ strategyName: string, step: string }}
 */
export function parseStrategyDesignRoute(splat) {
  const segments = String(splat || '').replace(/^\/+/, '').split('/').filter(Boolean);
  if (segments.length === 0) {
    return { strategyName: '', step: '' };
  }

  const lastRaw = segments[segments.length - 1];
  const last = decodeURIComponent(lastRaw);

  if (STRATEGY_DESIGN_STEP_KEYS.has(last) && segments.length > 1) {
    const nameSegs = segments.slice(0, -1);
    const strategyName = nameSegs.map((seg) => decodeURIComponent(seg)).join('/');
    return { strategyName, step: last };
  }

  const strategyName = segments.map((seg) => decodeURIComponent(seg)).join('/');
  return { strategyName, step: '' };
}
