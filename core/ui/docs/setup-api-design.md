# Setup API 设计

## Section A：API 契约

### 目标

定义 setup 流程的后端契约，支撑前端按 pipeline 执行：

- 动态步骤定义（自动步骤/互动步骤）
- 步骤状态快照
- 启动、提交输入、重试
- 统一错误结构

### 数据模型

### 步骤定义（Step Definition）

```json
{
  "id": "db_connection",
  "name": "DB 配置检查/填写",
  "description": "对应 setup/init_database 的前置配置检查。",
  "requiredUserInputs": [
    {
      "key": "dbType",
      "label": "Database Type",
      "type": "select",
      "required": true,
      "defaultValue": "postgresql",
      "options": [
        { "label": "postgresql", "value": "postgresql" },
        { "label": "mysql", "value": "mysql" }
      ]
    }
  ]
}
```

### 步骤运行态（Step Runtime State）

```json
{
  "stepId": "db_connection",
  "status": "waiting_input",
  "errorMessage": ""
}
```

`status` 枚举：

- `not_started`
- `waiting_input`
- `running`
- `success`
- `failed`

### Setup 状态快照（Setup Status Snapshot）

```json
{
  "sessionId": "setup_20260424_001",
  "version": 12,
  "isReady": false,
  "stepStates": [
    { "stepId": "resolve_deps", "status": "success", "errorMessage": "" },
    { "stepId": "db_connection", "status": "waiting_input", "errorMessage": "" },
    { "stepId": "seed_data", "status": "not_started", "errorMessage": "" }
  ],
  "inputsByStep": {
    "db_connection": {
      "dbType": "postgresql",
      "host": "localhost",
      "port": "5432",
      "database": "new_tea_quant",
      "user": "postgres",
      "password": "",
      "defaultPgsqlSchema": "public"
    }
  }
}
```

### 接口列表

#### 1) 获取 setup 步骤定义

`GET /api/v1/setup/definition`

响应示例：

```json
{
  "status": "ok",
  "message": {
    "steps": [
      {
        "id": "resolve_deps",
        "name": "依赖安装",
        "description": "对应 setup/resolve_deps 步骤。",
        "requiredUserInputs": []
      },
      {
        "id": "db_connection",
        "name": "DB 配置检查/填写",
        "description": "对应 setup/init_database 的前置配置检查。",
        "requiredUserInputs": [
          { "key": "dbType", "label": "Database Type", "type": "select", "required": true, "defaultValue": "postgresql", "options": [{ "label": "postgresql", "value": "postgresql" }, { "label": "mysql", "value": "mysql" }] },
          { "key": "host", "label": "Host", "type": "text", "required": true },
          { "key": "port", "label": "Port", "type": "text", "required": true },
          { "key": "database", "label": "Database Name", "type": "text", "required": true },
          { "key": "user", "label": "User", "type": "text", "required": true },
          { "key": "password", "label": "Password", "type": "password", "required": true },
          { "key": "defaultPgsqlSchema", "label": "Schema", "type": "text", "required": false }
        ]
      },
      {
        "id": "seed_data",
        "name": "初始数据导入",
        "description": "对应 setup/setup_data 步骤。",
        "requiredUserInputs": []
      }
    ]
  }
}
```

#### 2) 获取 setup 当前状态

`GET /api/v1/setup/status?sessionId=<id>`

响应体为 `Setup Status Snapshot`。

#### 3) 启动 setup 流程

`POST /api/v1/setup/start`

请求示例：

```json
{
  "sessionId": "setup_20260424_001",
  "ifMatchVersion": 12
}
```

行为：

- 重置步骤状态为 `not_started`
- 从第一步开始执行 pipeline
- 遇到互动步骤（`waiting_input`）或失败立即停止

响应示例：

```json
{
  "status": "ok",
  "message": {
    "kind": "paused",
    "pausedStepId": "db_connection",
    "snapshot": {}
  }
}
```

`kind` 枚举：

- `paused`
- `failed`
- `completed`

#### 4) 提交互动步骤输入

`POST /api/v1/setup/steps/{stepId}/submit`

请求示例：

```json
{
  "sessionId": "setup_20260424_001",
  "ifMatchVersion": 12,
  "inputs": {
    "dbType": "postgresql",
    "host": "localhost",
    "port": "5432",
    "database": "new_tea_quant",
    "user": "postgres",
    "password": "secret",
    "defaultPgsqlSchema": "public"
  }
}
```

行为：

- 按步骤 schema 校验输入
- 校验失败：该步骤置 `failed`
- 校验成功：该步骤置 `success`，继续执行后续步骤

#### 5) 重试失败步骤

`POST /api/v1/setup/retry`

请求示例：

```json
{
  "sessionId": "setup_20260424_001",
  "ifMatchVersion": 12
}
```

行为：

- 非互动步骤失败：从失败步骤重试并继续
- 互动步骤失败：回到 `waiting_input`，等待用户重新输入

### 错误格式

错误响应示例：

```json
{
  "status": "error",
  "message": {
    "code": "SETUP_STEP_VALIDATION_FAILED",
    "detail": "输入不完整，缺少字段: Password",
    "stepId": "db_connection",
    "details": {}
  }
}
```

错误码采用渐进式补充（按实现迭代增加）。

### 并发控制

- `GET /api/v1/setup/status` 返回最新 `version`
- `start / submit / retry` 必须携带 `ifMatchVersion`
- 版本过期返回冲突（建议 HTTP 409）

冲突响应示例：

```json
{
  "status": "error",
  "message": {
    "code": "SETUP_VERSION_CONFLICT",
    "detail": "setup session has newer state, please refresh",
    "currentVersion": 13
  }
}
```

## Section B：流程语义

### 前端执行规则（对齐约定）

- 步骤顺序严格以 `GET /api/v1/setup/definition` 返回为准
- 前端不可写死步骤序列
- 每个步骤执行态至少展示 2 秒
- 互动步骤与非互动步骤失败后的重试逻辑不同
