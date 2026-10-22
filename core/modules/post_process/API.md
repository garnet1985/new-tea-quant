# PostProcess API 文档

**版本：** `0.3.0`  
**最低支持核心版本：** `>=0.5.0`

> 须与 `module_info.yaml` 一致。公开入口状态最高 **`beta`**。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。协议见 [docs/PROTOCOL.md](./docs/PROTOCOL.md)；声明见 [docs/POST_PROCESSOR.md](./docs/POST_PROCESSOR.md)。

**公开约定：** 包根仅导出 `PostProcess`；协议与 `BaseAdapter` 从 [`contracts.py`](./contracts.py) 导入。实现位于 `core/`，禁止 deep-import。

---

## PostProcess

**描述：** 扫描后续处理门面（协议规范化 + Adapter / PostProcessor 发现与执行）

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

### PostProcessor

#### list_post_processors / list_enabled_post_processors / validate_post_processor / load_post_processor

发现、校验、加载 `userspace/extensions/post_process/post_processors/` 下的声明。  
`list_enabled_post_processors` 仅返回 ``is_enabled: true`` 的 key。

#### run_post_processor / run_enabled_post_processors

`PostProcess.run_post_processor(key, session)` — 显式跑指定 key（忽略 is_enabled）。  
`PostProcess.run_enabled_post_processors(session) -> list[str]` — 扫描结束后默认路径：跑所有 enabled。

---

## contracts

| 符号 | 说明 |
|------|------|
| `Opportunity` | 标准机会协议 |
| `StrategyScanReport` | 单策略扫描报告 |
| `ScanSessionReport` | 扫描会话报告 |
| `BaseAdapter` | userspace adapter 基类（`run(session, config, deps)`） |
| `PostProcessorDefinition` / `AdapterBinding` | 声明内存形态 |
