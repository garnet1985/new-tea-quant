# PostProcess API 文档

**模块：** `modules.post_process` · **版本：** `0.3.2`

**最低支持核心版本：** `>=0.5.0`

> 须与 `module_info.yaml` 一致。公开入口状态最高 **`beta`**。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。协议见 [docs/PROTOCOL.md](./docs/PROTOCOL.md)；声明见 [docs/POST_PROCESSOR.md](./docs/POST_PROCESSOR.md)。

**公开约定：** 包根仅导出 `PostProcess`；协议与 `BaseAdapter` 从 [`contracts.py`](./contracts.py) 导入。实现位于 `core/`，禁止 deep-import。

---

## PostProcess

**描述：** 扫描后续处理门面（协议规范化 + Adapter / PostProcessor 发现、摘要、启用写入与执行）

### 协议

#### build_session_report

`PostProcess.build_session_report(*, scan_date, strategy_name, opportunities, goal=None, strategy_version="", emitted_at="") -> ScanSessionReport`

- **状态：** `beta`
- **描述：** 将单策略扫描机会规范为会话报告（`strategies` 长度为 1）

#### opportunity_from_scan_item / goal_summary_from_settings / validate_session

辅助映射与校验；见源码 docstring。

### Adapter

#### list_adapters / validate_adapter / load_adapter_class

发现、校验、加载 `userspace.extensions.post_process.adapters.<name>.adapter` 中的 `BaseAdapter` 子类。

#### summarize_adapter / list_adapter_summaries

`PostProcess.summarize_adapter(name) -> dict | None`  
`PostProcess.list_adapter_summaries() -> list[dict]`

- **状态：** `beta`
- **描述：** 目录摘要：`name`、`display_name`、`validate`、`supports_dry_run`、`default_dry_run`、`readiness`、`status`（`live` / `dry_run` / `unavailable`）；不含 secrets

#### check_adapter_readiness

`PostProcess.check_adapter_readiness(name, *, config=None) -> dict`

- **状态：** `beta`
- **描述：** 合并 settings 与可选 `config` 后按**真发必备**做静态检查；返回 `ok` / `message` / `missing` / `dry_run` / `status` / `remark` / `loadable`。  
  `status` 优先级：`unavailable`（缺配置/不可加载）> `dry_run`（配置齐但仍测试模式）> `live`。

### PostProcessor

#### list_post_processors / list_enabled_post_processors / validate_post_processor / load_post_processor

发现、校验、加载 `userspace/extensions/post_process/post_processors/` 下的声明。  
`list_enabled_post_processors` 仅返回 ``is_enabled: true`` 的 key。

#### summarize_post_processor / list_post_processor_summaries

`PostProcess.summarize_post_processor(key) -> dict | None`  
`PostProcess.list_post_processor_summaries() -> list[dict]`

- **状态：** `beta`
- **描述：** 方案摘要：元数据、`adapters`（含 depends_on / per-adapter `status`）、`execution_order`（拓扑）、`validate`

#### set_enabled

`PostProcess.set_enabled(key, enabled) -> PostProcessorDefinition`

- **状态：** `beta`
- **描述：** 写入 JSON ``is_enabled``

#### update_post_processor_adapters

`PostProcess.update_post_processor_adapters(key, adapters) -> (PostProcessorDefinition, list[str])`

- **状态：** `beta`
- **描述：** 写回方案内 adapters 与 depends_on；未提交的 `config` 保留原值；返回定义与拓扑序

#### run_post_processor / run_enabled_post_processors

`PostProcess.run_post_processor(key, session)` — 显式跑指定 key（忽略 is_enabled）。  
`PostProcess.run_enabled_post_processors(session) -> list[str]` — 扫描结束后默认路径：跑所有 enabled。

### Userspace 脚手架（Adapter / PostProcessor）

`PostProcess.scaffold_user_adapter(*, name, display_name="") -> dict`  
`PostProcess.write_user_adapter_files(*, name, adapter_py="", settings_py="") -> dict`  
`PostProcess.validate_user_adapter(*, name) -> dict`  
`PostProcess.scaffold_user_post_processor(*, key, name="", adapter_name="", is_enabled=False) -> dict`  
`PostProcess.write_user_post_processor(*, key, json_body="") -> dict`  
`PostProcess.validate_user_post_processor(*, key) -> dict`  
`PostProcess.describe_user_adapter(*, name) -> dict` / `describe_user_post_processor(*, key) -> dict`  
`PostProcess.list_user_adapter_summaries() -> dict` / `list_user_post_processor_summaries() -> dict`

- **状态：** `beta`
- **描述：** 实现在 `user_post_process`。模板：`_template/empty_adapter`、`_template/empty_post_processor`。发现即注册；返回 `{ok, ...}`。

---

## contracts

| 符号 | 说明 |
|------|------|
| `Opportunity` | 标准机会协议 |
| `StrategyScanReport` | 单策略扫描报告 |
| `ScanSessionReport` | 扫描会话报告 |
| `BaseAdapter` | userspace adapter 基类（`run(session, config, deps)`） |
| `PostProcessorDefinition` / `AdapterBinding` | 声明内存形态 |
