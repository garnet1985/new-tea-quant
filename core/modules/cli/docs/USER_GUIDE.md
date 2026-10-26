# CLI — 用户指南

**版本：** `0.4.5`

`CLI 是命令行入口——cli.py 给普通用户跑扫描/回测/更新，devcli.py 给开发者打包检查。`  
相关：[README.md](../README.md) · [API.md](../API.md) · [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 功能总览

- 用 `cli.py` 跑日常操作：扫策略、跑模拟、打标签、看版本、更新应用
- 用 `devcli.py` 跑开发操作：打包发布、代码检查、清缓存、生成样本
- 用 `cli.py a` 跟 AI 助手对话，让它帮你干活
- 用 `cli.py list` 看股票、策略、因子等清单
- 用 `cli.py export_strategy` / `import_strategy` 导入导出策略

## 配置说明

无用户可配项。

## 常见使用方式

### 场景 1：跑一次策略扫描

1. 打开终端，切到仓库根目录
2. 跑 `python cli.py scan`（或简写 `python cli.py c`）
3. 等扫描跑完，终端会输出结果

### 场景 2：跑一次策略模拟

1. 打开终端，切到仓库根目录
2. 跑 `python cli.py strategy_simulate`（或简写 `python cli.py sim`）
3. 等模拟跑完，按提示查看结果

### 场景 3：打一批因子标签

1. 打开终端，切到仓库根目录
2. 跑 `python cli.py tag`（或简写 `python cli.py t`）
3. 想先试运行不写库，加 `--dry-run`

### 场景 4：查看版本或更新应用

1. 跑 `python cli.py version`（或简写 `python cli.py v`）看当前版本
2. 跑 `python cli.py update`（或简写 `python cli.py u`）触发升级

### 场景 5：开发者打包 / 检查

1. 跑 `python devcli.py pack`（或简写 `python devcli.py p`）做发布打包
2. 跑 `python devcli.py check_import`（或简写 `python devcli.py ic`）检查 import 合规
3. 跑 `python devcli.py check_deps`（或简写 `python devcli.py cd`）检查依赖

## 常见坑与注意事项

- **不要在子目录跑**：`cli.py` / `devcli.py` 都得在仓库根目录执行，否则找不到项目根
- **长短别名别混**：用户命令和开发命令的短别名可能撞车，看错入口会跑到不认识的命令
- **有些命令是长任务**：扫描、模拟、打标签这类命令会跑很久，期间别开第二个实例去抢资源
- **想用 AI 助手**：用 `python cli.py a`（或 `python cli.py agent`），不要在 `devcli.py` 里找
- **看帮助用 `-h`**：跑 `python cli.py -h` 或 `python devcli.py -h` 看完整命令清单

## 相关文档

- [概览 README](../README.md)
- [公开 API](../API.md)
- [架构](./ARCHITECTURE.md)
- [术语表](../glossary.yaml)
- [快速上手](../QUICKSTART.md)
