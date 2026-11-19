# CLI（`modules.cli`）

**模块：** `modules.cli` · **版本：** `0.4.5`

**最低支持核心版本：** `>=0.5.0`

## 简介

命令行入口。两套独立入口：`cli.py` 给普通用户用（跑扫描、模拟、更新等），`devcli.py` 给开发者用（打包、检查、清理、生成样本等）。对外统一走 `Cli` 门面类。

## 适用场景

- 从仓库根用 `cli.py scan` 跑策略扫描，或 `cli.py simulate` 跑回测
- 从仓库根用 `devcli.py pack` 打包发布，或 `devcli.py check` 做代码质量检查
- 在自己的脚本里 import `Cli` 复用命令解析逻辑

## 模块依赖

- `infra.cmd_layout`：终端输出样式（进度条、表格、图标）
- `infra.db`：数据库操作
- `infra.project_context`：路径与配置
- `infra.setup`：安装编排
- `infra.job_pipeline`：长任务互斥与队列
- `infra.trace`：匿名上报
- `infra.utils`：通用工具
- `modules.agent`：AI 助手
- `modules.data_contract`：声明式取数
- `modules.data_manager`：数据访问门面
- `modules.data_source`：外部数据源对接
- `modules.indicator`：技术指标计算
- `modules.series_relation`：序列关系分析
- `modules.strategy`：策略执行
- `modules.tag`：因子持久化

## 设计初衷

- **要解决的问题：** 用户命令和开发命令受众不同、短别名会冲突，所以分成两套入口，但共享底层解析和分发逻辑。
- **明确不做：** 不把 `Cli.user` / `Cli.dev` / `Cli.shared` 内部路径当作公开 import 面——外部只 import `Cli`。

## 相关文档

- [用户指南](./docs/USER_GUIDE.md)
- [快速开始](./QUICKSTART.md)
- [公开 API](./API.md)
- [术语表](./glossary.yaml)
- [架构](./docs/ARCHITECTURE.md)
- [测试用例](./__test__/TEST_CASES.md)
- [决策](./docs/DECISIONS.md)
