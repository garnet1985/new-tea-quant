# infra.setup — 设计与决策

**模块：** `infra.setup` · **版本：** `0.2.1`

**最低支持核心版本：** `>=0.5.0`

本文记录 infra.setup 模块的设计目标、方案思路与拍板决策。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

- 安装必须在尚无可用 CLI、甚至尚无 venv 时能跑（源码 zip / Docker / `install.py`），因此安装域必须独立于 CLI 与升级编排。
- `install.py` 不询问 userspace / 数据库，但开始前要同意使用条款；这两项不能被静默丢掉。UI 向导刷新后必须看到与 CLI 一致的同一完成态。

## 方案与思路

- **安装域独立于 CLI：** 安装逻辑只写在 `core/infra/setup/`，CLI 侧只做薄调用，升级编排交给 `infra.updater`（见下文 DEC-01）。
- **门面收口：** 对外只导出 `Setup`。`NewTeaQuantSetup`、`InstallOrchestrator` 等为内部实现，步骤脚本可继续引用，产品代码与 CLI handlers 不应深挖。
- **CLI 与 UI 安装状态同一份：** 以 `.ntq/setup-runtime.json` 的 `isReady` 作为向导完成态的唯一事实来源，CLI 与 UI 写同一份文件（见下文 DEC-02）。
- **目录按步骤｜共用｜编排：** 见 DEC-03。

---

## DEC-01：设计点 1：安装域独立于 CLI

- 安装逻辑只写在 `core/infra/setup/`
- `cli.py` / `devcli.py` 安装相关只调用 `Setup.*`；应用升级走 `userspace/system/updater` / `Updater`
- 禁止 `infra.setup` import `core.modules.cli`
- 禁止 setup 实现升级编排（见 `infra.updater`）
- userspace 模板 zip 落在 `core/infra/setup/core/steps/init_userspace/assets/`；演示包落在 `userspace/.ntq/packages/{demo|member|full}/`（导出与下载共用）

---

## DEC-02：设计点 3：CLI 与 UI 安装状态同一份

- `.ntq/setup-runtime.json` 的 `isReady` 是向导完成态的唯一事实来源
- CLI 可带 `--userspace` / `--db`（及连接参数）；省略走默认；带了就必须用；失败即停
- CLI 跑完写入同一份 `setup-runtime.json`；UI 向导跑完同时 `mark_cli_ready`

---

## DEC-03：步骤｜共用｜编排 目录收口

- `core/steps/<id>/`：步骤实现；产物工厂并入对应步骤（`init_userspace/package.py`、`import_data/export/`），取消独立 `core/scripts/`
- `core/shared/`：跨步骤共用（env、install_runtime、meta、progress、trace、license…）
- `core/orchestrator.py`：外层编排；`install_*_runtime` 等集中调度 CLI / UI / session
- userspace 模板从仓库根 `initialization/userspace/` 迁入 `steps/init_userspace/assets/`（演示数据已走 `.ntq/packages`，模板不必再放在仓库根）
- 禁止 `pip_index` 一类仅转发 infra 的 re-export 空壳；镜像策略走 `Utils.pkg`

---

## DEC-04：穿透引用与门面扩展

- **已收口：** 安装导入进度对 `Progress` 的 flush 只经 `Progress.drain`；BFF / job_pipeline 读导入摘要经 `Setup.runtime.read_import_progress`，绑 progress 目录经 `Setup.runtime.bind_install_progress_dir`
- **仍允许（步骤内）：** `core/steps/*/install.py` 与 `core/shared/*` 互引；导出工厂被 devcli 脚本 deep-import（维护者路径，非产品门面）
- **待收口（产品代码勿扩）：** BFF `SetupRuntimeManager` 仍 deep-import `setup_session`、`pipeline_state`、`db_install_config`、`import_plan`、`data_packages` 及安装进度逐步函数（`open_install` / `begin_install_step` 等）— UI 向导与 setup 紧耦合，下一刀宜增 `Setup.runtime` 子命名空间或 BFF 专用薄适配层，而非继续扩散 deep-import
- **modules 依赖：** 仍声明 `modules.data_manager`（导表）；**不再**依赖 `ntq_external`（见 DEC-06）。
- **未声明依赖：** `core.orchestrator` 仍 import `core.ui.ports` / `process_cleanup`，`module_info` 未声明（backlog）。

---

## DEC-05：测试隔离走公开路径覆盖

- **采用：** 单测用 `NTQ_USERSPACE_ROOT` + `ProjectContext.cache.clear_userspace_cache`（及必要时 mock `ProjectContext.path.*`），不深导入 `PathManager`。
- **理由：** 与 project_context 门面纪律一致；0.x 不为测试保留内部缓存钩子。

---

## DEC-06：数据包下载由入口注入，setup 不依赖 ntq_external

- **采用：** `Setup.runtime.set_package_fetcher` / 环境变量 `NTQ_SETUP_PACKAGE_FETCHER=module:callable`；缺本地包且无 fetcher 时明确报错。官网实现在 `ntq_external.setup_bridge`，由 `install.py` / CLI / BFF 接线。
- **理由：** infra 不得依赖官网层；删掉 `ntq_external` 后仍可用预置 zip 完成导入。会员分卷齐套判定下沉到 `data_packages.member_parts_complete`。
- **影响：** 条款 URL 由 BFF 补齐；trace endpoint 注册改由入口 / 导入 `ntq_external` 完成，setup 只发事件。

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
