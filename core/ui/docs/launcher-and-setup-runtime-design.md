# Launcher 与 Setup Runtime 设计（单入口方案）

## 1. 目标

用一个统一入口 `launcher.py` 解决：

- 首次运行：自动检查并安装最小依赖，然后启动 UI
- 日常运行：直接启动 BFF + FED
- 异常场景：明确报错并给出下一步提示

核心原则：

- 对用户只有一个命令：`python launcher.py`
- 不要求用户区分 install/start
- 安装与启动编排逻辑统一在 launcher 中

## 2. 运行流程（状态机）

`launcher.py` 执行状态机：

1. `check_env`：检查 Python/Node/npm
2. `need_install`：判断是否需要安装
3. `install_if_needed`：仅在需要时执行安装步骤
4. `start_bff`
5. `wait_bff_ready`
6. `start_fed`
7. `monitor_and_exit`

流程图（文字）：

- 启动 -> 环境检查失败 -> 退出并提示
- 启动 -> 环境检查通过 -> 需要安装 -> 安装失败 -> 退出并提示
- 启动 -> 环境检查通过 -> 不需要安装 -> 启动服务成功

## 3. 职责边界

## 3.1 launcher.py（唯一入口）

负责：

- 检查环境是否可运行
- 判定安装是否必需
- 触发 setup pipeline
- 启动 BFF/FED
- 健康检查与子进程清理

不负责：

- 业务 API 逻辑
- UI 页面逻辑

## 3.2 setup steps

`setup/*/install.py` 保持“单步骤实现”职责：

- 每个步骤处理一个安装/初始化任务
- 返回明确成功/失败退出码
- 不自行启动 UI 服务

## 4. 依赖分层（最小可启动）

目标：满足“有 Python、有 Node，能启动 BFF，能渲染 FED”。

建议分层：

- Python（UI runtime）：
  - `core/ui/bff/requirements.txt`
- Node（FED runtime）：
  - `core/ui/fed/package.json` + lock 文件
- Core 全量依赖（非 UI 最小启动）：
  - 根目录 `requirements.txt`（后续可继续拆分）

安装顺序（最小模式）：

1. Python UI runtime 依赖
2. FED Node 依赖
3. BFF/FED 就绪检查

## 5. needInstall 判定

## 5.1 安装状态文件

路径：`.ntq/install-state.json`

建议结构：

```json
{
  "coreVersion": "0.3.0",
  "python": {
    "uiRequirementsHash": "sha256:...",
    "lastInstallAt": "2026-04-24T03:00:00Z"
  },
  "node": {
    "fedLockHash": "sha256:...",
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

## 5.2 判定条件

任一满足则 `needInstall=true`：

- 状态文件不存在
- 版本不一致（`system_meta.version` != `coreVersion`）
- Python UI 依赖 hash 变化或缺失
- FED lock hash 变化或 node_modules 缺失
- userspace 路径无效/未初始化
- 上次 setup 状态非 success

## 6. setup 元数据（供 BFF/FED API 化）

建议每个步骤目录提供 `meta.json`：

```json
{
  "id": "db_connection",
  "name": "DB 配置检查/填写",
  "description": "初始化数据库连接与可达性检查",
  "scriptEntry": "install.py",
  "requiresUserInput": true,
  "inputSchema": [],
  "retryPolicy": { "mode": "input_required_on_failure" },
  "dependsOn": ["resolve_python_deps"]
}
```

用途：

- BFF 读取 meta 直接生成 setup definition API
- FED 无需硬编码步骤

## 7. userspace 路径策略

目标：userspace 不再固定在仓库目录，可由用户自定义。

路径优先级：

1. 环境变量 `NTQ_USERSPACE_PATH`
2. install-state 持久化路径
3. 迁移兜底默认路径

建议新增 setup 步骤：`init_userspace`

- 校验路径可写
- 初始化目录结构
- 持久化路径

## 8. 版本检查

必须做（本地）：

- 比较 `system_meta.version` 与 `install-state.coreVersion`
- 不一致时进入安装/升级流程

可选做（远程）：

- 查询 release 最新版本并做非阻塞提示

## 9. 服务启动编排

顺序：

1. 启动 BFF
2. 轮询 `/healthz` + `/readyz`
3. 启动 FED

失败策略：

- BFF 未就绪超时：终止并报错
- FED 启动即退出：打印日志并回收全部子进程

## 10. 分阶段落地

Phase A（最小可用）：

- 实现 `launcher.py` 状态机
- 接入 install-state 读写
- 接入最小依赖安装（BFF+FED）

Phase B（setup API 对齐）：

- 为 setup 步骤补 `meta.json`
- BFF 输出 setup definition/status/start/retry API
- FED setup 页面切到真实 API

Phase C（增强）：

- userspace 可配置路径
- 版本冲突与升级提示
- 更细粒度依赖分层（core/full 与 ui/runtime）

## 11. 当前已确认决策

- 只保留一个用户入口：`python launcher.py`
- launcher 负责“检查 + 按需安装 + 启动”
- install 不是用户日常入口（可保留为内部实现）
- 文档统一中文
