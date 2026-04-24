# 全局 API 规范

## 1) 路径与版本

- 路径模式：`/api/{version}/...`
- 示例版本：`v1`
- 示例路径：`/api/v1/setup/definition`
- 破坏性变更必须升级版本号。

## 2) 统一响应信封

所有接口统一返回：

```json
{
  "status": "ok",
  "message": {}
}
```

约定：

- `status` 取值：`ok` / `error`
- `message` 承载实际业务内容
- 失败时 `message` 里必须有结构化错误信息

成功示例：

```json
{
  "status": "ok",
  "message": {
    "steps": []
  }
}
```

失败示例：

```json
{
  "status": "error",
  "message": {
    "code": "SETUP_STEP_EXECUTION_FAILED",
    "detail": "network timeout",
    "stepId": "resolve_deps"
  }
}
```

## 3) 错误码体系

- 错误响应保留 `code` 字段
- 错误码清单按功能迭代逐步补齐，不一次性冻结

## 4) 幂等性

- `retry` 在相同步骤状态下应幂等
- `start` 可重复调用，以最后一次为准（重置并重新开始）

## 5) 状态机约束

- 非法状态迁移必须返回 `status=error` + 明确 `code`
- 例如：对非互动步骤提交输入，应返回错误

## 6) 稳定标识

- 步骤必须使用稳定 ID（如 `id` / `stepId`）
- 禁止用展示名称作为主键

## 7) 时间格式

- 时间字段统一使用 UTC + ISO8601

## 8) 命名规范

- 前端接口字段统一 `camelCase`
- Query 参数尽量统一 `camelCase`
- 同一接口中禁止混用 `snake_case` 与 `camelCase`

## 9) 分页规范

- 默认使用 offset 分页
- 请求：`page`、`pageSize`
- 响应：`page`、`pageSize`、`total`、`items`

## 10) 排序与过滤语法

- 排序：`sort=field:asc|desc`
- 多字段排序：`sort=createdAt:desc,name:asc`
- 过滤：`filters[field]=value`

## 11) 空值语义

- `""`：显式空字符串
- `null`：未提供值
- 默认规则：除非接口明确声明，否则避免使用 `null`

## 12) 鉴权与权限

- 401：未认证
- 403：已认证但无权限

## 13) 并发控制（推荐）

- 可变资源建议使用乐观并发（`version` 或 `ETag`）
- 更新请求携带最新版本号
- 版本冲突返回 409，客户端需刷新后重试

## 14) 长任务协议

- 异步任务返回 `runId`
- 提供状态查询接口（如 `GET /api/v1/setup/runs/{runId}`）
- 状态枚举建议：`pending`、`running`、`succeeded`、`failed`、`cancelled`
- 若支持取消，需提供显式取消接口

## 15) 可重试错误分类

- 可重试：网络异常、超时、`429`、瞬时 `5xx`
- 默认不可重试：校验/权限/业务规则类 `4xx`
- 错误体建议提供 `retryable: true|false`

## 16) 可观测性

- 响应头建议包含 `requestId`（或 `traceId`）用于排障

## 17) 兼容性

- 优先增量字段（向后兼容）
- 删除或重命名字段必须升级版本
