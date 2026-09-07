import { normalizeRequestError, isHttpStatusError } from './errors';

/**
 * @param {unknown} err
 * @param {{ url?: string, silent?: boolean }} ctx
 * @returns {import('./errors').RequestError}
 */
export function handleRequestFailure(err, ctx = {}) {
  const normalized = normalizeRequestError(err, { url: ctx.url });
  if (!ctx.silent && process.env.NODE_ENV !== 'production') {
    const status = isHttpStatusError(normalized) ? normalized.status : '';
    // eslint-disable-next-line no-console
    console.warn(
      '[request]',
      normalized.type,
      status || '-',
      ctx.url || normalized.url,
      normalized.message,
    );
  }
  return normalized;
}
