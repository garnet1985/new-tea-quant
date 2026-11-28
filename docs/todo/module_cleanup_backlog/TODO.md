# Module cleanup backlog — 模块审查遗留清单

**来源：** `feature/clean-code` 上对 `core/infra` / `core/modules`（及部分 `bff`/`tables`）的系统 review  
**约定：** 本清单只记**当时未做完 / 有意推迟**的债；已落地的清理不写。  
**版本规则：** 当前分支上每个模块 `module_info.version` **只允许 bump 一次**；后续在本分支再改代码时勿再升版本号。

---

## 怎么用

| 优先级（建议） | 含义 |
|----------------|------|
| P0 | 行为/互斥错误或安全缺口，应尽快 |
| P1 | 边界/穿透，影响可维护性 |
| P2 | 结构/文档/命名统一，可择机 |
| P3 | 可选文档、低 ROI |

改完一项就在本文件勾掉或删行，并在对应模块 `docs/DECISIONS.md` 补一句若有架构含义。

---

## P0 — 行为 / 互斥

### job_pipeline · BFF `strategy_scan` 未接入管道

- **现象：** BFF `scanner_run.py` 仍用进程内 `_ACTIVE_JOB_ID` + 线程；不 `submit`、不占全局 running 槽（相对 agent 已 `running_lease(kind=strategy_scan)`）。
- **后果：** 扫描与其它长任务两套互斥；管道坞可能看不到扫描。
- **方向：** `register_handler("strategy_scan")` → BFF 改 `JobPipeline.submit` / `start_now` + lease；删本地单飞。
- **记录：** `infra.job_pipeline` DEC-08
- **状态：** [ ]

### infra.setup · 依赖 `ntq_external`（错误边界）

- **已修：** PackageFetcher 注入 + `NTQ_SETUP_PACKAGE_FETCHER`；`member_parts_complete` 在 setup；条款 URL 由 BFF 补；trace 注册移出 setup（DEC-06）。`module_info` 已去掉 `ntq_external`。
- **状态：** [x]

---

## P1 — 边界 / 穿透

### infra.setup · BFF 仍深导入 `setup.core.*`

- **现象：** `SetupRuntimeManager` 等仍穿透 `setup_session` / `pipeline_state` / `db_install_config` / `import_plan` / `data_packages` 与 step 级 `install_progress`。
- **方向：** 继续收到 `Setup.*` 门面（已有部分 `runtime.bind_*` / `read_import_progress`）。
- **记录：** setup DEC-04
- **状态：** [ ]

### infra.setup · 未声明依赖 `core.ui`；`test_process_cleanup` 测的是 UI

- **现象：** `orchestrator.py` import `core.ui.ports` / `process_cleanup`；`core/shared/__test__/test_process_cleanup.py` 测 UI 而非 setup。
- **方向：** 声明或抽共享端口；UT 迁到 `core/ui`（或删重复）。
- **状态：** [ ]

### infra.setup · → `modules.data_manager`

- **现象：** installer / demo_data_exporter 直连 `DataManager`（已声明依赖）。
- **方向：** 窄注入口 / 安装端口，避免 infra 绑死业务导表实现。
- **状态：** [ ]

### infra.trace · `ntq_external` 深导入 `TraceEndpointService`

- **现象：** `register_trace_endpoint` 仍直连 `trace.core.services.endpoint_service`；无 `Trace.register_*` 门面钩子。
- **方向：** Facade 增加 register；官网层只调门面。
- **状态：** [ ]

### infra.trace · BFF WSGI 路径可能漏注册 ingest

- **现象：** `python -m core.bff.app` 已显式 import / 注册；纯 WSGI 部署若未走同一入口，可能缺 ingest URL。
- **方向：** 与 `__main__` 对齐的统一注册点。
- **状态：** [ ]

### infra.project_context · 多处深导入 `PathManager`

- **现象：** 测试 / 少数模块仍直连 `PathManager` 做 mock（生产 setup 三处已改 Facade）。
- **方向：** 测试 fixture 优先 mock `ProjectContext.path` / `cache`。
- **备注：** membership 单测已 mock Facade；`DATA_PACKAGE_KINDS` 已上 contracts（DEC-07）。
- **状态：** [ ] 测试侧逐步收敛

### membership · token 文件名双处声明

- **已修：** 真源 `project_context.contracts.MEMBERSHIP_TOKEN_FILE_NAME`；membership_constants 再导出。
- **状态：** [x]

### infra.project_context · `MetaNamespace.core_info` → `core.system`

- **现象：** infra 可选 import modules 侧 `core.system`（已文档化为 trade-off）。
- **方向：** 评估是否改为注入 / 上移契约，避免 infra→modules。
- **状态：** [ ]

### modules.strategy · 大量 `strategy.core.*` 穿透

- **现象：** BFF / agent / series_relation 等约百级 deep-import（`ArtifactStore`、consts 等）。
- **方向：** 收窄 `contracts` 或 Facade 加载助手；不做引擎重写级别一次到位。
- **状态：** [ ]

### modules.cli ·（已部分修）其它深导入

- **已修：** `renew --clear-logs` → `DataSourceManager.clear_finished_runs`。
- **仍可查：** `py311_compat_check` 死参 / `--no-py311-compile` 类 0.x 垫片（若仍在）。
- **状态：** [ ] 确认并删死参

### job_pipeline · BFF 测试 monkeypatch `queue_store.queue_path`

- **现象：** `test_workbench_run.py` 等穿透 `job_pipeline.core.queue_store`。
- **方向：** 测 `ProjectContext` / 公开测试钩子，避免测实现路径。
- **状态：** [ ]

### data_manager · tables 测试深导入 `KlineService`

- **现象：** `core/tables/.../test_adj_factor_decimal_consume.py` 直连服务类。
- **方向：** 经 `DataManager().stock.kline` 或 contracts。
- **状态：** [ ]

---

## P2 — 结构 / 命名 / 门面位置

### Facade 文件不在模块根（CORE 指标）

下列大模块 Facade 仍在 `core/<name>.py`，与「根目录 `<module>.py`」不完全一致（有的已文档说明）：

| 模块 | 现状 |
|------|------|
| strategy | `core/strategy.py` |
| tag | `core/tag.py` |
| data_source | `core/data_source_manager.py`（无根 `data_source.py`） |
| backtest_engine | 对照已较规范；perf 脚本仍深导入 `Timeline` |

- **方向：** 择机挪到根或正式在 DECISIONS 写「允许 core/ 门面」。
- **状态：** [ ]

### strategy · `strategy_name` vs `strategy_key` 双轨

- **现象：** 门面/BFF/URL 多用 `strategy_name`；进度/sim/部分 API 用 `strategy_key`（值常相同）。
- **方向：** 对外收敛命名；wire 层可保留 alias 文档。
- **状态：** [ ]

### series_relation / strategy · 展示层兜底

- **现象：** presenter / `discovered_strategy` display_name 等仍有 flat 摘要等磁盘/展示兜底（非公开 API shim）。
- **方向：** 确认无旧磁盘格式后删。
- **状态：** [ ]

### backtest_engine

- 缺可选 `docs/CONCEPTS.md`；`SLICE_BASED_ALGORITHM.md` 无标准版本头。
- `__performance__/scripts/cmd/run.py` 深导入 `Timeline`。
- `BacktestEngine.Performance` 与 `core/performance` 双入口（仅内部）。
- **状态：** [ ]

### data_source

- `DataSourceConfigError` 未进 contracts（若 userspace 要 catch 再加）。
- `docs/BUFFER_PIPELINE.md` 可迁 `docs/notes/`。
- **状态：** [ ]

### tables

- 无 Facade/`contracts`（按发现设计可接受）；缺可选 QUICKSTART / DECISIONS / CONCEPTS。
- 部分 `schema.py` **文件头**仍写旧逻辑名，body 已是 `sys_*`。
- `module_info.dependencies` 空但运行依赖 `infra.db` / `utils`。
- **状态：** [ ]

### ntq_external

- 无 `contracts.py` / `QUICKSTART`（可选）。
- 调用方仍穿透 `ai/member_channel`、`member_profile` 等子模块。
- `conf/endpoints.py` 与 `site_target` 双轨。
- **状态：** [ ]

### analysis

- `contracts.py` 仍空；归因 I/O 仍在 strategy analyzer。
- **状态：** [ ]

### membership / export_import

- 已较干净；无强制后续。export_import zip-slip 已修。

### machine_capacity · Windows `get_disk_type` 不按 path

- **现象：** Win 用全机 `PhysicalDisk.MediaType`，忽略 `path`（DEC-03）。
- **方向：** 若产品要按数据目录精确选盘，再补卷→磁盘映射。
- **状态：** [ ]

---

## P3 — 文档 / 元数据

### 全仓文档版本漂移（publish 检查）

- **现象：** `publish_prep` 的 `test_module_docs_match_module_info_version` 曾报多模块头不一致（ntq_external / setup / updater / utils 等）。
- **方向：** 与 `module_info` 对齐一轮（注意：本分支已 bump 过的模块**不要再升号**，只对齐文头）。
- **状态：** [ ]

### updater

- 未正式启用；编排 / migrate CLI 可能重做。本轮仅轻触文档（DEC-02）。
- **方向：** 重设计时再清 `core/orchestrator` 等。
- **状态：** [ ] 待产品排期

### progress · 测试深导入 `progress.core.store`

- **已修：** `Progress.reset_for_tests()`；跨模块单测已迁到门面（DEC-05）。
- **状态：** [x]

---

## 已在本轮处理、勿重复开单（备忘）

| 项 | 结果 |
|----|------|
| infra.ai ↔ ntq_external 反向依赖 | `complete_http` + `member_channel.complete` |
| db 包根再导出 / `ensure_data_manager_restored` | 仅 `Db` + contracts |
| cmd_layout separator / icon 别名 | 已删 |
| discovery API 漏记 `parse_yaml_text` / `load_python_namespace` | 已补 |
| export_import zip-slip | 已校验 |
| job_pipeline → setup 硬依赖 | 改为 `set_import_progress_reader` |
| job_pipeline `strategy_scan` 误猜 `pipeline-*` 根 | DEC-10 → `scan-*` |
| progress 测试深导入 `core.store` | `Progress.reset_for_tests` |
| project_context setup 三处 PathManager 生产深导入 | 改 Facade / contracts |
| membership token 文件名双写 | contracts.MEMBERSHIP_TOKEN_FILE_NAME |
| setup 单测 PathManager 深 mock | `NTQ_USERSPACE_ROOT` + ProjectContext |
| setup → ntq_external 硬依赖 | PackageFetcher 注入（DEC-06） |
| CLI renew 深导入 data_source.run_status | 已走 Facade |
| project_context `get_ai_*` | 已删 |
| series_relation `strategy`↔`strategy_key` 兼容 | 已删 |

---

## 相关链接

- 准则：[`CORE_MODULE_STANDARDS.md`](../../../CORE_MODULE_STANDARDS.md)、[`CODE_STYLE.md`](../../../CODE_STYLE.md) §13、[`docs/module-doc-standard.md`](../../module-doc-standard.md)
- 市场相关另册：[`../general_market_support/TODO.md`](../general_market_support/TODO.md)
