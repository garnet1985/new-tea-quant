const { createProxyMiddleware } = require('http-proxy-middleware');

/**
 * 开发模式 /api → 共享 BFF :8888。
 * 覆盖 package.json 的 ``proxy``，拉长超时以避免 BFF 冷启动 import 时 ECONNRESET。
 */
module.exports = function setupProxy(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8888',
      changeOrigin: true,
      logLevel: 'warn',
      proxyTimeout: 120000,
      timeout: 120000,
    }),
  );
};
