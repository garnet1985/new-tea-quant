# UI 架构

**模块：** `ui` · **版本：** `0.2.3`

浏览器里的 NTQ。React 应用在 `fed/`。HTTP 在 [`core/bff`](../../bff/README.md)，不在本模块。

API 不在这里。安装门面见 `core/infra/setup`，路由见 `core/bff/docs`。

---

## 职责与边界

**负责**

- 页面、导航、设置表单和报告展示
- 全页引导的目录与挖洞（关闭账本由 BFF 写入 userspace）

**不负责**

- 策略、标签、数据的计算与落盘
- 安装状态机（`launcher.py` 与 `infra.setup`）

---

## 结构

```text
core/ui/
├── README.md
├── module_info.yaml
├── docs/
└── fed/src/
    ├── app.js                 # 路由
    ├── components/            # 导航、引导、图表
    ├── pages/                 # 制定策略、选股、高级功能、设置、Setup
    └── api/                   # 调 BFF
```

生产构建产物在 `fed/build`，由 BFF 静态托管。

---

## 主导航

- **制定策略** `/strategy-design`：策略列表，以及单策略四步（枚举机会、价格回测、投资模拟、决策模拟）。
- **策略选股** `/scan`。
- **高级功能**：特征标签 `/advanced/tags`、数据源 `/advanced/data-sources`、数据契约 `/advanced/data-contracts`。`/advanced` 进入标签页。适配器、库表、备份不在这里。
- **设置** `/settings`。首次安装完成后，数据库等全局配置在这里维护。

不在主导航里：

- Logo 回到欢迎页 `/welcome`。
- Setup 只在必要配置缺失时把业务页送到 `/setup`，不是常驻入口。
- 决策模拟是制定策略第四步，依赖枚举机会和投资模拟都完成，价格回测不是前置。跨策略一本账不在这一步。

旧路径转到现行入口：`/strategy-workbench`、`/decision`、`/decision/play` 到制定策略；`/tags` 到 `/advanced/tags`。
