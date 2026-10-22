# Adapter 设计说明

**版本：** `0.3.0`

userspace 扩展布局、动态加载、以及与策略 `PostProcessDispatcher` 的协作。

**相关文档**：[架构总览](./ARCHITECTURE.md) · [出口协议](./PROTOCOL.md) · [后续处理](./POST_PROCESS.md)

---

## userspace 目录约定

```text
userspace/extensions/
├── components/<name>/
│   ├── adapter.py      # BaseAdapter 子类
│   └── settings.py       # 可选
└── post_processes/<key>/
    └── post_process.yaml
```

启用（全局，不在策略 settings）：

```yaml
# post_processors/presenter/post_processor.yaml
is_enabled: true
```

---

## 运行时

1. Scanner 产出内部机会列表  
2. `PostProcess.build_session_report` → `ScanSessionReport`  
3. `PostProcess.run_enabled_post_processors(session)` → 对每个 enabled PostProcessor 拓扑执行  

Component **共享同一份** session；`depends_on` 仅注入依赖方的 **return**（`deps` map），不改写标准协议。

---

## 设计决策

1. **协议与编排分离** — 三层协议只描述扫描出口；干活在 Component。  
2. **PostProcess 不是 pipeline** — 声明无序；执行序仅由依赖拓扑决定。  
3. **一策略一份 StrategyScanReport** — 多策略用 `ScanSessionReport.strategies`。  
4. **不兼容旧 adapters 目录** — 过时 `BaseOpportunityAdapter` / `scanner.adapters` 已删除。  
