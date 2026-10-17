# Progress — 架构

**版本：** `0.1.0`

本模块只保存当前任务的步骤计数。业务模块在自己的生命周期里调用门面，界面和 PHP 读取同一份文件。

---

## 职责与边界（结论）

**负责**

- 把当前任务的步骤和子步骤写入临时目录里的一个文件
- 提供读取和同一条比例式

**不负责**

- 不解释步骤在业务上是什么
- 不保存错误、结果或机会列表
- 不保留上一份任务的历史

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
│   └── store.py
└── docs/
    ├── ARCHITECTURE.md
    └── DESIGN.md
```

---

## 架构图

```text
安装 / 回测 / 扫描 / 归因 / 数据源 / 标签
   → Progress
        → userspace/.ntq/tmp/progress.json
界面 / PHP
   → Progress.read()
```

---

## 数据流（若有）

```text
open
  → step（已完成步骤，子步骤清零）
  → sub（当前步骤内的计数）
  → close（步骤收到总数）
```

---

## 依赖（结论）

- `infra.project_context`：定位 userspace 临时目录

---

## 相关文档

- [README](../README.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
- [设计](./DESIGN.md)
- [快速开始](../QUICKSTART.md)
