import logClientError from './logClientError';

describe('logClientError', () => {
  const originalEnv = process.env.NODE_ENV;

  afterEach(() => {
    process.env.NODE_ENV = originalEnv;
    jest.restoreAllMocks();
  });

  it('warns in development', () => {
    process.env.NODE_ENV = 'development';
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    logClientError('test.scope', new Error('boom'), 'extra');
    expect(warn).toHaveBeenCalledWith('[client:test.scope]', 'boom', 'extra');
  });

  it('is silent in production', () => {
    process.env.NODE_ENV = 'production';
    const warn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    logClientError('test.scope', new Error('boom'));
    expect(warn).not.toHaveBeenCalled();
  });
});
