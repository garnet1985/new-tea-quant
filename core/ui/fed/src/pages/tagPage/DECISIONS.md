# Tag 控制台 UI — 决策记录

更新时间：2026-06-18  
分支：`feature/add-tag-and-data-source-into-ui`

## 背景

Demo 策略（如横截面低价股路径中的 `cap_filter=tag`）依赖 userspace 中已计算的 tag 数据。当前仅 CLI（`python cli.py tag --scenario …`）可触发计算；需要在 UI 上完成 **列表 + 运行**，以便在策略回测前准备 tag 数据。

Tag 配置编辑、tag 结果预览等均 **不在 MVP**。

## MVP 范围

| 包含 | 不包含 |
|------|--------|
| Tag scenario 列表页 | 单 scenario 详情页 / 配置表单 |
| 展示 display name、enabled、定义的 tags、最后更新（有则显示） | 保存 settings、编辑 `core` / `data` 块 |
| 单行「运行」+ 进度轮询 | 「运行全部」、tag-preview |
| BFF：`list` / `run` / `progress` | Data Contract / Tables |

**优先级**：Tag 第一；Data Source（只读列表 + Renew）在时间允许时再做（见 `../dataSourcePage/`）。

## 路由（FED）

| 路径 | MVP |
|------|-----|
| `/advanced/tags` | 是 — 列表 + 行内运行 |
| `/tags` | 重定向至 `/advanced/tags` |
| `/tags/<path:tag_key>` | 否 — 后续与 strategy 详情对齐时再开 |

- **展示名**：`meta.display_name`；缺省回退 `tag_key`（与 strategy 列表一致）。
- **机器 ID / URL**：discovery 的 `tag_key`（POSIX 路径，如 `demo/market_cap_tier`）。
- **主导航**：「高级功能 ▾」→「标签」→ `/advanced/tags`（无独立 landing；`/advanced` 重定向至标签页）
- **原型**：`prototype/tag-console.html` 仅作信息架构参考，不必高保真还原。

## 与 Strategy / Scan 的对齐

- 列表形态参考 `StrategyListPage` + **V2-02** `GET /strategy/catalog/{page}/{limit}`。
- 运行形态参考 **机会扫描**：`POST …/run` → `job_id` → `GET …/progress`（见 `scanPage` + `strategy_scan` BFF）。
- API 编号采用 **T1-xx**（Tag 控制台 MVP）；契约写法与 `strategyWorkbenchPage/mocks/API.md` 一致。

## 列表「最后更新」用哪个字段？

**两层含义，不要混用：**

| 字段 | 含义 | 何时变化 |
|------|------|----------|
| **`last_computed_as_of`**（列表主展示） | 业务数据新鲜度：`sys_tag_value` 上该 scenario 的 **MAX(as_of_date)** | 每次 tag 计算写入 value 后变化 |
| **`scenario_updated_at`**（可选次要） | `sys_tag_scenario.updated_at` 注册表时间 | 仅 scenario **元数据**创建/变更时 |

代码事实（详见下文「scenario.updated_at」）：

- 增量跑 tag、只写 value **不会**更新 `sys_tag_scenario.updated_at`。
- DuckDB 下 schema 的 `ON UPDATE CURRENT_TIMESTAMP` **被剥掉**，insert 后通常不再自动刷新。
- 因此 UI 列表「最后更新」**必须以 `last_computed_as_of` 为准**；`scenario_updated_at` 最多作「配置/registry 变更」补充。

## 并发：两层互斥（均需要）

### 第 1 层 — Tag ↔ Tag（简单）

- **FED**：任一 tag 在跑 → 所有行的「运行」disabled（仅当前 job 可显示进度）。
- **BFF**：进程内 tag run 锁 + 活跃 `job_id`（对齐 `scanner_run._ACTIVE_JOB_ID`）。
- **Progress**：仍按 job 分文件 `userspace/.ntq/tmp/progress/tag-run/{tag_key}__{job_id}.json`（与 scan 同形）。

### 第 2 层 — DuckDB 全局 pipeline（跨模块）

Tag、Strategy 回测/扫描、Data Source renew 等可能争用 **`data.duckdb`**（及个别写路径）。MVP **不做排队**，冲突即 **409** + UI disable。

**推荐实现：全局 pipeline 租约（单文件）**

- 路径：`userspace/.ntq/runtime/pipeline_active.json`（与 `ProgressRecorder` 同属 `.ntq` 运行时区）。
- 内容示例：`{ "kind": "tag_run"|"strategy_scan"|"strategy_run"|"data_renew", "job_id", "resource_key", "started_at", "domains": ["data","tag"] }`
- **Acquire**：任何长任务启动前 CAS 写入；已有活跃租约 → 拒绝。
- **Release**：任务终态（completed/failed）或 BFF 进程 atexit 清理。
- **查询**：`GET /api/v1/runtime/pipeline`（**T1-00**）供 FED 进页/轮询时 disable 按钮并展示「谁占用了 DB」。

各模块后续在 `POST …/run` 入口统一调用同一 `PipelineLease.acquire(kind=…)`；Tag MVP 先实现 tag 侧 + 只读 T1-00，Strategy/renew 接入可渐进。

默认三分库：`data.duckdb`、`tag.duckdb`、`strategy.duckdb` — tag run 写 tag、读 data；renew 写 data；回测读 data、写 strategy。

## Setup 边界

Setup 完成 `import_data` 后，用户可在 Tag 列表触发计算；与 setup 流程独立，不重复 import。

## 实施顺序

1. 定 URL + 本文档 + [`API.md`](./API.md)
2. FED 列表页 UI（可先 mock）
3. BFF 实现 + FED 对接
4. 验收：`demo/market_cap_tier` 可从 UI 跑通，列表「最后更新」有变化

## 验收（Tag MVP）

- [ ] `GET /api/v1/tags/list` 返回 userspace 下所有 discovered scenarios
- [ ] 对 `is_enabled=true` 的 scenario，`POST …/run` 成功并返回 `job_id`
- [ ] `GET …/progress` 直至 `status=completed` 或 `failed`
- [ ] 第二个并发 run 返回 **409**（或等价业务错误）
- [ ] 运行完成后，列表 `last_computed_as_of` 更新
- [ ] `GET /api/v1/runtime/pipeline` 在 tag/strategy/renew 占用时返回 `busy: true`
- [ ] 全局 busy 时 Tag「运行」disabled；第二个 tag run 仍 409

---

## 附录：`sys_tag_scenario.updated_at` 在代码里如何更新

1. **表定义**（`core/tables/tag/tag_scenario/schema.py`）：MySQL 风格 `default: CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`。
2. **DuckDB 建表**（`core/infra/db/engines/_shared/fields/base.py`）：`ON UPDATE` 被去掉，仅剩 insert 默认值 → **无自动 on-update**。
3. **写入路径**（`ScenarioModel._ensure_scenario_metadata` → `tag_service`）：
   - 首次：`save_scenario` → `upsert_many`
   - 已存在且 `recompute=True`：删旧 scenario 再 `save_scenario`
   - 已存在且 meta 变：`update_scenario`（仅 **display_name / description** 与 DB 不一致时，见 `_has_meta_diff`）
   - 已存在且 meta 不变：**直接 `_set_meta(scenario_metadata)`，不写库**
4. **计算阶段**：`save_batch` 只写 `sys_tag_value`，**不 touch** `sys_tag_scenario.updated_at`。

结论：该字段 **不是**「最后一次 tag 计算完成时间」；列表用 `get_max_as_of_date` / value 聚合（`tag_service.get_tag_value_last_update_info`）。
