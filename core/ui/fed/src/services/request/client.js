import { HTTP_TIMEOUT_MS } from './config';
import { buildHttpStatusError, HttpTimeoutError } from './errors';

function isAbortError(err) {
  return err?.name === 'AbortError' || err?.code === 20;
}

function attachAbortForward(userSignal, controller) {
  if (!userSignal) {
    return () => {};
  }
  if (userSignal.aborted) {
    controller.abort(userSignal.reason);
    return () => {};
  }
  const onAbort = () => {
    if (!controller.signal.aborted) {
      controller.abort(userSignal.reason);
    }
  };
  userSignal.addEventListener('abort', onAbort, { once: true });
  return () => userSignal.removeEventListener('abort', onAbort);
}

/**
 * @param {string} url
 * @param {RequestInit & { timeoutMs?: number }} [options]
 * @returns {Promise<Response>}
 */
export async function requestFetch(url, options = {}) {
  const {
    timeoutMs = HTTP_TIMEOUT_MS.DEFAULT,
    signal: userSignal,
    ...fetchOptions
  } = options;

  const controller = new AbortController();
  const detachUserAbort = attachAbortForward(userSignal, controller);

  const fetchPromise = fetch(url, {
    ...fetchOptions,
    signal: controller.signal,
  });

  let timerId = null;
  let timedOut = false;
  const racers = [fetchPromise];
  if (timeoutMs > 0) {
    racers.push(new Promise((_resolve, reject) => {
      timerId = setTimeout(() => {
        timedOut = true;
        controller.abort();
        reject(new HttpTimeoutError(url, timeoutMs));
      }, timeoutMs);
    }));
  }

  try {
    return await Promise.race(racers);
  } catch (err) {
    if (err instanceof HttpTimeoutError) {
      throw err;
    }
    if (timedOut || (isAbortError(err) && !userSignal?.aborted)) {
      throw new HttpTimeoutError(url, timeoutMs);
    }
    throw err;
  } finally {
    if (timerId) clearTimeout(timerId);
    detachUserAbort();
  }
}

/**
 * @param {Response} response
 * @returns {Promise<object>}
 */
export async function readResponseJson(response) {
  try {
    const json = await response.json();
    return json && typeof json === 'object' ? json : {};
  } catch {
    return {};
  }
}

function assertOkJsonResponse(response, json, url) {
  if (!response.ok || json?.status !== 'ok') {
    throw buildHttpStatusError(response, json, url);
  }
}

/**
 * @param {string} url
 * @param {RequestInit & { timeoutMs?: number }} [options]
 */
export async function requestJson(url, options = {}) {
  const { headers: optionHeaders, body, ...rest } = options;
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
  const headers = {
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
    ...(optionHeaders || {}),
  };

  const response = await requestFetch(url, {
    ...rest,
    body,
    headers,
  });
  const json = await readResponseJson(response);
  assertOkJsonResponse(response, json, url);
  return json;
}

/**
 * @param {string} url
 * @param {RequestInit & { timeoutMs?: number }} [options]
 * @returns {Promise<{ blob: Blob, response: Response }>}
 */
export async function requestBlob(url, options = {}) {
  const response = await requestFetch(url, options);
  if (!response.ok) {
    const json = await readResponseJson(response);
    throw buildHttpStatusError(response, json, url);
  }
  const blob = await response.blob();
  return { blob, response };
}
