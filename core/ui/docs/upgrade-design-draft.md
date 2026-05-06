# NTQ 升级机制设计草案（Draft）

## 1. 背景与目标

当前 NTQ 代码、BFF 与 FED 在同一安装目录中运行。若直接在运行中替换代码目录，会遇到自替换与文件锁问题（尤其是 Windows）。  
本草案目标是提供一套可跨平台落地、与现有 `launcher.py + setup` 架构兼容的升级方案。

目标：
- UI 可提示新版本并发起一键升级。
- 升级过程不中断用户数据（`userspace` 保留）。
- 升级流程具备可观测状态与失败重试能力。
- 方案可逐步演进到回滚与灰度升级。


## 2. 核心原则

- 代码目录与用户数据目录解耦：升级默认替换代码，不覆盖 `userspace`。
- 不让运行中的服务（BFF/FED）直接替换自身文件。
- 升级状态持久化在 `userspace/.ntq`，便于重启恢复与排错。
- 升级逻辑采用双层 updater，避免“updater 自升级死锁”。


## 3. 目录与状态建议

建议将运行时状态统一收敛至 `userspace/.ntq`（包含 setup 状态、upgrade 状态等）：

- `userspace/.ntq/upgrade.lock`
- `userspace/.ntq/upgrade-state.json`
- `userspace/.ntq/upgrade-last-error.json`
- `userspace/.ntq/updater/bootstrap_updater.py`
- `userspace/.ntq/updater/cache/`（升级包缓存）
- `userspace/.ntq/tmp/`（解压与执行临时目录）


## 4. 升级总体架构（双层 updater）

### 4.1 Layer 0：Bootstrap Updater（稳定层）

位置：`userspace/.ntq/updater/bootstrap_updater.py`  
职责：
- 接收升级任务参数（版本、下载地址、校验信息等）
- 下载并校验升级包
- 解压升级包到临时目录
- 拉起升级包内的 Versioned Updater（Layer 1）

特点：
- 逻辑尽量小且稳定，变更频率低
- 不依赖被替换目录内的业务代码

### 4.2 Layer 1：Versioned Updater（版本层）

位置：升级包内（例如 `updater/runner.py`）  
职责：
- 执行该版本定义的升级步骤（替换代码、迁移、清理等）
- 写回 upgrade 状态
- 触发启动新版本 `launcher.py`

特点：
- 可随版本演进
- 允许本版本引入新升级逻辑


## 5. 推荐升级流程（MVP）

1. UI 调用 `POST /api/v1/system/upgrade/start`
2. BFF 记录任务并拉起 Bootstrap Updater
3. BFF 进入“准备退出”状态并优雅停止
4. Bootstrap Updater 执行下载/校验/解压
5. Bootstrap Updater 调用包内 Versioned Updater
6. Versioned Updater 等待旧进程完全退出（端口释放）
7. Versioned Updater 替换代码目录（`userspace` 保留）
8. Versioned Updater 执行升级迁移（若有）
9. Versioned Updater 启动新版本 `launcher.py`
10. UI 轮询 `upgrade-state`，显示 `completed` 或 `failed`


## 6. 升级状态机（建议）

- `queued`
- `precheck`
- `downloading`
- `verifying`
- `installing`
- `migrating`
- `restarting`
- `completed`
- `failed`

状态字段建议：
- `jobId`
- `fromVersion`
- `toVersion`
- `phase`
- `progressPercent`
- `message`
- `updatedAtUtc`


## 7. API 草案（后续实现）

- `GET /api/v1/system/version`
  - 返回当前版本、最新版本、升级策略（`auto/guided/reinit`）
- `POST /api/v1/system/upgrade/start`
  - 创建升级任务并返回 `jobId`
- `GET /api/v1/system/upgrade/jobs/{jobId}`
  - 返回状态机阶段与进度
- `POST /api/v1/system/upgrade/retry`
  - 失败后重试


## 8. 升级策略与 setup 关系

- `auto`：后台自动迁移，不要求用户重走 setup
- `guided`：进入升级向导（补充新增配置）
- `reinit`：极少数破坏性变更才要求重新初始化

原则：绝大多数升级应做到无感，不要求用户重走 setup。


## 9. 失败与恢复

- 失败时写 `upgrade-last-error.json`，包含阶段与错误摘要
- 支持用户在 UI 点击“重试升级”
- 后续版本可增加“自动回滚到上一版本目录”（V2）


## 10. 跨平台注意事项

- Windows 文件锁严格，必须确保旧进程退出后再替换目录
- 替换优先使用“新目录就绪后切换（rename/swap）”而非原地覆盖
- 执行脚本路径含空格时，命令参数需严格转义


## 11. 分阶段落地建议

Phase 1（MVP）：
- 引入 upgrade 状态机与接口
- 引入 Bootstrap + Versioned updater 最小链路
- UI 展示升级状态与失败重试

Phase 2：
- 增加回滚能力
- 增加升级包签名校验
- 增加灰度升级/延迟切换策略

