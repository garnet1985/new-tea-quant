# 策略域 BFF：`routes/` 编排

**版本：** 0.2.1

FED 侧尚无独立 `strategy*/API.md`（原 `strategyWorkbenchPage/mocks/API.md` 已移除）；本文件为策略 HTTP 路由与编排的当前 SSOT，字段语义以工作台 / 设计页前端消费为准。

## 目录

```text
core/bff/APIs/strategy/
  api_base.py               # strategy_api_bp, API_BASE_PATH
  helpers/                  # snapshots / report_hydrate / formatting …
  routes/
    catalog/                # V2-02
    decision/               # D1-01 … D1-11 决策者会话
    package/                # V2-13 … 15
    report/                 # V2-07*
    settings/               # V2-04 / V2-09
    version/                # V2-01/03/08 + cache + pin
    folder/                 # 打开策略目录
    runner/                 # V2-05/06* + scan 薄壳；进度落盘在 strategy core
```

## 原则

- **路径**：有 target 时统一为 `/v1/strategy/{strategy_key_or_name}/…`（``meta.key`` 或 path name，可多段）；无 target 的全局资源（catalog、settings 选项、package import、全表 cache、scan/context）不加 strategy 段。
- **共用类方法**：``DiscoveryService.resolve_strategy_path``、``WorkbenchVersionId.parse``、``WorkbenchStep.try_parse``（挂在类上，不单独 export 函数）。
- **routes/<area>/routes.py**：解析 HTTP → `impl.lazy_load()` → `ok` / `error`。
- **routes/<area>/implementer.py**：领域编排 / DTO；lazy-import strategy core 与本包 helpers。
- **Snapshot**：前端概念（多 version settings）；读模型在 ``helpers/workbench_snapshots``（磁盘 registry）。后端 run 经 ``Strategy.simulate`` 写 ``simulations/{vid}/``，BFF 不做 cache 命中判断。
- 不再保留独立的 ``cache`` 路由模块；磁盘 version 清理与固定挂在 **version**。
- Version / 指纹规则见 ``modules.strategy`` [VERSIONING.md](../../modules/strategy/docs/VERSIONING.md)。
- BFF 不做缓存命中判断。
- 工作台三步 ``enum | price | portfolio`` 与核心共用 ``WorkbenchStep``（``core.modules.strategy.contracts``）。制定策略 UI 另有第四步 **决策模拟**（``/strategy-design/.../decision``），不进入 ``WorkbenchStep``。
- **决策模拟 / 决策者**不是 ``WorkbenchStep`` / ``SimulateKind``。HTTP 挂在 ``/decision/sessions``；动作与 CLI ``sd`` 同一台 ``DecisionEngine``（每次请求从磁盘打开该局）。FED 入口是制定策略第四步；主导航 ``/decision`` 已去掉（跨策略推迟到 0.5.1）。

## V2 路由 × 文件

| V2 | 方法 | 路由 | 文件 |
|----|------|------|------|
| V2-01 | GET | `/v1/strategy/<strategy_key_or_name>/version/latest` | `routes/version/` |
| V2-02 | GET | `/v1/strategy/catalog/<page>/<limit>` | `routes/catalog/` |
| V2-03 | GET | `/v1/strategy/<strategy_key_or_name>/versions` | `routes/version/` |
| V2-04 | GET | `/v1/strategy/settings/{portfolio,sampling,simulation,risk-control,market-rules}` | `routes/settings/` |
| V2-05 | POST | `/v1/strategy/<strategy_key_or_name>/<step>/run` | `routes/runner/` |
| V2-06b | GET | `/v1/strategy/<strategy_key_or_name>/run/progress` | `routes/runner/` |
| V2-06 | GET | `/v1/strategy/<strategy_key_or_name>/<step>/progress` | `routes/runner/` |
| V2-07 | GET | `/v1/strategy/<strategy_key_or_name>/report/<step>/<version_id>` | `routes/report/` — 含 ``report`` + ``analysis``（``enabled`` / ``available`` / ``facts`` / ``conclusion``）。portfolio ``capitalMetrics`` 另附完整 ``eventCurveLabels/Values``、``eventDrawdownValues``、``tradeEvents``（买卖点；来自 ``equity_curve.json`` / ``trades.json``，非 ≤80 抽稀序列） |
| V2-07b | GET | `/v1/strategy/<strategy_key_or_name>/report/<step>/<version_id>/ref` | `routes/report/` |
| V2-07c | GET | `/v1/strategy/<strategy_key_or_name>/report/<step>/<version_id>/stock/<stock_id>` | `routes/report/` |
| V2-08 | GET | `/v1/strategy/<strategy_key_or_name>/version/<version_id>` | `routes/version/` |
| occupancy | GET | `/v1/strategy/<strategy_key_or_name>/settings/current` | `routes/settings/` — 当前 `settings.py` 字节 rev + 正文 + execute 投影 |
| persist | POST | `/v1/strategy/<strategy_key_or_name>/settings/persist` | `routes/settings/` — 草稿写回；`If-Match` / `settings_rev`，冲突 409 |
| V2-09 | POST | `/v1/strategy/<strategy_key_or_name>/settings/apply/<version_id>` | `routes/settings/` — 恢复历史 version 配置到 ``settings.py``；同样 If-Match |
| V2-11 | DELETE | `/v1/strategy/version/cache` | `routes/version/` |
| V2-12 | DELETE | `/v1/strategy/<strategy_key_or_name>/version/<version_id>/cache` | `routes/version/` |
| pin | POST | `/v1/strategy/<strategy_key_or_name>/version/<version_id>/pin` | `routes/version/` — 固定（只改 `meta.json` 根上 `pinned`） |
| pin | DELETE | `/v1/strategy/<strategy_key_or_name>/version/<version_id>/pin` | `routes/version/` — 取消固定 |
| folder | POST | `/v1/strategy/<strategy_key_or_name>/folder/reveal` | `routes/folder/` — 本机打开策略目录 |
| V2-13 | GET | `/v1/strategy/<strategy_key_or_name>/package/export` | `routes/package/` |
| V2-14 | POST | `/v1/strategy/package/import/preview` | `routes/package/` |
| V2-15 | POST | `/v1/strategy/package/import` | `routes/package/` |
| scan | GET | `/v1/strategy/scan/context` | `routes/runner/` |
| scan | GET/POST | `/v1/strategy/<strategy_key_or_name>/scan` | `routes/runner/` |
| scan | GET | `/v1/strategy/<strategy_key_or_name>/scan/progress` | `routes/runner/` |

## D1 决策者

口径见 strategy [DECISION_MAKER.md](../../../modules/strategy/docs/notes/DECISION_MAKER.md)。``version`` / ``version_id`` 默认当前 ``settings.py`` 命中的 enum vid（与 ``so`` / ``sd`` 相同）。信封同 V2：``{ status, message }``。

| D1 | 方法 | 路由 | 说明 |
|----|------|------|------|
| D1-01 | GET | `/v1/strategy/<strategy_key_or_name>/decision/sessions` | 列出该 version 下各局。query：``version``。``message`` 含 ``last_session_id``（上次打开的局）与 ``has_completed``（本 version 是否至少有一局走完） |
| D1-02 | POST | `/v1/strategy/<strategy_key_or_name>/decision/sessions` | 打开或续局。body：``version_id`` / ``session_id`` / ``new_session``。0 局新开；1 局续；≥2 且未指定 session → **409** ``ambiguous_sessions``（``message.sessions``） |
| D1-03 | GET | `/v1/strategy/<strategy_key_or_name>/decision/sessions/<dm_id>` | 该局现场快照（不推进） |
| D1-04 | DELETE | `/v1/strategy/<strategy_key_or_name>/decision/sessions/<dm_id>` | 删除一局 |
| D1-05 | POST | `…/sessions/<dm_id>/pick` | body ``{ local_id, shares }``；也可 ``cash``（金额按手数折股）。同一编号覆盖。返回现场 |
| D1-06 | POST | `…/sessions/<dm_id>/done` | 看账单，``phase=confirming`` |
| D1-07 | POST | `…/sessions/<dm_id>/reset` | 清空当天草稿并回到 picking。body 可带 ``keep_draft=true``：只取消确认，保留已选股数 |
| D1-08 | POST | `…/sessions/<dm_id>/next` | 须已 done。提交并推进到下一事件日（仓位变化或新机会）；``exits`` 为沿途只读出场 |
| D1-09 | GET | `…/sessions/<dm_id>/holdings` | 持仓（这一停的收盘 / 浮动 / 策略目标文案） |
| D1-10 | GET | `…/sessions/<dm_id>/info` | query：``target``（编号或代码，必填）、``n``、``columns``（逗号分隔）。截至 D 的最近 N 根。``message`` 含 CLI 表 ``columns/rows``，以及与 V2-07c 同形的 ``candles`` / ``indicator_series``（NaN → ``null``） |
| D1-11 | GET | `…/sessions/<dm_id>/report` | 走完后的终局报告，形状与 portfolio ``capitalMetrics`` 相同。未走完 → **400** |

现场 ``message``（D1-02/03/05–08）主要字段：``dm_id`` / ``version_id`` / ``phase``（``picking`` \| ``confirming`` \| ``completed``）/ ``current_date`` / ``start_date`` / ``end_date``（时间线回测区间）/ ``cash`` / ``open_position_count`` / ``max_portfolio_size`` / ``allocation_mode``（``equal_capital`` \| ``equal_shares`` \| ``kelly``）/ ``asof_stats``（整份策略 as-of）/ ``opportunities[].stats``（**该标的** as-of：该标的 ``exit_date < D`` 的已完成枚举）/ ``opportunities[].lot_size`` / ``opportunities[].lot_step``（主板/创业板 100，科创板/北证 1）/ ``opportunities[].suggested_shares``（按 ``allocation_mode`` 的建议股数：等价 / 等股 / 凯莉；下不成或凯莉无样本为 ``null``）/ ``opportunities[].suggested_cash``（建议股数对应金额）/ ``opportunities[].suggested_basis``（建议根据文案）/ ``opportunities[].status_tags``（枚举触发日 ``st`` / ``star_st``，与 ``stock_status_at_trigger`` 同口径）/ ``opportunities[].name``（去掉 ST / ``(退)`` 后的稳定名）/ ``draft`` / ``bill`` / ``exits`` / ``report_available``。``opportunities`` 同一标的同一买入日只留一笔，已持仓标的不再出现。``pick`` 金额或股数为 0 时从当天草稿去掉该编号。

无枚举产物 → **400**（文案与 CLI 相同）。策略不存在 → **404**。

工作台 ``step_status.decision.done``：当前仿真 version 至少有一局决策模拟走完（不是「正在看的那一局」）。

**未注册**：V2-10 `versions/range`。
