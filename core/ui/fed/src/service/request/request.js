import { requestBlob, requestFetch, requestJson } from './client';
import { handleRequestFailure } from './handlers';

function prepareBody(body) {
  if (body == null) {
    return { body: undefined };
  }
  if (typeof FormData !== 'undefined' && body instanceof FormData) {
    return { body };
  }
  if (typeof body === 'string' || body instanceof Blob || body instanceof ArrayBuffer) {
    return { body };
  }
  if (typeof body === 'object') {
    return { body: JSON.stringify(body) };
  }
  return { body };
}

/**
 * @param {string} url
 * @param {RequestInit & {
 *   timeoutMs?: number,
 *   silent?: boolean,
 *   responseType?: 'json' | 'blob' | 'raw',
 *   body?: unknown,
 * }} [options]
 */
async function request(url, options = {}) {
  const {
    responseType = 'json',
    silent = false,
    body,
    ...rest
  } = options;
  const prepared = prepareBody(body);

  try {
    if (responseType === 'raw') {
      return await requestFetch(url, { ...rest, ...prepared });
    }
    if (responseType === 'blob') {
      return await requestBlob(url, { ...rest, ...prepared });
    }
    return await requestJson(url, { ...rest, ...prepared });
  } catch (err) {
    throw handleRequestFailure(err, { url, silent });
  }
}

request.get = (url, opts = {}) => request(url, { ...opts, method: 'GET' });
request.post = (url, opts = {}) => request(url, { ...opts, method: 'POST' });
request.put = (url, opts = {}) => request(url, { ...opts, method: 'PUT' });
request.delete = (url, opts = {}) => request(url, { ...opts, method: 'DELETE' });

request.getJson = (url, opts = {}) => request.get(url, { ...opts, responseType: 'json' });
request.postJson = (url, opts = {}) => request.post(url, { ...opts, responseType: 'json' });
request.putJson = (url, opts = {}) => request.put(url, { ...opts, responseType: 'json' });
request.deleteJson = (url, opts = {}) => request.delete(url, { ...opts, responseType: 'json' });

request.getBlob = (url, opts = {}) => request.get(url, { ...opts, responseType: 'blob' });
request.postBlob = (url, opts = {}) => request.post(url, { ...opts, responseType: 'blob' });

request.postForm = (url, opts = {}) => request.post(url, { ...opts, responseType: 'json' });

export default request;
