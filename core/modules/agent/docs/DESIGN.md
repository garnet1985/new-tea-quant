# Agent 设计说明

**版本：** `0.1.0`

**相关文档：** [架构](./ARCHITECTURE.md)

本文件记录骨架阶段已经定下的切分。工具执行和模型往返还没做。

---

## 和 assistant 的分界

`Assistant.chat` 继续做一轮问答：说明书、供应商、会员通道。

`Agent` 做调用循环。它不读取 `api_key.txt`，也不自己发 HTTP。下一步要在 assistant 上增加一个公开的「带工具表的补全」，agent 只调用该入口。

---

## 三块内部结构

### 工具清单（`tool_catalog`）

六个名字先登记，`implemented` 全是 `False`：

| 名字 | 作用 |
|------|------|
| `create_strategy` | 从模板新建策略，已存在则拒绝 |
| `write_strategy_files` | 写 `strategy.py` 与 `settings.py` |
| `validate_strategy` | 加载钩子和 settings，未通过则不准回测 |
| `start_simulate` | 启动组合回测，立刻返回任务 id |
| `read_progress` | 读进度摘要 |
| `read_report` | 读收益、回撤、夏普、交易次数、版本号、报告路径 |

模型只能点这些名字。执行函数等实现时再挂上，不放进 `ToolSpec`。

### 写入准则（`policy`）

相对路径解析后，必须落在下面三个目录之一：

- `userspace/strategies/`
- `userspace/extensions/tags/`
- `userspace/extensions/adapters/`

绝对路径、`..`、`userspace/system/`、`extensions/assistant/`（含密钥）都拒绝。路径经 `ProjectContext.path`，不在模块里写死 userspace 根。

### 运行循环（`run_loop`）

类在树上，门面不导出，调用会说明模型通道尚未接通。次数上限、运行记录目录留到接通模型时再定。记录将落在本机，经 `ProjectContext` 取路径，不把策略正文和报告全文放进每一轮请求。

---

## 本版明确不做

- 不接 DeepSeek，不改 `Assistant.chat`
- 不新建策略、不写文件、不跑回测
- 不把循环暴露成 `Agent.run`
