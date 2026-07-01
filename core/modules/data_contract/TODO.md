# Data Contract — 待修正项

## 缓存 API 漂移（需修正）

**状态：** 未做  
**优先级：** 中（影响 Strategy / Tag 串 run 重复 load、与文档心智不一致）

### 设计意图（[`docs/DECISIONS.md`](docs/DECISIONS.md) 决策 1 / 4）

- 对外主入口 **`DataContracts.issue` / `load`**；cache 对调用方 **黑盒**。
- **GLOBAL**：默认 **cache**；**PER_ENTITY**：默认 **不 cache**（用户不可配）。
- **GLOBAL 可缓存数据**：`issue(load=true)` / `load` 后 `data` 已加载；是否命中 cache 内部决定。

### 目标形态（修正方向）

1. **`DataContracts()` 默认自带 cache**（进程级 lazy store）：
   - **PER_ENTITY** → 内部不 cache（静默）
   - **GLOBAL** → cache（`cache_enabled=False` 仅单测关闭 GLOBAL cache）
2. **用户不可控制 PER_ENTITY cache**；API 若暴露显式请求（如 override 含 cache 键 + PER_ENTITY）→ `ValueError`；无暴露则不报错。
3. **不可注入** `ContractCacheManager`。
4. **下游**：Strategy / Tag 停止 per-call `ContractCacheManager()`，改用 `DataContracts()` + run 边界清理。

### 不在此项范围内

- **跨进程** worker 缓存：spawn 子进程 **不继承** 进程内 store；仍由 Strategy / Tag 编排层 **`global_data` preload**（或未来 shared memory）解决，与本次 DCM 黑盒 cache 正交。

### 验收

- [ ] 同进程、两次 `issue(同一 GLOBAL data_key + 窗 + params)`，**不**注入 manager 时第二次不触库。
- [ ] `cache_enabled=False` 时两次均触库（或等价可观测行为）。
- [ ] 决策 1 / 5 文档更新，消除「必须注入 `ContractCacheManager`」与「issue 黑盒 cache」的矛盾表述。
- [ ] Strategy preload 路径不再为「复用 cache」而依赖临时 new manager。
