# Agent 设计说明

**版本：** `0.1.0`

**相关文档：** [架构](./ARCHITECTURE.md)

本文件记录骨架阶段已经定下的切分。工具执行和模型往返还没做。

---

## 和 assistant 的分界

`Assistant.chat` 继续做一轮问答：说明书、供应商、会员通道。

`Agent` 做调用循环。它不读取 `api_key.txt`，也不自己发 HTTP。补全走 `Assistant.complete`。`Agent.run` 固定使用会员通道 `ntq`，官网把模型定成 `glm-4-flash`。

---

## 三块内部结构

### 工具清单（`tool_catalog`）

已登记的工具里，新建、写文件、校验、后台启动、读进度和读报告都已实现。`Agent.run` 会把这些说明写进系统提示，让模型用 JSON 点名。

| 名字 | 作用 | 状态 |
|------|------|------|
| `create_strategy` | 从模板新建策略 | 已实现 |
| `write_strategy_files` | 覆盖 `strategy.py` 与 `settings.py` | 已实现 |
| `validate_strategy` | 加载钩子和 settings | 已实现 |
| `start_enumerate` | 后台枚举 | 已实现 |
| `start_price_factor` | 后台价格回测 | 已实现 |
| `start_portfolio` | 后台资金模拟 | 已实现 |
| `start_simulate` | 后台依次跑枚举、价格、资金，一层失败即停 | 已实现 |
| `start_attribute_enumerate` | 后台枚举归因 | 已实现 |
| `start_attribute_price` | 后台价格归因 | 已实现 |
| `start_attribute_portfolio` | 后台资金归因 | 已实现 |
| `start_rolling` | 后台滚动对照 | 已实现 |
| `start_scan` | 后台扫描当前交易日机会 | 已实现 |
| `read_progress` | 读后台任务进度 | 已实现 |
| `read_execution_report` | 读枚举 / 价格 / 资金执行报告摘要 | 已实现 |
| `read_attribution_report` | 读归因结论和敏感度排名 | 已实现 |
| `read_scan_report` | 读扫描摘要和前几条机会 | 已实现 |

模型只能点这些名字。存在性检查、语法、钩子是否可加载，不另登记成工具。行情检查留到启动回测时再做。

`create_strategy` 内部顺序：校验目录名 → 写入准则 → 目录已存在则拒绝 → 确认空模板在 → 复制并启用 → 把 `meta.key` 改成目录名。返回相对路径 `strategies/<key>`。

`write_strategy_files` 只覆盖这两个文件，目录不存在则拒绝。`validate_strategy` 接着检查语法、`meta.key` 与目录名一致、`is_enabled` 为真、公开类继承 `StrategyHooks` 并实现 `is_opportunity`。校验会加载这两个文件，和 NTQ 发现策略时一样。

`start_enumerate`、`start_price_factor`、`start_portfolio`、`start_simulate`、三个 `start_attribute_*` 和 `start_rolling` 共用 `background_run`。都先走同一套校验，再看系统是否已有长任务、该策略是否已在跑。通过后在后台调用 `Strategy` 上对应的方法，马上把 `task_id` 交给模型。区间用 `settings` 里的日期。归因要求已有主 version，滚动对照读 `rolling.py`。`start_simulate` 在同一条进度里依次把管道名改成枚举、价格、资金。`start_scan` 走同一套校验，但进度记在扫描任务上，租约种类是 `strategy_scan`。扫描日由行情决定，模型不传日期。`read_scan_report` 只回摘要和前 8 条机会。

### 写入准则（`policy`）

相对路径解析后，必须落在下面三个目录之一：

- `userspace/strategies/`
- `userspace/extensions/tags/`
- `userspace/extensions/adapters/`

绝对路径、`..`、`userspace/system/`、`extensions/assistant/`（含密钥）都拒绝。路径经 `ProjectContext.path`，不在模块里写死 userspace 根。

### 运行循环（`run_loop`）

`Agent.run` 调用本类。每轮把系统提示、用户原话和此前的工具摘要发给 `Assistant.complete`。模型回复 `{"tool","arguments"}` 时执行工具；启动类工具会等到任务结束再把进度送回。回复 `{"reply"}` 时把这句话返回给用户。一轮最多 10 次模型调用。官网代理只接受 system、user、assistant 三种文本消息，所以工具结果作为下一条 user 消息送回。运行记录目录还没落盘。

---

## 本版明确不做

- 不改 `Assistant.chat` 的百科问答
- 不在文档示例里启动全市场回测
