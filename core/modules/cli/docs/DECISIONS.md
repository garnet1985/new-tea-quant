# modules.cli — 决定

**版本：** `0.4.5`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：设计点 1：双入口，不合成一个二进制

- **采用：** 方案 B
- **理由：** 受众与别名表本就不该强行合并
- **影响：** 调用方记住两个入口；实现共享 `Cli.shared`

---

---

## DEC-02：设计点 2：只导出（export）门面类 `Cli`

- **采用：** 方案 B
- **理由：** 对齐核心模块准则；测试只钉门面类
- **影响：** 无函数式兼容层

---

---

## DEC-03：设计点 3：shared 是 namespace，不是独立产品

- **采用：** 方案 B
- **理由：** shared 只服务双入口，不是第三套 CLI
- **影响：** 公开面仍只有 `Cli`

---

---

## DEC-04：设计点 4：删除 `infra.devcli` 与无兼容层

- **采用：** 方案 B
- **理由：** 核心模块不保留向后兼容 proxy
- **影响：** 一律 `from core.modules.cli import Cli`

---

---

## DEC-05：设计点 5：短别名与 bootstrap 行为

- **采用：** 方案 B
- **理由：** 与双入口决策一致
- **影响：**
  - 首 token 在表中则替换为长命令，再交 argparse；空 argv / `-v` / `--version` → `version`
  - dev 的 `pack` 可经 `after_expand` 支持 `-core_vX.Y.Z` → `--version X.Y.Z`
  - pack 以各模块 `module_info.yaml` 为版本 SSOT：检查 `name`、changelog、文档文首 `**版本：**` / `# Version:` / `最低支持核心版本`；非 `--check-only` 时按 SSOT 改写文首
  - user bootstrap：非 venv 且存在 `venv/` 时 `os.execv` 重入；非 early 命令按需 `install.py`；early 含 `update` / `version` / 策略 import|export、help、`-n` 新建等

---


## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
