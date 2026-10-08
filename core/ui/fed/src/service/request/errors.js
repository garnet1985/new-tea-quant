export class RequestError extends Error {
  constructor(message, { type = 'api', url = '', cause = null } = {}) {
    super(message);
    this.name = 'RequestError';
    this.type = type;
    this.url = url;
    if (cause) this.cause = cause;
  }
}

export class HttpTimeoutError extends RequestError {
  constructor(url, timeoutMs) {
    const sec = Math.max(1, Math.round(Number(timeoutMs) / 1000));
    super(`请求超时（${sec}s）：${url}`, { type: 'timeout', url });
    this.name = 'HttpTimeoutError';
    this.timeoutMs = timeoutMs;
  }
}

/** HTTP 非 2xx 或 BFF ``status: error``；含 status/code/payload 供 api 层分支。 */
export class HttpStatusError extends RequestError {
  constructor(message, {
    status = 0,
    url = '',
    code = '',
    payload = null,
    cause = null,
  } = {}) {
    super(message, { type: httpErrorType(status), url, cause });
    this.name = 'HttpStatusError';
    this.status = status;
    this.code = code;
    this.payload = payload;
    this.preview = payload && typeof payload === 'object' ? payload.preview : undefined;
  }
}

const DEFAULT_STATUS_MESSAGES = {
  400: '请求无效',
  401: '未授权',
  403: '无权限',
  404: '资源不存在或已删除',
  409: '操作冲突，请稍后重试',
  422: '请求无法处理',
  429: '请求过于频繁，请稍后再试',
  500: '服务器错误',
  502: '网关错误',
  503: '服务暂时不可用，请稍后重试',
  504: '网关超时',
};

function httpErrorType(status) {
  if (status === 404) return 'not_found';
  if (status === 409) return 'conflict';
  if (status === 503 || status === 502 || status === 504) return 'unavailable';
  if (status >= 500) return 'server';
  if (status >= 400) return 'client';
  return 'http';
}

function extractMessagePayload(json) {
  const message = json?.message;
  if (message && typeof message === 'object') {
    return message;
  }
  if (typeof message === 'string') {
    return { detail: message };
  }
  return {};
}

/**
 * 从 BFF 响应构造 ``HttpStatusError``（全局 404/409/503 等兜底文案）。
 * @param {Response} response
 * @param {object} json
 * @param {string} url
 */
export function buildHttpStatusError(response, json, url) {
  const status = Number(response?.status) || 0;
  const payload = extractMessagePayload(json);
  const detail = String(
    payload.detail
    || json?.error
    || DEFAULT_STATUS_MESSAGES[status]
    || '',
  ).trim();
  const message = detail || `HTTP ${status || 'error'}`;
  const code = String(payload.code || '').trim();
  return new HttpStatusError(message, {
    status,
    url,
    code,
    payload: Object.keys(payload).length ? payload : null,
  });
}

function isAbortError(err) {
  return err?.name === 'AbortError' || err?.code === 20;
}

function isNetworkFetchError(err) {
  if (!err) return false;
  if (err instanceof TypeError) return true;
  const msg = String(err.message || '').toLowerCase();
  return msg.includes('failed to fetch')
    || msg.includes('networkerror')
    || msg.includes('load failed');
}

/**
 * @param {unknown} err
 * @param {{ url?: string }} [context]
 * @returns {RequestError}
 */
export function normalizeRequestError(err, context = {}) {
  const url = String(context.url || err?.url || '').trim();
  if (err instanceof RequestError) {
    if (url && !err.url) err.url = url;
    return err;
  }
  if (isAbortError(err)) {
    return new RequestError('请求已取消', { type: 'abort', url, cause: err });
  }
  if (isNetworkFetchError(err)) {
    return new RequestError('无法连接服务器（网络或代理异常）', { type: 'network', url, cause: err });
  }
  const message = String(err?.message || '请求失败').trim() || '请求失败';
  return new RequestError(message, { type: 'api', url, cause: err });
}

export function isRequestError(err) {
  return err instanceof RequestError;
}

export function isHttpStatusError(err) {
  return err instanceof HttpStatusError;
}
