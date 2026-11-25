# <Module Display Name> — 架构

**模块：** `<namespace.module_name>` · **版本：** `<module.version>`

**最低支持核心版本：** `<compatible_core_versions>`
<!-- 只写已定结论；选型过程 → DECISIONS（若有） -->
<!-- 图示：架构图必须 mermaid；目录树 / 短步骤用 text。见 module-doc-standard §3.1 -->

`<1～3 句：模块在系统中的位置、对外提供什么能力。>`

---

## 职责与边界（结论）

**负责**

- `<已确定由本模块负责的能力>`

**不负责**

- `<明确不做、由谁负责>`

---

## 模块结构图

```text
<module_root>/
├── <module_file>.py
├── contracts.py
├── API.md
├── glossary.yaml
├── module_info.yaml
├── __test__/
├── __performance__/           # 可选
├── core/
│   └── <pkg>/
└── docs/
    ├── ARCHITECTURE.md
    ├── DECISIONS.md           # 可选
    ├── USER_GUIDE.md
    ├── CONCEPTS.md            # 可选
    └── notes/
```

---

## 架构图

```mermaid
flowchart LR
  Caller --> Facade
  Facade --> CompA
  Facade --> CompB
```

---

## 数据流（若有）

短步骤可用 `text`：

```text
<input>
  → <step 1>
  → <step 2>
  → <output / store>
```

有分支或并行时改用 Mermaid（同「架构图」语法）。

---

## 依赖（结论）

- `<dep.name>`：`<用途>`

---

## 相关文档

- [README](../README.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
- [设计与决策](./DECISIONS.md)<!-- 若无则删 -->
- [用户指南](./USER_GUIDE.md)
- [概念](./CONCEPTS.md)<!-- 若无则删 -->
- [快速开始](../QUICKSTART.md)<!-- 若无则删 -->
