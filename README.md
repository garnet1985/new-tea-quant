# New Tea Quant（NTQ）- A股量化交易研究框架

<br/>

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/2026-01/logo_0.png" alt="New Tea Quant Logo" width="220" />
</p>

<p align="center">
  <a href="CHANGELOG.md"><img alt="Version" src="https://img.shields.io/badge/version-0.4.2-8A2BE2"></a>&nbsp;
  <a href="#"><img alt="Platform" src="https://img.shields.io/badge/platform-mac%20%7C%20linux%20%7C%20win-4CAF50"></a>&nbsp;
  <a href="#"><img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white"></a>&nbsp;
  <a href="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml"><img alt="Build" src="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml/badge.svg"></a>&nbsp;
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache%202.0-007EC6"></a>
</p>

> For an English introduction, please see **[here](README_en.md)**.

作者：Garnet Xin & 他的AI小伙伴

<a href="https://github.com/garnet1985/new-tea-quant"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-new--tea--quant-181717?logo=github&logoColor=white"></a>&nbsp;
<a href="https://gitee.com/garnet/new-tea-quant"><img alt="Gitee" src="https://img.shields.io/badge/Gitee-new--tea--quant-C71D23?logo=gitee&logoColor=white"></a>&nbsp;
<a href="https://new-tea.cn"><img alt="Website" src="https://img.shields.io/badge/website-new--tea.cn-009688?logo=google-chrome&logoColor=white"></a>

## 当前版本（v0.4.x）

自 **v0.4.0** 起，NTQ 引入 Python 原生文件存储（DuckDB），不再强制依赖第三方数据库服务——有 Python 即可运行。若您仍想使用 MySQL 或 PostgreSQL，向导与设置中均可配置。

最近更新摘要：

**v0.4.2**

- 回测器与标签计算器支持**多股并行、日历切片**式计算。
- UI 新增**高级功能**入口：特征标签、数据契约和数据源（更新尚未完成）。
- 再增加2个演示策略 - 低价股策略（仅演示目的）
- 更多更新请参照 [CHANGELOG.md](CHANGELOG.md)。

## NTQ 是什么？

New Tea Quant是一款对个人开发者友好、轻量级、高性能量化策略回测与研究框架。
它不仅能帮你验证交易策略，还能在接入最新数据源后，作为市场**信号扫描器**，实时捕捉符合策略的交易机会并发出通知。（注：NTQ 专注投研与信号生成，不直接接入实盘交易）。

**如果您在量化研究中遇到过以下痛点，NTQ 将是您的绝佳选择：**

**🚀 个人PC运行效率低下**
- **痛点：**海量数据回测容易导致个人电脑内存溢出或进程卡死，被迫花钱上云。
- **NTQ 方案：**专门对个人 PC 深度优化过。内置动态资源调度引擎，自动根据 CPU 核心数与内存余量分配计算资源，实现运行稳定性与高速回测的相对平衡。

**📦 部署复杂，安装麻烦**
- **痛点：**配置环境折磨人，需要安装数据库、消息队列等一堆繁琐的第三方组件。
- **NTQ 方案：**零第三方外部服务依赖。只要你的电脑装有 Python（≥3.9），克隆代码即可一键运行，把时间留给策略，而不是配环境。

**🧭 研究结论不是按照认知分层，需要复杂的分析**
- **痛点：**一体式回测只给一个净值曲线，不知道问题出在「信号太滥」「买点太差」「仓位太重」还是「根本执行不了」；改一个参数就要整段重跑，越调越懵。
- **NTQ 方案：**把研究拆成可独立验证的阶段——寻找机会的能力 → 捕获价格波动的能力 → 有没有把资金正确投入高价值资产的能力 → 策略执行者能不能适应策略交易方式的能力（即将推出的决策者模式）→ 以及多策略组合层（已规划）。先看清每一层好不好，再决定要不要往下走——避免被一条好看的净值曲线掩盖了底层信号或执行环节的真实问题。

**🔍 交易轨迹难以回溯**
- **痛点：**回测跑通了，但想逐股排查某笔交易的细节却无从下手，宛如黑盒。
- **NTQ 方案：**分层回测的每一步均落盘保留（含版本快照）；配合 Web 策略实验室，可逐股查看买卖轨迹。结构化产物也便于后续分析与机器学习特征工程。

**📊 横截面回测复杂且笨重**
- **痛点：**想做「每月/每年在全 A 里选 Top N、低价股组合」这类横截面策略，本地框架往往要手写大量循环，全市场一跑就占满内存，只能缩小样本或上云。
- **NTQ 方案：**原生支持横截面研究模式（如换仓日同步比较全市场标的）。大样本下框架自动分片加载与并行计算，在个人 PC 上也能完成全市场枚举；仓库内附低价股等横截面演示策略，可直接对照学习。

**🛡️ 实盘收益远低于回测**
- **痛点：**回测收益率极高，实盘却亏损。往往是因为忽略了未来函数、幸存者偏差、涨跌停限制或复杂的交易规则。
- **NTQ 方案：**内置贴近真实市场的回测引擎。框架在底层默认处理了几类最容易让回测失真的问题：
  - **幸存者偏差：**使用了PIT（point-in-time）股票池来防止
  - **交易规则限制：**自动遵守买入手数规则、涨跌停无法成交、停牌、T+1 等等
  - **未来函数：**数据严格按照日期切割，防止"上帝视角"式的回测
  
让您只需专注挖掘 Alpha，剩下的交给框架。

**♻️ 每个策略需要重复计算因子**
- **痛点：**多个策略复用同一个指标（如复杂动量因子）时，重复计算导致效率低下，且容易写错。
- **NTQ 方案：**提供强大的“特征标签”功能。支持特征预处理与全局缓存，一次计算，多策略复用。不仅提升了回测速度，更保证了因子逻辑的一致性与安全性。


### 您还能得到这些“工程化的小心思”

- **核心与用户数据的分离**：框架的核心功能`core` 与用户产生的数据 `userspace` 分离，升级框架时策略与配置可保留。
- **大量的配置驱动**：使用settings配置方式完成常做的事情；复杂逻辑再写 Python。
- **方便的使用接口**：自带UI和命令行cli，可以通过UI或者快捷命令完成大部分操作，且遵从「同一策略同一产物」。
- **可复现的研究记录**：版本快照与指纹、`results/` 结构化输出，便于对比「这次和上次差在哪」。

## 支持一下项目

若 NTQ 对您有用、您愿意持续关注它的演进，欢迎在 [GitHub](https://github.com/garnet1985/new-tea-quant) 或 [Gitee](https://gitee.com/garnet/new-tea-quant) 上为仓库点亮一颗 **Star**——这对个人开源项目而言，是非常实在的支持。

这是我第一次认真做开源，您的认可与反馈，是我继续打磨框架的最大动力。谢谢您！

### 请注意

NTQ 本身免费开源，但部分能力依赖您自备资源：

- **数据**：框架提供接入与存储能力，**不含**数据源的付费账号或 token；需在第三方平台注册/购买后自行配置。
- **通知与外部自动化**：短信、邮件、推送等**不在框架内**；扫描结果可通过 Adapter 等扩展点交给您自己的程序处理。

### 另外

需要**轻微的 Python/配置能力**（或使用 AI 辅助）。运行环境为 **Python 3.9+**；默认使用内置 **DuckDB** 文件库，也可在向导中改用 **MySQL / PostgreSQL**。更完整的教程与概念说明见官网 **[new-tea.cn](https://new-tea.cn)**（中文）。

本项目采用 **Apache 2.0** 许可，可自由学习、改造与扩展。


## 快速安装（5分钟跑起来）

目标：**5 分钟内跑起框架 + 跑通一个演示策略**。

### 前提条件

- 本机需要有 **Python 3.9 或以上**版本。如果您不知道怎么安装，请参考这篇文档：[安装 Python](https://new-tea.cn/zh-hans/install-python)。

### 第 1 步：获取代码

任选其一：

- **Git clone**（推荐）：

```bash
git clone https://github.com/garnet1985/new-tea-quant.git
cd new-tea-quant
```

- **下载 ZIP**：在 GitHub 仓库页选择 **Code → Download ZIP**，解压后进入 **`new-tea-quant`** 根目录（与 `launcher.py` 同级）。

### 第 2 步：在仓库根目录启动安装向导

在**项目根目录**（能看到 `launcher.py`）打开终端，执行其一：

```bash
python launcher.py
```

若系统上 `python` 指向旧版本，可改用：

```bash
python3 launcher.py
```

脚本会：切到仓库根目录、确保虚拟环境、然后**启动 BFF + 前端并打开浏览器**，进入图形化 **Setup 安装向导**（由 BFF setup API 驱动步骤）。

日常开发 UI 可用 **`python devcli.py ui`**（浏览器 `:8000`，共享 BFF `:8888`）；上式 `launcher.py` 为**生产入口**（`:8888` 托管 `fed/build`）。结束 UI 进程：`python devcli.py uk`。

### 第 3 步：在浏览器中按向导完成初始化

按页面提示依次完成即可（数据库连接、用户空间路径、数据导入等以当前向导为准）。以下为界面示意（共 5 张；若与您的版本略有差异，以实际页面为准）：

**图 1**

![Setup 向导示意 1](setup/images/step1.png)

系统会自动安装需要的依赖包，这一步只需要点击“开始安装”并等待

**图 2**

![Setup 向导示意 2](setup/images/step2.png)

本步配置 **userspace（用户空间）** 根目录，您可以：

- 使用向导给出的**默认路径**（直接点 **「下一步」**）。
- 或勾选 **「我想自定义 userspace 路径」**，在输入框中填写本机上的其他目录（请确保磁盘空间充足；若目标目录已有内容，向导会按策略提示是否覆盖）。

**图 3**

![Setup 向导示意 3](setup/images/step3.png)

本步连接 **数据库** app默认使用python原生支持的duckdb，如果您需要使用其他db如mysql或pgsql，请先设置好数据库连接参数，然后按照提示填入连接信息。

连接校验通过后点 **「下一步」** 继续。之后仍可在 **「设置」** 中调整数据库配置。

**图 4**

![Setup 向导示意 4](setup/images/steps.png)

数据库就绪后会进入 **数据导入** 等后续步骤，页面会显示步骤进度；本阶段可能持续较久，请保持页面打开并耐心等待。

**图 5**

![Setup 向导示意 5](setup/images/step4.png)

全部步骤完成后，可点击 **「前往策略实验室」** 进入主界面。

### 跑通第一个策略（Web 或命令行）

**推荐（Web）**：在项目根目录启动 UI：

```bash
python launcher.py          # 生产：:8888
# 或开发：
python devcli.py ui         # 开发：:8000（CRA），BFF API 共用 :8888
```

浏览器打开**策略实验室**，选择 **`userspace/strategies/demo/`** 下任一演示策略（或向导完成后自带的示例策略），按界面执行枚举 / 价格层 / 资金层回测并查看报告。

**命令行（价格层示例）**：

```bash
python cli.py sp --strategy demo/regression/rsi/rsi_v1_without_value_anchor
```

终端出现回测摘要即表示 CLI 链路可用。完整分层流程还可使用 `se`（枚举）、`so`（组合层）；见下文「命令行」表。

> **说明**：根目录 **`python install.py`** 用于 **CLI 应用首次安装**（依赖、userspace、库表、内置小数据等），安装向导完成后通常不必再跑。若从官网下载**更大的演示数据 ZIP**，请放入 `setup/init_data/`（该目录内**只能有 1 个 zip**），再执行：
>
> ```bash
> python setup/steps/import_data/install.py
> ```
>
> 需要全量重导时可加 `--force`。日常仅用向导导入的内置小数据时，完成向导 + 上节任一路径即可。

### 更多常用命令

查看帮助：

```bash
python cli.py -h
```

机会枚举（分层回测第一步）：

```bash
python cli.py strategy_enumerate --strategy demo/regression/rsi/rsi_v1_without_value_anchor
# 或短命令
python cli.py se --strategy demo/regression/rsi/rsi_v1_without_value_anchor
```

带资金的策略模拟：

```bash
python cli.py strategy_portfolio --strategy demo/regression/rsi/rsi_v1_without_value_anchor
# 或短命令
python cli.py so --strategy demo/regression/rsi/rsi_v1_without_value_anchor
```

全市场扫描：

```bash
python cli.py scan --strategy demo/regression/rsi/rsi_v1_without_value_anchor
# 或短命令
python cli.py c --strategy demo/regression/rsi/rsi_v1_without_value_anchor
```

生成特征标签：

```bash
python cli.py tag --scenario your_scenario
# 或短命令
python cli.py t
```

您也可以修改 `userspace/strategies/` 下的 settings 或 worker，自定义策略算法与目标。

Have fun `^_^`, 更多用法请参考这里 [更多用例](https://new-tea.cn/zh-hans/more-examples)

### 数据说明（请先看）

1. **仓库内置小数据**：只覆盖部分表，用于快速启动和演示。  
2. **获取更多（约 3 年）演示数据包**：（注意，这一步暂时不可用，正在修正中）用于更完整的策略验证/回测，请在 **[new-tea.cn](https://new-tea.cn)** 注册后下载，**清空** `setup/init_data/` 后只放入 **1 个** zip，再执行 `python setup/steps/import_data/install.py`（必要时加 `--force`）。  
3. **自有数据源**：也可自行接入（如 Tushare），详见 [userspace/extensions/data_source/README.md](userspace/extensions/data_source/README.md)。

### 欢迎一起交流早期使用体验

NTQ 目前在 **v0.x** 阶段，安装向导、文档和 Web UI 都还在改。不同系统、数据库和研究习惯差别很大，我一个人很难把所有情况都想到——如果您也愿意在本机按上文试试看，很欢迎一起聊聊：**哪里不顺手、哪句说明不好懂、哪段流程可以更省事**。

**互相交流、一起摸索**：您在实际研究里卡住的点，往往也是我需要补上的理解；您怎么用策略、怎么看回测结果，也常常能提醒我框架还缺什么。期待与您的交流。

**如何找到我？**您可以直接在gitee或者github私信我，或者到官网 **[联系我](https://new-tea.cn/zh-hans/contact)** 留言（无需注册也可填表单）。很期待听到您声音。

## 请注意
当前版本仍然是非正式版本 **v0.x** 框架现阶段不能保证任何API的稳定性，当版本进入1.0之后，API将基本稳定。详见 [CHANGELOG.md](CHANGELOG.md)。

## 文档维护约定

- **根目录 `README.md` 是仓库文档主入口**，用于对外说明项目用法与当前推荐流程。
- **命令入口统一为 `cli.py`**；如其他文档出现 `start-cli.py` 或 `start.py`，以本页与 `python cli.py -h` 为准。
- **`docs/development/` 为内部工作区文档**，当前阶段不纳入对外文档整理范围。
- 每次版本发布至少同步更新：
  - `README.md`
  - `CHANGELOG.md`

## 开源仓库里包含什么？

| 内容 | 说明 |
|------|------|
| **框架代码** | `core/`、用户命令行（`cli.py`）与 UI 启动（`launcher.py` / `devcli.py ui`） |
| **Web UI** | `core/ui/bff` + `core/ui/fed`（发布构建产物已纳入仓库，日常无需 Node） |
| **演示策略** | `userspace/strategies/demo/` 下多组演示策略；另有 `_template/` 空模版可复制 |
| **演示行情等数据** | 包含一份可快速启动的小数据；更完整数据可从官网下载 |
| **辅助工具** | `devtools/`：Docker 说明、维护用自动化脚本等（非业务核心，索引见 [docs/README.md](docs/README.md) 中「仓库辅助工具」一节） |

## 如何联系到我？

- **留言**：[new-tea.cn/zh-hans/contact](https://new-tea.cn/zh-hans/contact)（无需注册也可填表单）
- **Issue**：[GitHub Issues](https://github.com/garnet1985/new-tea-quant/issues) · [Gitee Issues](https://gitee.com/garnet/new-tea-quant/issues)
- 反馈预期与贡献方式见 [SUPPORT.md](SUPPORT.md)

## 分支策略是什么？

- **master**：最新版本，拒绝任何直接的 PR 或者提交

- **dev**：可从中建立分析，dev 会和 master 同步，到合适时机后会 merge 入 master 并且在 master 上建立 rc 分支用于 release，之后 release 代码会回到 dev

- **bugfix**：请使用 `bugfix/your-change` 的方式命名，否则无法 merge

- **feature**：请使用 `feature/your-change` 的方式命名，否则无法 merge

- **hotfix**：请使用 `hotfix/your-change` 的方式命名，否则无法 merge，分支只能从 rc 分支拉取

**Docker**：可用仓库内 `Dockerfile` 与 `docker-compose.yml` 拉起 PostgreSQL 与运行环境，步骤见 [devtools/docker/README.md](devtools/docker/README.md)。

## 有了新版本如何升级？

1. 拉取或下载最新 **master**，**保留**本机 `userspace/`（及其中策略、备份与配置），其余按新版本覆盖。
2. 在项目根目录执行 `python install.py`（或 `python cli.py` 触发自动安装），以刷新依赖与安装状态；若发布说明要求重导数据，再按「数据说明」运行 `setup/steps/import_data/install.py`。
3. 使用 Web UI 时，用 `python launcher.py` 启动即可（一般无需本地 `npm run build`，除非您自行改前端或文档另有说明）。开发前端改动时用 `python devcli.py ui`。

---

## 命令行（`cli.py`）

入口脚本：**`cli.py`**（无参时默认显示 **`version`**，等同 `-v` / `--version` / `v`）。

规则：`xx`=命令，`-f` / `-n`=全局开关，`--xx`=对象参数。

```bash
python cli.py -h
```

| 用途 | 命令示例 |
|------|----------|
| 查看帮助 | `python cli.py -h` |
| 查看版本（默认） | `python cli.py` 或 `-v` / `--version` / `v` |
| 更新数据 | `renew [SOURCE]` 或 `r [SOURCE]` |
| 扫描机会 | `scan` 或 `c [--strategy NAME] [--demo]` |
| 枚举机会 | `strategy_enumerate` 或 `se [--strategy NAME]` |
| 价格因子模拟 | `strategy_price_factor` 或 `sp [--strategy NAME]` |
| 组合模拟 | `strategy_portfolio` 或 `so` |
| 资金分配（将用 `so` 替代） | `strategy_capital_allocate` 或 `sa` |
| 完整模拟链路 | `strategy_simulate` 或 `s` |
| 分析结果摘要 | `strategy_analyse` 或 `sy [--session ID]` |
| 标签计算 | `tag` 或 `t [--scenario NAME]` |
| 导出策略包 | `export_strategy` 或 `ex [NAME] [-o PATH]` |
| 导入策略包 | `import_strategy` 或 `im [PATH]` |
| 从模版新建策略 | `python cli.py -n userspace/strategies/my_strategy` |
| 从模版新建 Tag | `python cli.py t -n userspace/extensions/tags/my_scenario` |
| 检查 core 更新 | `update` 或 `u` |

**`--strategy`**：未指定时，若只有一个 `is_enabled=True` 的策略会自动选用；多个启用时默认取名称排序第一个并 **告警**，建议显式写 `--strategy`。

**`-f`**：强制刷新 / 重算 / 覆盖（适用于 `se`、`sp` 等支持刷新的命令）。

**说明**：文档与站点中若仍出现 `start-cli.py` 或 `start.py`，请以本仓库 **`cli.py`** 为准。

---

## 开发命令（`devcli.py`）

面向本机开发与排障（仓库根目录）。规则与 `cli.py` 相同：`xx`=命令、`-v`=版本、`--xx`=对象参数。

```bash
python devcli.py -h          # 完整缩写表
python devcli.py               # 显示版本（默认）
python devcli.py ui              # 启动开发 UI（launcher -d，:8000 + BFF :8888）
python devcli.py uk              # 结束 UI 端口（8000 + 8888）
python devcli.py csc             # 清空策略模拟磁盘 + DB 工作台缓存
python devcli.py cdc             # 仅清空 DB 工作台快照
python devcli.py cmc             # 仅删除各策略 results/
python devcli.py cgc             # 清空 userspace/.ntq（全局缓存）
python devcli.py dbc             # DuckDB WAL 合并（`--recover` 修复损坏 WAL）
python devcli.py p -core_v0.4.2  # 发布前检查流水线
python devcli.py ssp 500         # 分层样本股票池（dev 轻量 renew）
python devcli.py pc              # 取消样本池
```

Web **设置 → 缓存管理** 也可清理 DB 快照、`results/`、`userspace/.ntq` 等（与部分 `devcli` 清理命令等价）。

工作台快照 HTTP 清理接口见策略模块文档 [db-cache-service.md](core/modules/strategy/docs/db-cache-service.md) §8（V2-11 / V2-12）。

---

## 如何运行测试？

可以通过运行下列代码来实现，如果您要提交一个PR，请务必保证UT能跑过。

```bash
python -m pytest
```

## 依赖管理（Python）

项目使用 `pip-tools` 维护可复现锁定依赖：

- 顶层声明：`requirements.in`、`requirements-dev.in`
- 锁定结果：`requirements.txt`、`requirements-dev.txt`

更新锁文件（在仓库根目录）：

```bash
python3 -m piptools compile --output-file requirements.txt requirements.in
python3 -m piptools compile --output-file requirements-dev.txt requirements-dev.in
```

## 支持、反馈与捐赠

- **文档与会员资源（Demo 数据、扩展策略等）**：[new-tea.cn](https://new-tea.cn)  
- **问题反馈、Issue / PR 预期**：[SUPPORT.md](SUPPORT.md)  
- **参与贡献**：[CONTRIBUTING.md](CONTRIBUTING.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)  
- **安全披露**：[SECURITY.md](SECURITY.md)  

若您希望 **捐赠或商业合作**，请以 **官网** 当前公示的联系方式或页面为准。

---

## 许可证与免责

本项目采用 **Apache License 2.0**，见 [LICENSE](LICENSE)。

**免责声明**：仅供学习与研究，不构成任何投资建议；回测结果不代表未来表现。

---

<details>
<summary>仓库内文档与归档</summary>

- 离线文档索引：[docs/README.md](docs/README.md)  
- **辅助工具 `devtools/`**：[文档索引](docs/README.md) · [Docker 说明](devtools/docker/README.md)  

</details>
