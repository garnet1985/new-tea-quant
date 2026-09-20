---
title: install NTQ 安装
aliases:
  - install
  - setup
  - launcher
  - 安装
  - 安装向导
  - 第一次
summary: 用 launcher 走图形化安装向导；完成后从制定策略开始。
---

# 如何安装 NTQ

## 前置条件

- Python **3.9 或以上**
- 在能看到 `launcher.py` 的项目根目录操作

开发者若要改 UI，另外需要 Node.js。日常使用只跑 launcher 即可。默认数据库是 DuckDB，不必先装 MySQL / PostgreSQL。

## 步骤

1. 拿到代码（任选）：

```bash
git clone https://github.com/garnet1985/new-tea-quant.git
cd new-tea-quant
```

或从 GitHub / Gitee 下载 ZIP，解压后进入与 `launcher.py` 同级的目录。

2. 启动安装向导：

```bash
python launcher.py
```

Windows PowerShell 可用 `python .\launcher.py`。若 `python` 指向旧版本，改用 `python3 launcher.py`。

3. 浏览器里按向导走完（多数保持默认即可）：

   1. 安装核心 Python 依赖
   2. 初始化 `userspace`
   3. 配置数据库（默认 DuckDB；可选 MySQL / PostgreSQL）
   4. 是否导入演示数据（可跳过，之后自己接数据源）
   5. 是否安装机器学习依赖（归因分析用，可跳过）
   6. 使用统计（允许或暂不分享都会继续）

4. 进入欢迎页后，点导航 **制定策略**。

## 验证

- 项目下出现 `userspace/`（策略、配置、库文件都在这里）
- 能打开制定策略列表，里面有 demo 策略
- 若导入了演示数据：大约 2023-01～2025-12、约 300 只股票，仅供学习，勿商用

## 日常与升级

| 场景 | 做法 |
| --- | --- |
| 以后打开 UI | 再执行 `python launcher.py` |
| 只补 CLI / Python 依赖 | `python install.py` |
| 升级已安装的应用 | 拉取新代码，**保留** `userspace/`，然后 `python cli.py u` |
| 从头再走向导 | 设置 → 安装与维护 → 重新安装（可能覆盖库连接；导入演示数据可能覆盖表） |
| 补装机器学习依赖 | 设置 → 安装与维护，或向导里那一步 |
| 换更大演示包 | `initialization/data/` 里只留 **1 个** zip，再 `python cli.py id`（全量重导加 `-f`） |

换库见 [切换数据库](switch_database.md)。在界面里调策略见 [从界面制定策略](use_strategy_workbench.md)。填聊天密钥见 [配置 AI Key](configure_ai_key.md)。
