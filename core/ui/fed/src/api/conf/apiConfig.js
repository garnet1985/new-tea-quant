// 这里只定义 API 版本前缀。
// Host/port 不在这里配置：FED 当前使用「相对路径 + CRA proxy」方式访问后端。
// 若需修改开发环境后端地址，请更新 `core/ui/fed/package.json` 中的 `proxy` 字段。
export const API_VERSION_PREFIX = '/api/v1';
