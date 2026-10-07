import request, {
  HttpStatusError,
  HttpTimeoutError,
  buildHttpStatusError,
} from './index';
import { requestFetch } from './client';

describe('requestFetch timeout', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('throws HttpTimeoutError when fetch does not settle in time', async () => {
    global.fetch = jest.fn(() => new Promise(() => {}));

    await expect(
      requestFetch('/api/v1/health', { timeoutMs: 50 }),
    ).rejects.toBeInstanceOf(HttpTimeoutError);
  });

  it('forwards user AbortSignal without HttpTimeoutError', async () => {
    global.fetch = jest.fn((_url, init) => new Promise((_resolve, reject) => {
      init.signal.addEventListener('abort', () => {
        reject(Object.assign(new Error('Aborted'), { name: 'AbortError' }));
      });
    }));

    const controller = new AbortController();
    const pending = requestFetch('/api/v1/health', {
      timeoutMs: 5000,
      signal: controller.signal,
    });
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: 'AbortError' });
  });
});

describe('request proxies', () => {
  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('getJson delegates to GET with json responseType', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: async () => ({ status: 'ok', message: { items: [] } }),
    }));

    const json = await request.getJson('/api/v1/health');
    expect(json.status).toBe('ok');
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/health',
      expect.objectContaining({ method: 'GET' }),
    );
  });

  it('postJson stringifies plain object body', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: true,
      json: async () => ({ status: 'ok', message: {} }),
    }));

    await request.postJson('/api/v1/setup/start', { body: { foo: 1 } });
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/v1/setup/start',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ foo: 1 }),
      }),
    );
  });

  it('throws HttpStatusError on 404 with default message', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: false,
      status: 404,
      json: async () => ({ status: 'error', message: { detail: '' } }),
    }));

    await expect(request.getJson('/api/v1/missing')).rejects.toMatchObject({
      name: 'HttpStatusError',
      status: 404,
      type: 'not_found',
      message: '资源不存在或已删除',
    });
  });

  it('throws HttpStatusError on 409 with preview payload', async () => {
    global.fetch = jest.fn(() => Promise.resolve({
      ok: false,
      status: 409,
      json: async () => ({
        status: 'error',
        message: {
          detail: '导入冲突：目标路径已存在',
          code: 'package_conflict',
          preview: { rows: [] },
        },
      }),
    }));

    await expect(request.postForm('/api/v1/strategy/package/import')).rejects.toMatchObject({
      name: 'HttpStatusError',
      status: 409,
      code: 'package_conflict',
      type: 'conflict',
    });
  });
});

describe('buildHttpStatusError', () => {
  it('prefers BFF message.detail over default status text', () => {
    const err = buildHttpStatusError(
      { status: 503 },
      { status: 'error', message: { detail: 'DuckDB 锁占用中' } },
      '/api/v1/strategy/run',
    );
    expect(err).toBeInstanceOf(HttpStatusError);
    expect(err.message).toBe('DuckDB 锁占用中');
    expect(err.type).toBe('unavailable');
  });
});
