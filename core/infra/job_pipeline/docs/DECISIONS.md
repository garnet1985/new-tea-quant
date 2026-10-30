# Job Pipeline — 设计与决策

**版本：** `0.1.0`

实现前的拍板记录。完整叙述见 [DESIGN.md](./DESIGN.md)；架构草图见 [ARCHITECTURE.md](./ARCHITECTURE.md)。

---

## 设计目标

用单一长任务 infra 统一「能不能跑 / 跑到哪了 / 队列里还有谁」，让前端只读任务表，并绞杀退役 `task_guard` 与对外 `progress`。

---

## DEC-01：新建模块而非扩写 Progress / TaskGuard

**是什么：** 新建 `infra.job_pipeline`，包根门面 `JobPipeline`。

**为什么选它：** 对外契约是「任务表 + 队列」，与现有 Progress 树 API、TaskGuard 租约 API 语义不同；新模块便于绞杀期双轨，避免把队列塞进旧门面造成永久歧义。

**放弃了什么：** 在 `Progress` 上直接挂 lease；或只扩 `TaskGuard` 成队列。

---

## DEC-02：第一期串行队列，忙则入队

**是什么：** 全局同时 `running` 至多 1；新提交进 `pending`，队列有上限，满则拒绝。

**为什么选它：** 相对今日 deny-only 明显改善 UX，且表结构自然支持以后的 locks 并行与 `depends_on` ready。

**放弃了什么：** 第一期就做 strategy∥tag 条件并行。

---

## DEC-03：扩展性用资源锁；不做执行 DAG

**是什么：** 预留 per-job `locks` / 冲突政策；依赖边以后按需加。无边时不跑拓扑排序。

**为什么选它：** 「能不能一起跑」是互斥问题；「B 等 A 产物」多数可用启动前置检查。Airflow 式图对当前产品过重。

**放弃了什么：** 一上来上依赖图调度器。

---

## DEC-04：绞杀迁移，最后退役旧模块

**是什么：** 先适配 TaskGuard + Progress → 迁 launcher → 换心 → 删旧对外 API。

**为什么选它：** 降低一次性重写风险；FED/BFF 可先吃新读面。

---

## DEC-05：挂死必须纠正任务表

**是什么：** 进程死或长时间无心跳时，表内状态必须更新并释放执行权。

**为什么选它：** 否则全局管道与「完成后提示」不可信；继承并强化 TaskGuard 的 pid 存活检查思路。

---

## DEC-06a：只读主 API 为 `get_running_job`

**是什么：** BFF/FED 日常用 `get_running_job() -> None | job`；`has_running_job` 为薄封装；`list_jobs` 留给队列（pending 多条）可见时。

**为什么选它：** 纯 bool 无法跨 tab 接管与完成跳转；串行期「0 或 1 条 running」用单对象最省事。

**放弃了什么：** 只暴露 `has_running_job: bool` 作为唯一读面。

---

## DEC-06：互斥锁优先用 `filelock`；管道自建

**是什么：** 整体任务表 / 队列 / 进度视图 **自建** `job_pipeline`，不上 Celery/Prefect 一类全家桶。换心阶段的跨进程互斥，**优先采用成熟的 [`filelock`](https://github.com/tox-dev/py-filelock)**（`FileLock`），而不是继续手写租约文件协议（现行 TaskGuard 那套可在绞杀期暂时委托）。

**为什么选它：**

- 单机文件锁场景 `filelock` 更简单、跨平台行为清楚，少维护自研锁边角
- 队列、任务表、进度形状、BFF 读面仍是产品特定，没有合适的一站式库

**放弃了什么：**

- 引入 Celery / RQ / Huey / Prefect 等带 broker 的调度栈
- 换心后仍长期维护自研 lease JSON 协议（除非 `filelock` 实测不够用再回退）

**注意：** 依赖尚未写入 `requirements.txt`；真正换心实现时再加，并补测试。
