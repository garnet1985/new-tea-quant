# 命令行布局 — 设计

**版本：** `0.2.0`

记录跨平台 ASCII 默认、门面导出、图标回退与标题层级等选型。术语见 [glossary.yaml](../glossary.yaml)。相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计点 1：条形与分割线默认纯 ASCII

### 设计初衷

终端报告要在 Windows / Linux / macOS 上稳定可读，避免乱码。

### 设计背景

部分环境（如 Windows GBK 控制台）对方块、盒线支持差，曾出现乱码。

### 解决方案

| 方案 | 做法摘要 | 优点 | 缺点 |
|------|----------|------|------|
| A：Unicode 美观字符 | 方块 / 盒线 | 观感好 | 跨平台脆弱 |
| B：默认 ASCII（`#` / 空格 / `-` `=` `*`） | 填充与分割只用常见字符 | 稳定 | 观感朴素 |

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）## 设计点 2：只导出门面类 `CmdLayout`

### 设计初衷

符合核心模块「单一门面」约定。

### 设计背景

历史上 `__init__` 曾再导出 `IconService` 与快捷函数 `i`，形成多入口。

### 解决方案

| 方案 | 做法摘要 | 优点 | 缺点 |
|------|----------|------|------|
| A：继续导出 IconService / i | 兼容旧 import | 迁移少 | 多真源 |
| B：只导出 `CmdLayout` | 图标走 `CmdLayout.icon.*` | 契约清晰 | 调用方改 import |

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）## 设计点 3：图标 emoji / ASCII 回退

### 设计初衷

在支持的终端显示直观图标，在不支持时仍给出可读标签。

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）## 设计点 4：连续样本走等宽分桶再渲染

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）## 设计点 5：标题四级 h1 / h2 / h3 / h4

### 设计初衷

策略报告曾混用 `banner` + `separator` + `-- section --`，层级不清。

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
