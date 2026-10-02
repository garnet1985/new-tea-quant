# 命令行布局 — 架构

**版本：** `0.2.0`

为终端报告提供纯文本排版片段：标题层级、分割线、表格、行内文本、图标、水平条形图。对外唯一入口为门面类 `CmdLayout`。词条见 [glossary.yaml](../glossary.yaml)。

---

## 职责与边界（结论）

**负责**

- 门面类 `CmdLayout` 与命名空间：`bar_chart` / `title` / `separator` / `table` / `text` / `icon`
- 生成可打印字符串（及可选直接打印到流）
- 跨平台默认：条形 / 分割 / 表线用 ASCII；图标按终端能力在 emoji 与 ASCII 间切换

**不负责**

- 策略报告业务内容与指标计算（调用方组装）
- GUI / Web 图表组件
- 把内部实现类（`Title`、`BarChart`、`IconService` 等）作为跨模块公开 import 面
- 进度条产品（无 `progress` 命名空间）

---

## 模块结构图

```text
core/infra/cmd_layout/
├── cmd_layout.py          # 门面类 CmdLayout
├── __init__.py            # 仅导出 CmdLayout / i
├── API.md
├── QUICKSTART.md
├── glossary.yaml
├── module_info.yaml
├── shared/                # StreamWriter 等共用脚手架
├── bar_chart/
│   └── __test__/
├── title/
│   └── __test__/
├── separator/
│   └── __test__/
├── table/
│   └── __test__/
├── text/
│   └── __test__/
├── icon/
│   └── __test__/
├── __test__/              # 公开 API（test_api.py）
└── docs/
    ├── ARCHITECTURE.md
    └── DESIGN.md
```

---

## 架构图

```text
调用方（strategy report / setup / …）
        │
        ▼
   CmdLayout（门面 / Facade）
   ├── bar_chart → 分布 / 直方图字符串
   ├── title     → h1 / h2 / h3（及兼容 banner / section）
   ├── separator → line / thick / star / blank
   ├── table     → ASCII 对照表
   ├── text      → meta / kv / indent / numbered / bullets
   └── icon      → get / i / supports_emoji
```

```mermaid
flowchart LR
  Caller --> CmdLayout
  CmdLayout --> BarChart
  CmdLayout --> Title
  CmdLayout --> Separator
  CmdLayout --> Table
  CmdLayout --> Text
  CmdLayout --> Icon
```

---

## 数据流（若有）

```text
分桶或连续样本 / 标题文本 / 表头行 / 图标名
  → CmdLayout.<namespace>.*
  → str（可选 print 到 stdout 或指定 stream）
```

---

## 依赖（结论）

- 无模块级 YAML 依赖

---

## 相关文档

- [README](../README.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
- [设计](./DESIGN.md)
- [快速开始](../QUICKSTART.md)
