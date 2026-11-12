# Job Pipeline — 设计结论

**状态：** 互斥与队列由本模块承担；`task_guard` 已删除。`progress` 保留为进度明细库（不负责「谁在跑」）。  
**版本对齐：** `0.1.0`  
**相关：** [ARCHITECTURE.md](./ARCHITECTURE.md) · [DECISIONS.md](./DECISIONS.md)

本文固定讨论结论，作为实现与迁移的 SSOT。细节拍板进 DECISIONS；公开调用面进根目录 `API.md`。

---

## 1. 要解决什么

今天长任务被拆成两套基础设施：

| 模块 | 实际职责 | 缺口（迁移前） |
|------|----------|------|
| （已删除）`task_guard` | 全局单飞租约（忙则拒绝） | 不是队列；不是 UX 真相源 |
| `infra.progress` | 按 `job_id` 写进度树 / channel | 不能「发现正在跑谁」；与互斥脱节 |

前端若只靠 `sessionStorage` 记 `run_id`，跨 tab 会丢进度；切页后也没有「跑完了」的全局提示。业务 launcher（strategy / tag / renew…）同时摸租约和进度，边界模糊。

**目标：** 一个长任务 infra——**任务登记表 +（先）串行队列 + 进度视图**——阻断前端与「线程怎么跑」的直接耦合：前端只读任务表；后端只通过本模块更新任务状态与进度。

---

## 2. 模块边界

### 做

- 维护 **job 列表 / id→任务信息**（状态、阶段、进度、展示用元数据、跳转提示）
- **提交**长任务：空闲则跑，忙则 **入队**（有上限；满则仍拒绝并说清原因）
- **串行执行**（第一期：全局同时只跑 1 个）——政策，不是死架构
- **挂死 / 进程退出** 时纠正列表（释放槽位，必要时拉下一条）
- 经 BFF 给前端 **只读** list/get（及现有逐步 progress 形状的兼容映射）

### 不做（第一期）

- 通用工作流引擎、DAG 调度器、拓扑排序运行时
- 分布式多机队列
- 自动重试 / 恢复业务中间态（只保证登记表可信）
- 取代业务「如何 simulate / 如何算 tag」——本模块不管业务算法

### 与旧模块关系

| 模块 | 关系 |
|------|------|
| `task_guard` | **已删除。** 互斥与「谁在跑」全部由本模块承担。 |
| `infra.progress` | **保留。** 继续作为进度树 / channel 的读写库（业务页细进度、`tick`/`ratio`）。本模块任务表可摘要挂一份 progress，但不取代 `Progress.read`。 |

---

## 3. 核心模型

### 3.1 任务表（真相源）

`job_id → { kind, resource_key, status, progress, label, locks?, depends_on?, … }`

- 前端 / BFF **只读这份表**（或单条 get），不解析 lease 文件、不假设进度目录布局。
- 业务线程经本模块 **submit / running_lease / complete 路径** 登记任务；细进度仍可直接写 `Progress.*`（或业务 Progress 包装）。

### 3.2 第一期调度：有上限的串行队列

用户点 Run：**不再是忙则拒绝**，而是：

1. 构造 job → 写入表（`pending` 或立刻 `running`）
2. 若已有 `running` → 入队（`pending`），受 **队列最大长度** 约束
3. 当前任务终态后 → 取队头 → `running`
4. 队列满 → deny（明确 reason）

同资源重复提交政策（实现时拍板，倾向）：

- 同 `kind` + `resource_key` 已有 `pending`/`running` → 拒绝或合并，避免无意义堆叠

### 3.3 可扩展性（先预留，后实现）

**资源锁（locks），不是一上来上图：**

- 「strategy 与 tag 可并行、各自单飞」→ 不同 lock 槽
- 「simulate ∥ rolling」→ 拆细 `strategy:{key}:simulate` vs `…:rolling`
- 现在「全局只能一个」→ 大家抢同一把 `global`（或等价默认 policy）

**依赖（depends_on）稍后：**

- 队列模型已经是「表里的 pending/running」
- 加边之后只多一个 **ready 条件**（deps 完成才能出队）
- **不要**为扩展性先做拓扑排序引擎；无边时 FIFO + 单飞足够
- 「rolling 需要已有 simulate 产物」优先用 **启动前置检查**，不必建成任务边

### 3.4 崩溃与 hang

列表必须可纠正，否则 UX 不可信：

| 情况 | 行为 |
|------|------|
| 持有进程已死 | 标 `failed`/`stale`，释放执行槽，调度下一条（沿用 pid 存活检查） |
| 进程仍在但长时间无进度心跳 | 标 `stale` / 提示；是否允许用户「放弃」另定 |

---

## 4. 前后端契约（间接汇报）

```text
[业务 Run 按钮] → BFF submit → JobPipeline.submit(spec)
                                      ↓
                              任务表 +（内部）真正开跑
                                      ↓
[全局管道 UI / 完成 toast] ← BFF list/get ← JobPipeline.list_jobs / get_job
```

- **互斥是管道内部政策**；前端只读任务表。
- 全局管道列表 = 表中活跃任务（串行期 0～1 条 running + 若干 pending）；完成未查看时由 FED 本地「未读完成」缓冲展示（toast + 坞内「查看」），看过即消。
- 制定策略页进页发现在跑任务：读 list/get，**不依赖** `sessionStorage` 作为真相（最多当缓存）。

---

## 5. 迁移阶段

1. **骨架 + 本设计**（已完成）
2. **只读面**（已完成）：`get_running_job` / `list_jobs` 读自管 running 槽；`Progress.read(job_id)` 摘要可挂到快照。不在 infra 拉 `modules.*`。
3. **BFF + FED**（已完成）：`GET /v1/runtime/pipeline`；FED `JobPipelineWatch` 静默轮询 + 完成 toast/link；制定策略页可从管道跨 tab 接管 `strategy_run`。
4. **submit 入队**（已完成）：各 launcher 公开入口只校验后调 `JobPipeline.submit`；handler 调 `start_now` 真正开跑；结束 `notify_job_finished`→`advance`；队列上限 8。
5. **FED 管道坞**（已完成）：左下角入口常驻；展开显示活跃任务（running/pending）+ 前端「未读完成」缓冲；仅 pending 可取消（running 不提供取消按钮）；完成行显示「查看」，点开或已在目标页即消，不保留真历史。
6. **自管互斥**（已完成）：`job_pipeline_running.json` + `filelock`；`JobPipeline.running_lease`；running 协作取消；任务快照可挂细进度。`task_guard` 已删除；`progress` 继续作为明细进度库。

**已补：** 死 pid 在读面 `recover` 时清槽并 `advance`；有 Progress 时 `updated_at` 超过 2h 无写入标 `stale`（无 Progress 时墙钟 12h 兜底，避免长跑误伤）；坞仅对 stale 显示「放弃」。

**仍另定：** 资源级并行锁 / 依赖边。

---

## 6. 结论摘要（讨论拍板）

1. 长任务应有 **统一登记表**；前端只与表交互。
2. 第一期用 **有上限串行队列** 替代「忙则拒绝」，是明确的产品与模型进步。
3. 扩展靠 **资源锁 + 队列政策**；**依赖边** 可后加；**不要**先上 DAG / 拓扑排序。
4. `infra.job_pipeline` 负责互斥与任务发现；`progress` 仍负责细进度读写。
5. UX（跨 tab 可见、完成后 toast + link）挂在任务表上，不另造通知总线依赖租约。
6. **自建**管道；不上重型队列/工作流库。跨进程锁 **优先 `filelock`**（DEC-06）。
