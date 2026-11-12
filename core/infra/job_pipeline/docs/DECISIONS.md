# Job Pipeline — 设计与决策

**版本：** `0.1.0`

本文记录本模块的设计目标、方案思路与拍板决策。  
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

用单一长任务 infra 统一「能不能跑 / 队列里还有谁 / 任务级摘要」，让前端只读任务表；细进度继续用 `infra.progress`。

- 替代「忙则硬拒」：有上限串行入队
- 替代旧单文件互斥包：自管 running 槽 + `filelock`
- 跨 tab / 回页可发现长任务；完成后由 FED 本地未读缓冲提示
- 挂死可纠正：死 pid 自动清槽泵队列；无进度心跳可标 stale 并允许放弃

**第一期不做：** 条件并行、依赖图 / DAG、分布式队列、自动重试业务中间态。

---

## 方案与思路

候选过：扩写 `Progress` 挂 lease、只把旧互斥模块扩成队列、引入 Celery/Prefect。最终新建 `infra.job_pipeline`：任务表 + 串行队列是产品契约，与进度树、旧租约语义不同；进度库多处直接依赖，不宜私有化。现状结构见 [ARCHITECTURE.md](./ARCHITECTURE.md)。

迁移已完成：只读面 → BFF/FED 坞 → submit 入队 → 自管互斥并删除旧互斥包 → 死 pid recover + stale/abandon。仍另定：资源级并行锁、依赖边。

---

## DEC-01：新建模块而非扩写 Progress / 旧互斥模块

**是什么：** 新建 `infra.job_pipeline`，包根门面 `JobPipeline`。

**为什么选它：** 对外契约是「任务表 + 队列」，与 Progress 树 API、旧单文件租约语义不同；独立模块避免把队列塞进进度或旧互斥门面。

**放弃了什么：** 在 `Progress` 上直接挂 lease；或只把旧互斥模块扩成队列。

---

## DEC-02：第一期串行队列，忙则入队

**是什么：** 全局同时 `running` 至多 1；新提交进 `pending`，队列有上限，满则拒绝。

**为什么选它：** 相对「忙则拒绝」明显改善 UX，且表结构自然支持以后的 locks 并行与 `depends_on` ready。

**放弃了什么：** 第一期就做 strategy∥tag 条件并行。

---

## DEC-03：扩展性用资源锁；不做执行 DAG

**是什么：** 预留 per-job `locks` / 冲突政策；依赖边以后按需加。无边时不跑拓扑排序。

**为什么选它：** 「能不能一起跑」是互斥问题；「B 等 A 产物」多数可用启动前置检查。Airflow 式图对当前产品过重。

**放弃了什么：** 一上来上依赖图调度器。

---

## DEC-04：按调用点逐步迁移，最后删除旧对外 API

**是什么：** 先接只读任务表与 launcher 入队 → 自管 running 槽与 `filelock` → 删除旧互斥模块。`progress` 始终保留为进度明细库。

**为什么选它：** 降低一次性重写风险；FED/BFF 可先吃新读面；细进度调用面不必搬迁。

**影响：** 旧互斥包已删除；无兼容 shim。

---

## DEC-05：挂死必须纠正任务表

**是什么：** 进程死或长时间无进度写入时，表内状态必须更新并可释放执行权。

**为什么选它：** 否则全局管道与「完成后提示」不可信。

**落地：** 死 pid → `recover` 清槽并 `advance`；有 Progress 时 `updated_at` 超过 2h 标 `stale`（无 Progress 时墙钟 12h）；产品坞仅对 stale 暴露「放弃」。

---

## DEC-06a：只读主 API 为 `get_running_job`

**是什么：** BFF/FED 日常用 `get_running_job() -> None | job`；`has_running_job` 为薄封装；`list_jobs` 留给队列（pending 多条）可见时。

**为什么选它：** 纯 bool 无法跨 tab 接管与完成跳转；串行期「0 或 1 条 running」用单对象最省事。

**放弃了什么：** 只暴露 `has_running_job: bool` 作为唯一读面。

---

## DEC-06：互斥锁优先用 `filelock`；管道自建

**是什么：** 整体任务表 / 队列 **自建** `job_pipeline`，不上 Celery/Prefect 一类全家桶。跨进程互斥 **优先 [`filelock`](https://github.com/tox-dev/py-filelock)**。细进度仍用现有 `infra.progress`，不把进度树引擎重写进管道。

**为什么选它：**

- 单机文件锁场景 `filelock` 更简单、跨平台行为清楚，少维护自研锁边角
- 队列、任务表、BFF 读面是产品特定；进度树已有独立模块且多处直接依赖

**放弃了什么：**

- 引入 Celery / RQ / Huey / Prefect 等带 broker 的调度栈
- 继续维护自研单文件 lease JSON 协议
- 删除或私有化 `progress`（外部业务页仍需直接读进度）

**落地：** `filelock` 已写入 `requirements.in`；`JobPipeline.running_lease` + `registry_store` 为自管槽；旧互斥包已删除。

---

## DEC-07：产品坞仅取消 pending；僵死用放弃

**是什么：** 正常 `running` 不提供取消按钮；仅 `pending` 可取消；`stale` 可「放弃」强制清槽。

**为什么选它：** 协作取消对正在跑的重任务体验差且难保证立即退出；僵死才需要用户强制释放管道。

**放弃了什么：** 坞上对 running 暴露「取消 / 取消中」。

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
