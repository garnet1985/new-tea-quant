# New Tea Quant（NTQ）- A股量化交易研究框架

<br/>

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/2026-01/logo_0.png" alt="New Tea Quant Logo" width="220" />
</p>

<p align="center">
  <a href="CHANGELOG.md"><img alt="Version" src="https://img.shields.io/badge/version-0.4.4-8A2BE2"></a>&nbsp;
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

**v0.4.4**

- 策略投资组合使用**复权价格**（连续价格）作为信号，**实际价格作**为成交价格的双轨回测，增加了投资组合的准确性。
- 在投资组合回测过程中新增加了当出现多个机会，选择哪个机会进行投资的接口，让投资可干预性更强。
- UI 新增**高级功能**入口：特征标签、数据契约和数据源。
- 所有模块进行了标准化重构，统一API文档，使用说明，架构说明等等。
- 更多更新请参照 [CHANGELOG.md](CHANGELOG.md)。

## NTQ 是什么？

New Tea Quant是一款对个人开发者友好、轻量级、高性能量化策略回测与研究框架。
它不仅能帮你验证交易策略，还能在接入最新数据源后，作为市场**信号扫描器**，实时捕捉符合策略的交易机会并发出通知。（注：NTQ 专注投研与信号生成，不直接接入实盘交易）。

**如果您在量化研究中遇到过以下痛点，NTQ 将是您的绝佳选择：**

**🚀 个人PC运行效率低下**
- **痛点**：海量数据回测容易导致个人电脑内存溢出或进程卡死，被迫花钱上云。
- **NTQ 方案**：专门对个人 PC 深度优化过。内置动态资源调度引擎，自动根据 CPU 核心数与内存余量分配计算资源，实现运行稳定性与高速回测的相对平衡。

**📦 部署复杂，安装麻烦**
- **痛点**：配置环境折磨人，需要安装数据库、消息队列等一堆繁琐的第三方组件。
- **NTQ 方案**：零第三方外部服务依赖。只要你的电脑装有 Python（≥3.9），克隆代码即可一键运行，把时间留给策略，而不是配环境。

**🧭 研究结论不是按照认知分层，需要复杂的分析**
- **痛点**：一体式回测只给一个净值曲线，不知道问题出在「信号太滥」「买点太差」「仓位太重」还是「根本执行不了」；改一个参数就要整段重跑，越调越懵。
- **NTQ 方案**：把研究拆成可独立验证的阶段——寻找机会的能力 → 捕获价格波动的能力 → 有没有把资金正确投入高价值资产的能力 → 策略执行者能不能适应策略交易方式的能力（即将推出的决策者模式）→ 以及多策略组合层（已规划）。先看清每一层好不好，再决定要不要往下走——避免被一条好看的净值曲线掩盖了底层信号或执行环节的真实问题。

**🔍 交易轨迹难以回溯**
- **痛点**：回测跑通了，但想逐股排查某笔交易的细节却无从下手，宛如黑盒。
- **NTQ 方案**：分层回测的每一步均落盘保留（含版本快照）；配合 Web 策略实验室，可逐股查看买卖轨迹。结构化产物也便于后续分析与机器学习特征工程。

**📊 横截面回测复杂且笨重**
- **痛点**：想做「每月/每年在全 A 里选 Top N、低价股组合」这类横截面策略，本地框架往往要手写大量循环，全市场一跑就占满内存，只能缩小样本或上云。
- **NTQ 方案**：原生支持横截面研究模式（如换仓日同步比较全市场标的）。大样本下框架自动分片加载与并行计算，在个人 PC 上也能完成全市场枚举；仓库内附低价股等横截面演示策略，可直接对照学习。

**🛡️ 实盘收益远低于回测**
- **痛点**：回测收益率极高，实盘却亏损。往往是因为忽略了未来函数、幸存者偏差、涨跌停限制或复杂的交易规则。
- **NTQ 方案**：内置贴近真实市场的回测引擎。框架在底层默认处理了几类最容易让回测失真的问题：
  - **幸存者偏差**：使用了PIT（point-in-time）股票池来防止
  - **交易规则限制**：自动遵守买入手数规则、涨跌停无法成交、T+1 等等
  - **未来函数**：数据严格按照日期切割，防止"上帝视角"式的回测
让您只需专注挖掘 Alpha，剩下的交给框架。

**♻️ 每个策略需要重复计算因子**
- **痛点**：多个策略复用同一个指标（如复杂动量因子）时，重复计算导致效率低下，且容易写错。
- **NTQ 方案**：提供强大的“特征标签”功能。支持特征预处理与全局缓存，一次计算，多策略复用。不仅提升了回测速度，更保证了因子逻辑的一致性与安全性。


### 您还能得到这些“工程化的小心思”

- **核心与用户数据的分离**：框架的核心功能`core` 与用户产生的数据 `userspace` 分离，升级框架时策略与配置可保留。
- **大量的配置驱动**：使用settings配置方式完成常做的事情；复杂逻辑再写 Python。
- **方便的使用接口**：自带UI和命令行cli，可以通过UI或者快捷命令完成大部分操作，且遵从「同一策略同一产物」。
- **可复现的研究记录**：版本快照与指纹、`results/` 结构化输出，便于对比「这次和上次差在哪」。

## NTQ真挚地邀请早期体验志愿者（v0.x）

NTQ 仍在快速迭代：**安装向导、文档和 Web UI 都会变**。我一个人很难覆盖所有操作系统、Python 环境和研究习惯——**非常需要一批愿意在本机试用的朋友，一起把框架磨到更好用**。

您**不必会写代码**。按上文完成安装、跑通一个 demo，然后把真实感受告诉我就很有价值。

### 我们特别希望您反馈什么

- **安装与上手**：哪一步卡住、哪句 README 看不懂、期望更省事的流程
- **策略实验室 / 制定策略**：界面是否顺手、三步回测是否符合您的研究习惯
- **回测结果**：报告是否看得懂、单股溯源是否够用、哪里和预期不一致
- **性能与稳定**：个人 PC 上是否 OOM、卡顿、异常报错（请尽量附系统与复现步骤）
- **文档与示例**：缺哪类 demo 策略、官网/仓库哪块需要补

### 如何参与（任选其一）

| 方式 | 适合 |
|------|------|
| [GitHub Issues](https://github.com/garnet1985/new-tea-quant/issues) | Bug、功能建议（推荐，便于跟踪） |
| [Gitee Issues](https://gitee.com/garnet/new-tea-quant/issues) | 国内用户同样欢迎 |
| [官网留言](https://new-tea.cn/zh-hans/contact) | 无需注册也可填表单 |
| GitHub / Gitee 私信 | 简短交流、不方便公开的细节 |

提 Issue 时如能附上：**系统（Win / macOS / Linux）、Python 版本、做到第几步、截图或报错摘要**，会大大加快排查。

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


## 快速安装 + 运行一个策略

目标：**5 分钟内跑起框架 + 跑通一个演示策略**。

### 前提条件

- 本机需要有 **Python 3.9 或以上**版本。如果您不知道怎么安装，请参考这篇文档：[安装 Python](https://new-tea.cn/zh-hans/install-python)。
- **注意：如果您是开发者**：您需要安装Nodejs（主要是UI需要）；数据库建议使用mysql或者pgsql。（DuckDB的单写模式调试很麻烦）

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
windows power shell可能是：

```bash
python .\\launcher.py
```

若系统上 `python` 指向旧版本，可改用：

```bash
python3 launcher.py
```

脚本会：切到仓库根目录、确保虚拟环境、然后**启动 BFF + 前端并打开浏览器**，进入图形化 **Setup 安装向导**（由 BFF setup API 驱动步骤）。

### 第 3 步：在浏览器中按向导完成初始化

按页面提示依次完成即可，基本上都是按照默认方式安装。

演示数据的导入会在安装时自动完成（如果您已经有数据，会自动跳过数据安装）

安装成功后点「前往制定策略」进入策略页面。

至此，您就已经完成了NTQ的安装。

**如果您是开发者**，建议使用mysql或pgsql，数据库可以不用新建，程序会自动帮助您新建（如果和已有数据库重名会提示）。

### 第 4 步：运行一个demo

NTQ会自带下边资产用来演示：
- **数据：**自带2025年到2026年一年的500个股票的数据作为演示数据，请勿商用。
- **策略**自带默认的demo策略，请注意策略只是方便演示的作用，请不要用于实盘。 

从UI点击“制定策略”或更改url路径`/strategy-design/`进入策略目录，从列表里选择一个策略，点击策略名或者“进入调试”策略进入详细页面。

策略页面由4个大块组成：
- **策略信息**：在策略页面的上方占满全屏，记录了当前策略的信息和缓存版本
- **策略配置**：在页面的左半边，每一步都有每一步的配置，您可以在这里修改参数，这样就可以看到回测器得到不同的结果。每次参数的变化会导致新的回测版本，您可以切换不同版本回溯以前的配置。
- **执行面板**：当前回测的开始和刷新按钮执行处，还有通到其他回测步骤的快捷按钮，当然，您也可以点击右上角的步骤来快捷切换。
- **策略报告**：当前回测步骤下的回测报告，在您回测完成后会出现当前步骤的报告，您可以和之前不同版本间进行比较，有些步骤可以点击表格中的单股进行K线上的单股回溯。

第一个默认页面是枚举页面，您可以在“执行面板”点击“开始模拟”来进行机会枚举并产生报告。其他步骤页面也是类似步骤。**注意：**有些步骤是需要依赖枚举步骤的，单独运行他们会首先触发枚举的重新运行。

接下来，have fun ^_^

### 数据说明
 
1. **（注意，这一步暂时不可用，正在修复中）** 如果您想**获取更多（约 3 年，全 A 股市场）演示数据包**：用于更完整的策略验证/回测，请在 **[new-tea.cn](https://new-tea.cn)** 注册后下载，**清空** `setup/init_data/` 后只放入 **1 个** zip，再执行 `python setup/core/steps/import_data/install.py`（如果是清空再安装，需要在命令最后加入 `--force` 参数）。  
2. **自有数据源**：也可自行接入（例如 Tushare），详见 [userspace/extensions/data_source/README.md](userspace/extensions/data_source/README.md)。
3. 演示数据与 demo 策略仅供学习研究，请勿用于实盘或商用。


### 一些声明

当前版本仍然是非正式版本 **v0.x** 框架现阶段不能保证任何API的稳定性，当版本进入1.0之后，API将基本稳定。详见 [CHANGELOG.md](CHANGELOG.md)。

## 常用命令（`cli.py`）

分层回测与扫描（完整列表：`python cli.py -h`）：

```bash
python cli.py se --strategy demo/regression/rsi/rsi_v1_without_value_anchor   # 机会枚举
python cli.py sp --strategy demo/regression/rsi/rsi_v1_without_value_anchor   # 价格层
python cli.py so --strategy demo/regression/rsi/rsi_v1_without_value_anchor   # 资金层
python cli.py c  --strategy demo/regression/rsi/rsi_v1_without_value_anchor   # 全市场扫描
python cli.py t  --scenario demo/market_cap_tier                              # 特征标签
```

建议显式指定 `--strategy`；需要强制重算时加 `-f`。

---

## Fun time：AI 如何评价 NTQ？

> 以下为第三方 AI 在阅读NTQ一些核心文件和文档后的评价，只供娱乐**完整回复截图**。**非商业广告**，不代表任何 AI 官方立场；AI 可能过度乐观，请结合本仓库自行判断。  
> 也欢迎您使用自己的AI来评价这个工程，请注意要让AI读了核心代码文件以后再评价，否则AI可能会出现严重脱离实际的幻觉

<details>
<summary><strong>Gemini 3.1 Pro</strong>（展开长图）</summary>

![Gemini 3.1 Pro 对 NTQ 的审阅](docs/images/ai-assessments/gemini-3.1-pro.jpg)

</details>

<details>
<summary><strong>GPT-5.5</strong>（展开长图）</summary>

![GPT-5.5 对 NTQ 的审阅](docs/images/ai-assessments/gpt-5.5.jpg)

</details>

<details>
<summary><strong>Claude Sonnet 4.6</strong>（展开长图）</summary>

![Claude Sonnet 4.6 对 NTQ 的审阅](docs/images/ai-assessments/claude-sonnet-4.6.jpg)

</details>

<details>
<summary><strong>DeepSeek</strong>（展开长图，6 屏拼接）</summary>

![DeepSeek 对 NTQ 的审阅](docs/images/ai-assessments/deepseek.jpg)

</details>

<details>
<summary><strong>Gitee 马建仓助手</strong>（展开长图）</summary>

![Gitee 助手对 NTQ 的审阅](docs/images/ai-assessments/gitee-assistant.jpg)

</details>

---

## 几个典型用法（举例）

| 你想做的事 | 建议路径 |
|------------|----------|
| **验证「这个信号有没有」** | Web **制定策略** → 选 demo → **枚举机会** → 看触发次数与分布 |
| **验证「触发后单笔能不能赚」** | 枚举完成后 → **价格回测** → 报告里点单股看买卖点位 |
| **验证「有限资金下还能不能活」** | 价格层 OK 后 → **资金模拟** → 看组合曲线与持仓 |
| **每月在全 A 选低价 / Top N** | 参考 `demo/cross_sectional/low_price/`，用 **calendar_slice** 横截面模式 |
| **多个策略共用同一因子** | 先跑 **Tag**（`cli.py t`），策略 settings 里引用 Tag 数据 |
| **最新行情筛机会** | 数据更新后 **`cli.py c`** 或 Web 扫描（通知需 Adapter 自接） |

---

## 升级

1. 拉取最新 **master**，**保留** `userspace/`，其余覆盖。  
2. 根目录执行 `python install.py` 刷新依赖；发布说明若要求重导数据，见上文「数据说明」。  
3. 日常启动：`python launcher.py`。

---

## 许可与支持

- **许可证**：[Apache 2.0](LICENSE) · **变更**：[CHANGELOG.md](CHANGELOG.md)
- **反馈 / 贡献**：[SUPPORT.md](SUPPORT.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md)
- **官网**：[new-tea.cn](https://new-tea.cn)

**免责声明**：仅供学习与研究，不构成投资建议；回测结果不代表未来表现。

<details>
<summary>开发者附录（分支、devcli、测试、文档索引）</summary>

**仓库要点：** `core/` 框架 · `userspace/` 策略与配置（升级保留）· `userspace/strategies/demo/` 演示策略 · [docs/README.md](docs/README.md)

**分支：** `master` 发布；从 `dev` 拉 `feature/*` / `bugfix/*`；`hotfix/*` 仅从 rc 拉。勿直接向 `master` 提 PR。

**开发：** `python devcli.py -h`（`ui` 开发 UI · `uk` 释放端口 · `csc` 清缓存）· Docker：[devtools/docker/README.md](devtools/docker/README.md)

**测试 / 依赖：**

```bash
./venv/bin/python -m pytest   # 需先 pip install -r requirements-dev.txt（含 Flask 等）
python3 -m piptools compile --output-file requirements.txt requirements.in
```

</details>
