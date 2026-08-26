import { useCallback, useState } from 'react';
import { isRequestError } from 'services/request';

/**
 * 包装异步 API 调用：保证 busy 在 finally 释放，错误写入 state。
 * @template T
 * @param {(payload?: unknown) => Promise<T>} fn
 */
export function useAsyncAction(fn) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const clearError = useCallback(() => {
    setError('');
  }, []);

  const run = useCallback(async (payload) => {
    setBusy(true);
    setError('');
    try {
      return await fn(payload);
    } catch (err) {
      const message = isRequestError(err)
        ? err.message
        : (err?.message || '操作失败');
      setError(message);
      throw err;
    } finally {
      setBusy(false);
    }
  }, [fn]);

  return { run, busy, error, clearError, setError };
}
