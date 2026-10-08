/** 前端 HTTP 超时（毫秒）。默认勿过长，避免 BFF 卡死时 UI 无限转圈。 */
export const HTTP_TIMEOUT_MS = {
  /** 常规读写：列表、设置、快照等 */
  DEFAULT: 30_000,
  /** 进度轮询：单次 poll 应很快返回 */
  POLL: 20_000,
  /** 文件传输、清缓存、冷启动类 POST */
  LONG: 120_000,
  /** Setup 流水线单步（含数据导入，可能较慢） */
  SETUP: 600_000,
  /** 选装机器学习依赖（xgboost / shap） */
  SETUP_ML: 900_000,
};

// Host/port 不在这里配置：FED 使用相对路径 + CRA proxy。
export const API_VERSION_PREFIX = '/api/v1';
