# Progress — 架构

**版本：** `0.2.1`

本模块把进度写成文件。根节点和每一层 steps 是同一种节点。界面和 PHP 读文件里的 ratio。另提供无业务语义的频道快照（`Progress.channel`），供策略 / 标签等模块约定自己的 channel 名。

---

## 职责与边界（结论）

**负责**

- 按节点 id 更新进度树，并写入 `userspace/.ntq/tmp/progress/{根id}.json`
- 频道化 job 快照：`progress/{channel}/{file_key}.json`（`Progress.channel`）
- 在写入时算好每个节点的 ratio
- tick 时打一行日志
- 读取最新内容；合并短时间内的重复写盘

**不负责**

- 不保存任务结果、机会列表或失败日志
- 不替调用方决定业务步骤的含义
- 不在内部用定时器把进度往前推
- 不定义 strategy / tag 等业务 channel 名（见 [DEC-04](./DECISIONS.md#dec-04)）

---

## 模块结构图

```text
core/infra/progress/
├── progress.py
├── contracts.py
├── API.md
├── glossary.yaml
├── module_info.yaml
├── __test__/
├── core/
│   ├── store.py
│   └── channel_store.py
└── docs/
    └── ARCHITECTURE.md
```

---

## 架构图

```text
业务 tick / finish / fail
   → Progress
        → userspace/.ntq/tmp/progress/{根id}.json
业务 job 快照（自定 channel）
   → Progress.channel
        → userspace/.ntq/tmp/progress/{channel}/{file_key}.json
界面 / PHP / BFF
   → Progress.read / Progress.latest / Progress.channel.read
```

---

## 数据流（若有）

```text
start
  → tick（叶子计数，父节点 ratio 向上重算）
  → finish / fail / cancel / pause / resume
  → clear

channel.write / read / clear（即时落盘，无树形 ratio）
```

同一次根上的连续 tick 先改内存，再合并写盘。`read` 和 `latest` 读内存里的最新树。

测试可设 `NTQ_PROGRESS_DIR` 指向进度目录（树与 channel 共用）。

---

## 依赖（结论）

- `infra.project_context`：定位 userspace 临时目录

---

## 相关文档

- [用户指南](./USER_GUIDE.md)
- [README](../README.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
- [快速开始](../QUICKSTART.md)
- [决策](./DECISIONS.md)
