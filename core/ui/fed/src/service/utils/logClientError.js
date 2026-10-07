/**
 * 非 HTTP 层客户端错误/dev 诊断（poll 失败、storage、listener 等）。
 * production 不输出，避免用户控制台噪音。
 *
 * @param {string} scope 模块/场景，如 setup.poll、workbench.snapshotSync
 * @param {unknown} [err]
 * @param {string} [detail]
 */
export function logClientError(scope, err, detail = '') {
  if (process.env.NODE_ENV === 'production') {
    return;
  }
  const message = err instanceof Error
    ? err.message
    : String(err || '').trim();
  const tag = `[client:${scope}]`;
  if (detail) {
    // eslint-disable-next-line no-console
    console.warn(tag, message || 'unknown', detail);
    return;
  }
  // eslint-disable-next-line no-console
  console.warn(tag, message || 'unknown');
}

export default logClientError;
