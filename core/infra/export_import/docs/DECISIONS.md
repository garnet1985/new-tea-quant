# infra.export_import — 决定

**版本：** `0.2.0`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：D1：stdlib zip 为唯一实现

去掉系统 `zip` 双路径，保证跨平台行为一致；目录条目由实现显式写入。

---

## DEC-02：D2：实现一律类方法，门面薄委托

公开只经 `ExportImport.*`；不导出模块级自由函数。


## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
