# Post Process — 设计与决策

**版本：** `0.3.2`

本文记录本模块的设计目标、方案思路与拍板决策。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

为扫描出口提供 userspace 可扩展的后续处理能力：userspace 扩展布局、动态加载、以及与策略 `PostProcessDispatcher` 的协作。扩展的启用是全局的，不进策略 settings。

## 方案与思路

**userspace 目录约定**：

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

**运行时**：

1. Scanner 产出内部机会列表
2. `PostProcess.build_session_report` → `ScanSessionReport`
3. `PostProcess.run_enabled_post_processors(session)` → 对每个 enabled PostProcessor 拓扑执行

Component **共享同一份** session；`depends_on` 仅注入依赖方的 **return**（`deps` map），不改写标准协议。

---

## DEC-01：协议与编排分离

**是什么：** 三层协议只描述扫描出口；干活在 Component。

**放弃了什么：** 把协议字段直接塞进 Component 的输出里

## DEC-02：PostProcess 不是 pipeline

**是什么：** 声明无序；执行序仅由依赖拓扑决定。

**放弃了什么：** 把 Component 做成流水线、前一步输出作为下一步输入

## DEC-03：一策略一份 StrategyScanReport

**是什么：** 多策略联合扫描时，每个策略一份 StrategyScanReport，会话顶层用 ScanSessionReport.strategies 集合。

**放弃了什么：** 把所有策略机会扁平成一份大报告

## DEC-04：不兼容旧 adapters 目录

**是什么：** 过时的 BaseOpportunityAdapter / scanner.adapters 已删除；所有后续处理走 PostProcess Dispatcher。

**放弃了什么：** 为旧 adapters 目录保留兼容层

## DEC-05：扫描页 UI 先写死 presenter（非插件系统）

**是什么：** 扫描结束后若某 enabled 方案跑过 `presenter` adapter，将其 return 写入

`report.post_process.ui.scan_report = { view: "presenter", props: <presenter return> }`。

FED 扫描页用 **写死分支**（`view === "presenter"`）渲染 `PresenterScanReport`，替换默认「扫描报告 / 机会明细」。未跑后处理、未挂 presenter、或 `run_post_process=false` 时 **无 ui 载荷**，保持默认 UI。

**写死入口（改这里时搜 SPECIAL-CASE DEC-05）：**

- 后端：`post_processor_executor.ui_contributions_from_outputs`（按 adapter 名 `presenter` 抽取）
- 前端：`containers/scan/presenterScanReport` + `scan.js` 中 `readPresenterScanUi`

**放弃了什么（本迭代）：** SSR HTML；通用 JSON 模板引擎；点击时再探测「有没有 presenter」。

**演进条件：** 再出现 **第二个** 会改变前端渲染的 adapter / model 时：

1. 把 `post_process.ui.<slot> = { view, props }` 收成版本化前后端契约；
2. 在 FED 放置解析/渲染引擎（view 注册表或声明式模板）；
3. 废掉对 `presenter` 字符串的特殊分支。

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
