# Launcher 与 Setup Runtime 设计

## 1. 目标

在 setup 脚本与 UI/BFF 之间提供统一运行时层：

- 探测是否需要安装/更新
- 以结构化、可恢复方式执行 setup 步骤
- 让 BFF/FED 能直接消费步骤元数据
- 仅在依赖满足时启动 BFF/FED

## 2. 范围

本期包含：

- `launcher.py` 生命周期编排
- 安装状态存储（`install-state.json`）
- 步骤元数据（`setup/<step>/meta.json`）
- userspace 路径初始化与管理
- 本地版本兼容检查

本期不包含：

- 远程自动升级
- 全量回滚框架

## 3. 总体架构

组件：

- Setup 脚本：`setup/*/install.py`
- Step Meta：`setup/*/meta.json`
- 启动编排：`launcher.py`
- 状态存储：`.ntq/install-state.json`
- BFF：读取 meta + state，输出 setup API
- FED：消费 setup API，渲染 pipeline

执行链路：

1. 用户运行 `launcher.py`
2. 进行 `needInstall()` 判定
3. 若需要安装，执行 setup（完整或断点续跑）
4. 启动 BFF，等待就绪
5. 启动 FED

## 4. launcher.py 职责

- 环境检查（python/node/pip/npm 及版本）
- 判定是否需要安装
- 执行安装流程
- 按顺序启动服务（BFF -> FED）
- 健康检查与超时处理
- 子进程退出时的清理

建议命令：

- `python launcher.py`（默认：检查 -> 安装(如需) -> 启动）
- `python launcher.py --no-install`（跳过安装阶段）
- `python launcher.py --install-only`（仅安装）
- `python launcher.py --resume`（从失败步骤恢复）
- `python launcher.py --userspace /abs/path`

## 5. 是否需要安装（保护机制）

## 5.1 状态文件

路径：`.ntq/install-state.json`

建议结构：

```json
{
  "coreVersion": "0.3.0",
  "python": {
    "executable": "/abs/path/to/venv/bin/python",
    "requirementsHash": "sha256:...",
    "lastInstallAt": "2026-04-24T03:00:00Z"
  },
  "node": {
    "nodeVersion": "20.11.0",
    "fedLockHash": "sha256:...",
    "bffLockHash": "sha256:...",
    "lastInstallAt": "2026-04-24T03:01:00Z"
  },
  "userspace": {
    "path": "/abs/path/to/userspace",
    "initialized": true
  },
  "setupRuntime": {
    "lastStatus": "success",
    "lastFailedStepId": ""
  }
}
```

## 5.2 needInstall() 判定条件

满足任一条件则需安装：

- 状态文件不存在
- `system_meta.version` 与 `coreVersion` 不一致
- `venv` 缺失或 `requirementsHash` 变化
- FED/BFF 的 node 依赖缺失或 lock hash 变化
- userspace 路径不可读写或未初始化
- 上次 setup 非 success

## 6. setup 步骤元数据（meta）

每个步骤目录新增 `meta.json`，示例：

```json
{
  "id": "db_connection",
  "name": "DB 配置检查/填写",
  "description": "初始化数据库连接与可达性检查",
  "scriptEntry": "install.py",
  "requiresUserInput": true,
  "inputSchema": [
    { "key": "dbType", "label": "Database Type", "type": "select", "required": true, "options": ["postgresql", "mysql"] },
    { "key": "host", "label": "Host", "type": "text", "required": true },
    { "key": "port", "label": "Port", "type": "text", "required": true },
    { "key": "database", "label": "Database Name", "type": "text", "required": true },
    { "key": "user", "label": "User", "type": "text", "required": true },
    { "key": "password", "label": "Password", "type": "password", "required": true }
  ],
  "retryPolicy": {
    "mode": "input_required_on_failure"
  },
  "dependsOn": ["resolve_python_deps"]
}
```

约束：

- `id` 必须稳定
- `scriptEntry` 相对步骤目录
- `requiresUserInput` + `inputSchema` 驱动 FED 表单
- `retryPolicy` 驱动 BFF 重试语义

## 7. setup 运行时语义

状态枚举：

- `not_started`
- `waiting_input`
- `running`
- `success`
- `failed`

重试规则：

- 非互动步骤失败：从失败步骤直接重试
- 互动步骤失败：回到该步骤输入态（`waiting_input`）

pipeline 规则：

- 严格按定义顺序执行
- 遇到 `waiting_input` 或 `failed` 立即暂停
- 失败步骤之后全部保持 `not_started`

## 8. userspace 路径方案

现状问题：

- 默认耦合仓库内固定 `userspace/`

目标：

- userspace 路径可配置
- setup 负责创建/校验 userspace
- core 从单一来源读取 userspace 路径

路径来源优先级：

1. CLI 参数（`--userspace`）
2. 环境变量（`NTQ_USERSPACE_PATH`）
3. install-state 持久值
4. 仓库默认路径（仅迁移兜底）

新增步骤建议：

- `init_userspace`
  - 校验路径可写
  - 初始化目录结构
  - 拷贝模板文件（若不存在）
  - 写回 install-state

## 9. 版本判断机制

必须具备（本地）：

- 对比 `system_meta.version` 与 `install-state.coreVersion`
- 不一致时触发安装/升级流程

可选增强（远程）：

- 查询最新 release 版本
- 若有新版本，做非阻塞提醒

## 10. 服务启动编排

顺序：

1. 启动 BFF
2. 轮询 BFF 健康（`/healthz`、`/readyz`）
3. 启动 FED

策略：

- BFF 超时未就绪：快速失败并输出日志
- FED 启动异常退出：回收全部子进程

## 11. 分阶段落地计划

Phase A（最小可用）：

- 建立 launcher 框架
- 建立 install-state 读写
- 给现有 setup 步骤补 `meta.json`

Phase B（UI/BFF 接入）：

- BFF 读取 meta/state 输出 setup API
- FED setup 页面切换到 BFF API

Phase C（进阶）：

- userspace 自定义路径
- 版本冲突与升级提示

## 12. 待确认问题（下一轮细化）

- UI 中是“合并依赖步骤”还是“python/node 拆分步骤”？
- 首次启动是否默认自动安装，还是先弹确认？
- userspace 迁移是否需要自动从旧路径复制？
- 非互动步骤重试是否设最大重试次数？
# Launcher and Setup Runtime Design

## 1. Goal

Provide a unified runtime layer between setup scripts and UI/BFF:

- detect whether installation/update is required
- run setup steps in a structured and resumable way
- expose step metadata to BFF/FED as setup definition API source
- launch BFF/FED only when runtime prerequisites are ready

## 2. Scope

In scope:

- `launcher.py` lifecycle orchestration
- installation state persistence (`install-state.json`)
- setup step metadata schema (`setup/<step>/meta.json`)
- userspace path initialization and management
- local version compatibility check

Out of scope (for first iteration):

- remote update channel and auto-upgrade
- full rollback framework for every setup step

## 3. High-level Architecture

Components:

- **Setup Step Scripts**: existing `setup/*/install.py`
- **Step Metadata**: `setup/*/meta.json`
- **Launcher**: new `launcher.py`, runtime gatekeeper
- **State Store**: `.ntq/install-state.json`
- **BFF**: reads metadata and runtime state, exposes setup APIs
- **FED**: consumes BFF setup APIs and renders setup pipeline

Execution path:

1. user runs `launcher.py`
2. launcher runs `need_install()` checks
3. if install required, launcher executes setup flow (full or resume)
4. launcher starts BFF and waits for ready
5. launcher starts FED and optionally opens browser

## 4. Launcher Responsibilities

`launcher.py` should own:

- environment checks (python/node/pip/npm availability + version)
- installation-required decision
- setup execution entrypoint
- process startup order (`BFF -> FED`)
- health/readiness polling
- graceful shutdown for child processes

Suggested CLI:

- `python launcher.py` (default: check -> install if needed -> start services)
- `python launcher.py --no-install` (skip install phase)
- `python launcher.py --install-only` (run install, do not start services)
- `python launcher.py --resume` (resume from last failed step)
- `python launcher.py --userspace /abs/path`

## 5. Installation Required Detection

## 5.1 State File

Path: `.ntq/install-state.json` (repo root)

Suggested schema:

```json
{
  "coreVersion": "0.3.0",
  "python": {
    "executable": "/abs/path/to/venv/bin/python",
    "requirementsHash": "sha256:...",
    "lastInstallAt": "2026-04-24T03:00:00Z"
  },
  "node": {
    "nodeVersion": "20.11.0",
    "fedLockHash": "sha256:...",
    "bffLockHash": "sha256:...",
    "lastInstallAt": "2026-04-24T03:01:00Z"
  },
  "userspace": {
    "path": "/abs/path/to/userspace",
    "initialized": true
  },
  "setupRuntime": {
    "lastStatus": "success",
    "lastFailedStepId": ""
  }
}
```

## 5.2 need_install() Conditions

Return `true` if any condition matches:

- state file missing
- core version changed (`system_meta.version` != `coreVersion`)
- python venv missing or requirements hash changed
- node_modules missing for FED/BFF or lock hash changed
- userspace path missing/unreadable/uninitialized
- previous setup status not success

## 6. Setup Step Metadata

Each setup step folder should include `meta.json`.

Example `setup/init_database/meta.json`:

```json
{
  "id": "db_connection",
  "name": "DB 配置检查/填写",
  "description": "初始化数据库连接与可达性检查",
  "scriptEntry": "install.py",
  "requiresUserInput": true,
  "inputSchema": [
    { "key": "dbType", "label": "Database Type", "type": "select", "required": true, "options": ["postgresql", "mysql"] },
    { "key": "host", "label": "Host", "type": "text", "required": true },
    { "key": "port", "label": "Port", "type": "text", "required": true },
    { "key": "database", "label": "Database Name", "type": "text", "required": true },
    { "key": "user", "label": "User", "type": "text", "required": true },
    { "key": "password", "label": "Password", "type": "password", "required": true }
  ],
  "retryPolicy": {
    "mode": "input_required_on_failure"
  },
  "dependsOn": ["resolve_python_deps"]
}
```

Rules:

- `id` must be stable
- `scriptEntry` must be relative to step folder
- `requiresUserInput` + `inputSchema` drive FED form rendering
- `retryPolicy` guides BFF retry behavior

## 7. Setup Runtime Semantics

Status enum:

- `not_started`
- `waiting_input`
- `running`
- `success`
- `failed`

Retry behavior:

- non-interactive step fail -> retry from same step
- interactive step fail -> go back to `waiting_input` for that step

Pipeline rules:

- strict order from metadata list
- stop on first `waiting_input` or `failed`
- steps after failed step remain `not_started`

## 8. Userspace Path Plan

Current pain:

- userspace is assumed to exist under repo

Target:

- userspace path is a setup-managed variable
- user can choose custom path
- core reads userspace path from single source of truth

Proposed source of truth (priority):

1. CLI argument (`--userspace`)
2. env var `NTQ_USERSPACE_PATH`
3. persisted value in install-state
4. fallback default (repo-relative) only for migration

New setup step suggestion:

- `init_userspace`:
  - validate writable path
  - create directory structure
  - copy templates/examples if absent
  - persist path to install-state

## 9. Version Check Strategy

Local compatibility check (must-have):

- compare `system_meta.version` with `install-state.coreVersion`
- mismatch -> require install/upgrade flow

Remote update hint (optional later):

- query latest version from release endpoint
- if newer available, expose non-blocking UI notice

## 10. Service Startup Orchestration

Order:

1. start BFF
2. poll BFF `/healthz` and `/readyz`
3. start FED

Health policy:

- if BFF not ready within timeout, fail fast
- if FED exits immediately, surface startup logs and stop all

## 11. Migration Plan

Phase A:

- add launcher skeleton
- add install-state schema and write/read utility
- add `meta.json` for existing setup steps

Phase B:

- BFF reads metadata + state to serve setup APIs
- FED setup page switches from local mock to BFF APIs

Phase C:

- userspace custom path step
- version conflict and update hint flows

## 12. Open Questions (to refine together)

- do we want one combined `resolve_deps` step or separate python/node steps in UI?
- should first run auto-install silently or always ask confirmation in launcher?
- for userspace migration, do we need auto-copy from old default path?
- should setup retries be bounded (max retry count) for non-interactive steps?
