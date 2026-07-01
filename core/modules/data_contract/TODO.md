# Data Contract — 待修正项

## 缓存 API 漂移（需修正）

**状态：** 未做  
**优先级：** 中（影响 Strategy / Tag 串 run 重复 load、与文档心智不一致）

### 设计意图（[`docs/DECISIONS.md`](docs/DECISIONS.md) 决策 1 / 4）

- 对外主入口仅为 **`DataContractManager.issue(...)`**。
- **GLOBAL 可缓存数据**：`issue` 后 **`data` 应已物化**；是否命中缓存 **由 DCM 内部决定**，调用方 **不区分** 缓存分支。
- 缓存对业务层应是 **黑盒**：默认 **开启**；仅在 init 时通过 **开关** 关闭（测试、强制冷 load 等）。

### 当前实现（漂移）

- `DataContractManager.__init__` **强制**注入 `ContractCacheManager`，模块内 **无** 进程默认 store。
- Strategy / Tag 等调用方普遍 **`ContractCacheManager()` 临时 new**，导致：
  - 同进程串行多次 run **无法**自动复用 GLOBAL cache（与决策 1 文案不符）；
  - 调用方误以为要「分开管理 cache」，与 `issue` 黑盒语义冲突。
- [`docs/DECISIONS.md`](docs/DECISIONS.md) 决策 5 要求 **`enter_strategy_run` / `clear_global` 由应用编排** —— 这是 **生命周期清理**，不应等同于 **每次 new 一个空 store**。

### 目标形态（修正方向）

1. **`DataContractManager` 默认自带 cache**（进程级 lazy 单例或等价机制）：
   - `DataContractManager()` → GLOBAL `issue` **默认读写 cache**；
   - `cache_enabled=False`（或 `NullContractCache`）→ 关闭缓存，便于单测。
2. **可选注入** `contract_cache`：Workbench / simulate **Session**、集成测试需要共享或隔离 store 时使用（高级用法，非默认路径）。
3. **文档与实现对齐**：README / API 示例不再把「每次 new `ContractCacheManager`」当作常规用法；决策 1 与决策 5 分工写清：
   - **黑盒 cache** = DCM 内部 + 默认 store；
   - **应用职责** = run 边界 `enter_strategy_run` / `exit_strategy_run` / `clear_global`，而非每次新建 manager。
4. **下游调用方跟进**（修正 DCM 后）：
   - Strategy `GlobalDataPreloader` / `EntityDataLoader`：停止默认 per-call `ContractCacheManager()`；Session 级注入或依赖 DCM 默认 store。
   - Tag `TagManager`：可简化为复用 DCM 默认 store + 显式 session 清理，或继续注入同一实例（二选一，文档统一）。

### 不在此项范围内

- **跨进程** worker 缓存：spawn 子进程 **不继承** 进程内 store；仍由 Strategy / Tag 编排层 **`global_data` preload**（或未来 shared memory）解决，与本次 DCM 黑盒 cache 正交。

### 验收

- [ ] 同进程、两次 `issue(同一 GLOBAL data_key + 窗 + params)`，**不**注入 manager 时第二次不触库。
- [ ] `cache_enabled=False` 时两次均触库（或等价可观测行为）。
- [ ] 决策 1 / 5 文档更新，消除「必须注入 `ContractCacheManager`」与「issue 黑盒 cache」的矛盾表述。
- [ ] Strategy preload 路径不再为「复用 cache」而依赖临时 new manager。
