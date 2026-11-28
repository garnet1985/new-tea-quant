# 命令行布局 — 设计与决策

**模块：** `infra.cmd_layout` · **版本：** `0.3.0`

**最低支持核心版本：** `>=0.5.0`

本文记录本模块的设计目标、方案思路与拍板决策。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 设计目标

- **跨平台可读**：Windows / Linux / macOS 稳定可读，避免乱码
- **单一门面**：对外以 `CmdLayout` 为主；包根 `i` 为图标短入口例外
- **标题层级清晰**：固定 h1–h4，不再混用旧 banner / separator / section
- **预留完整能力保留**：如 `from_values`、未调用但字形完整的图标；不完整或与现行能力重复的入口删除

## 方案与思路

条形与分割曾在 Unicode 美观字符与纯 ASCII 间权衡，最终默认 ASCII（DEC-01）。  
门面曾导出 `IconService` 等多入口，收口为 `CmdLayout` + 短入口 `i`（DEC-02）。  
标题由混排改为四级 h1–h4（DEC-05）；0.3.0 起删除已被替代的兼容入口（DEC-06）。

---

## DEC-01：条形默认纯 ASCII

- **是什么：** 条形填充用 `#` / 空格
- **为什么选它：** 优先可读与可移植
- **放弃了什么：** Unicode 方块填充

---

## DEC-02：只导出门面 + 短入口 `i`

- **是什么：** `__all__ = ["CmdLayout", "i"]`；图标走 `CmdLayout.icon.*` 或 `i`
- **为什么选它：** 符合单一门面；`i` 在 CLI 使用极广，作为有文档的例外保留
- **放弃了什么：** 再导出 `IconService` 等实现类

---

## DEC-03：图标 emoji / ASCII 回退

- **是什么：** `supports_emoji` + 双表
- **为什么选它：** 与条形 ASCII 策略一致
- **放弃了什么：** 调用方自行分支字形

---

## DEC-04：连续样本走等宽分桶再渲染

- **是什么：** `from_values` 模块内等宽分桶
- **为什么选它：** 完整预留直方图能力；复杂分桶仍可自建后 `render`
- **放弃了什么：** 另立 `CmdLayout.histogram`

---

## DEC-05：标题四级 h1 / h2 / h3 / h4

- **是什么：** 固定四级标题语义
- **为什么选它：** 替代混用 banner + separator + section
- **放弃了什么：** 调用方自由拼规则线当标题

---

## DEC-06：删除已被替代的兼容面（0.3.0）

- **是什么：** 删除 `title.banner` / `section`、整包 `separator`、图标 `ALIASES`
- **为什么选它：** banner≈h1、section≈h3；separator 无生产调用且与标题层级重复；别名是兼容垫片
- **放弃了什么：** 旧 import / 旧图标昵称；调用方改用 h1–h4 与正式图标名
- **保留：** 完整未用图标字形；`from_values` 直方图预留

---

## 相关文档

- [架构](./ARCHITECTURE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
