# New Tea Quant（NTQ）- A股量化交易研究框架

<br/>

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/2026-01/logo_0.png" alt="New Tea Quant Logo" width="220" />
</p>

<p align="center">
  <a href="CHANGELOG.md"><img alt="Version" src="https://img.shields.io/badge/version-0.3.3-8A2BE2"></a>&nbsp;
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

## 当前版本（v0.3.x）

自 **v0.3.0** 起，NTQ 提供本机 **Web UI**（`launcher.py` 启动 BFF + 前端）：策略实验室（分层回测与报告）、策略扫描、图形化安装向导、应用设置等。日常**使用**无需自行安装 Node.js（前端以构建产物由 BFF 托管；仅 `-d` 开发模式或改前端源码时需要 Node）。

**v0.3.2** 起支持按板块配置最小买入单位、涨跌停与交易规则（**market profile**），回测报告展示统一回测区间等。完整变更见 [CHANGELOG.md](CHANGELOG.md)。

## NTQ 是什么？

您是不是心里有一些对股票操作策略的想法需要验证？比如周线 RSI 低于 20 是否值得买、MACD 金叉有没有统计优势、追热点到底胜率如何——想把它整理成**自己的策略**，用历史数据看证据，再拿去扫描最新行情找机会？

**NTQ**（New Tea Quant）就是为这类**个人量化研究**准备的：一套可在本机完整跑通的 A 股研究框架，帮您把「有个想法」推进到「有依据的结论」，而不是只做一次性黑盒回测。

### 核心价值：分层回测，把问题拆开看清

NTQ 把研究拆成三步，每一步回答不同的问题：

1. **机会枚举** — 您的逻辑在样本里**何时、在哪些股票上**会触发？
2. **价格层验证** — 触发之后，**单笔买卖**在手续费、滑点等设定下表现如何？
3. **资金层回测** — 在**有限资金、仓位与交易规则**下，组合层面还成不成？

逻辑、单笔表现和资金约束分开检验，更容易定位「信号不行」还是「仓位/规则把收益吃掉了」。枚举结果会沉淀为标准产物，可复用、可对比，也便于后续分析。

### 您还能得到什么

- **本地一体化**：数据接入与存储、指标/标签计算、回测、全市场扫描在同一套工程里完成；`core` 与 `userspace` 分离，升级框架时您的策略与配置可保留。
- **配置驱动**：多数实验通过改配置完成，复杂逻辑再写 Python；配合**策略实验室 Web UI**（回测、报告、版本对比）和命令行，同一策略可反复对照。
- **可复现**：版本快照、指纹与结构化产物目录，中间结果可追溯，便于回答「这次和上次差在哪」。
- **性能**：核心计算支持多进程/多线程，在普通台式机上也能承担较大样本的回测与扫描。

研究跑通后，可用**策略扫描**对库内最新行情做全市场筛选；机会默认在终端或 Web 界面展示，后续通知或下单需您自行对接第三方。

### 请注意

NTQ 本身免费开源，但部分能力依赖您自备资源：

- **数据**：框架提供接入与存储能力，**不含**数据源的付费账号或 token；需在第三方平台注册/购买后自行配置。
- **通知与交易**：短信、邮件、推送、下单等**不在框架内**；扫描结果可通过 Adapter 等扩展点交给您自己的程序处理。

### 另外

需要**轻微的 Python/配置能力**（或使用 AI 辅助）。运行环境为 **Python 3.9+** 与 **PostgreSQL 或 MySQL**（均可免费安装）。更完整的教程与概念说明见官网 **[new-tea.cn](https://new-tea.cn)**（中文）。

本项目采用 **Apache 2.0** 许可，可自由学习、改造与扩展。


## 快速安装（5分钟跑起来）

目标：**5 分钟内跑起框架 + 跑通 `example` 策略**。

### 前提条件

- 本机需要有 **Python 3.9 或以上**版本。如果您不知道怎么安装，请参考这篇文档：[安装 Python](https://new-tea.cn/zh-hans/install-python)。
- 本机需要有 **MySQL 或 PostgreSQL** 中的任意一种数据库。如果您不知道如何安装，请参考这篇文档：[安装数据库](https://new-tea.cn/zh-hans/install-database)。
- **Node.js**（**仅**在 `python launcher.py -d` 开发模式，或需要修改 `core/ui/fed` 前端源码时安装）。纯使用 / 跑回测 / 命令行**不需要** Node。详见 [Node.js 官网](https://nodejs.org/)。

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

本步连接 **MySQL** 或 **PostgreSQL**。请事先安装并启动数据库服务，然后按页面填写：

- **数据库类型**（mysql / postgresql）。
- **主机、端口**（默认一般为本机；若使用云库或远程实例请按实际填写）。
- **用户名、密码**（需具备连接及**建库**权限；库不存在时，向导会尝试自动创建目标库）。
- **数据库名**：建议使用**新建或专用的空库**；若指向已有库，初始化会写入/变更表结构，**请勿使用存放重要业务数据的库名**。

连接校验通过后点 **「下一步」** 继续。之后仍可在 **「设置」** 中调整数据库配置。

**图 4**

![Setup 向导示意 4](setup/images/steps.png)

数据库就绪后会进入 **数据导入** 等后续步骤，页面会显示步骤进度；本阶段可能持续较久，请保持页面打开并耐心等待。

**图 5**

![Setup 向导示意 5](setup/images/step4.png)

全部步骤完成后，可点击 **「前往策略实验室」** 进入主界面。

### 跑通第一个策略（Web 或命令行）

**推荐（Web）**：在项目根目录启动 UI（若安装向导已拉起过，也可直接复用该终端）：

```bash
python launcher.py
```

浏览器打开策略实验室，选择 **`example`** 策略，按界面执行枚举 / 价格层 / 资金层回测并查看报告。

**命令行（价格层示例）**：

```bash
python start-cli.py -sp --strategy example
```

终端出现回测摘要即表示 CLI 链路可用。完整分层流程还可使用 `-se`（枚举）、`-sa`（资金层）；见下文「命令行」表。

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
python start-cli.py -h
```

机会枚举（分层回测第一步）：

```bash
python start-cli.py -se --strategy example
```

带资金的策略模拟：

```bash
python start-cli.py -sa --strategy example
```

全市场扫描（无参数时 `start-cli.py` 默认也是扫描）：

```bash
python start-cli.py -sc --strategy example
```

生成特征标签：

```bash
python start-cli.py -t
```

您也可以修改 `userspace/strategies/` 下的 settings 或 worker，自定义策略算法与目标。

Have fun `^_^`, 更多用法请参考这里 [更多用例](https://new-tea.cn/zh-hans/more-examples)

### 数据说明（请先看）

1. **仓库内置小数据**：只覆盖部分表，用于快速启动和演示。  
2. **获取更多（约 3 年）演示数据包**：用于更完整的策略验证/回测，请在 **[new-tea.cn](https://new-tea.cn)** 注册后下载，**清空** `setup/init_data/` 后只放入 **1 个** zip，再执行 `python setup/steps/import_data/install.py`（必要时加 `--force`）。  
3. **自有数据源**：也可自行接入（如 Tushare），详见 [userspace/data_source/README.md](userspace/data_source/README.md)。

## 支持一下项目

当您看到这里，说明您已经了解 NTQ 在做什么，也走过了安装与第一次跑策略的路径。若 NTQ 对您有用、您愿意持续关注它的演进，欢迎在 [GitHub](https://github.com/garnet1985/new-tea-quant) 或 [Gitee](https://gitee.com/garnet/new-tea-quant) 上为仓库点亮一颗 **Star**——这对个人开源项目而言，是非常实在的支持。

这是我第一次认真做开源，您的认可与反馈，是我继续打磨框架的最大动力。谢谢您！

### 欢迎一起交流早期使用体验

NTQ 目前在 **v0.x** 阶段，安装向导、文档和 Web UI 都还在改。不同系统、数据库和研究习惯差别很大，我一个人很难把所有情况都想到——如果您也愿意在本机按上文试试看，很欢迎一起聊聊：**哪里不顺手、哪句说明不好懂、哪段流程可以更省事**。

**互相交流、一起摸索**：您在实际研究里卡住的点，往往也是我需要补上的理解；您怎么用策略、怎么看回测结果，也常常能提醒我框架还缺什么。期待与您的交流。

**如何找到我？**您可以直接在gitee或者github私信我，或者到官网 **[联系我](https://new-tea.cn/zh-hans/contact)** 留言（无需注册也可填表单）。很期待听到您声音。

## 请注意
当前版本仍然是非正式版本 **v0.x** 框架现阶段不能保证任何API的稳定性，当版本进入1.0之后，API将基本稳定。详见 [CHANGELOG.md](CHANGELOG.md)。

## 文档维护约定

- **根目录 `README.md` 是仓库文档主入口**，用于对外说明项目用法与当前推荐流程。
- **命令入口统一为 `start-cli.py`**；如其他文档出现 `start.py`，以本页与 `python start-cli.py -h` 为准。
- **`docs/development/` 为内部工作区文档**，当前阶段不纳入对外文档整理范围。
- 每次版本发布至少同步更新：
  - `README.md`
  - `CHANGELOG.md`

## 开源仓库里包含什么？

| 内容 | 说明 |
|------|------|
| **框架代码** | `core/`、命令行（`start-cli.py`）与 UI 启动（`launcher.py`） |
| **Web UI** | `core/ui/bff` + `core/ui/fed`（发布构建产物已纳入仓库，日常无需 Node） |
| **示例策略** | 仅内置 **`example`** 策略，用于对照配置与接口 |
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
2. 在项目根目录执行 `python install.py`（或 `python start-cli.py` 触发自动安装），以刷新依赖与安装状态；若发布说明要求重导数据，再按「数据说明」运行 `setup/steps/import_data/install.py`。
3. 使用 Web UI 时，用 `python launcher.py` 启动即可（一般无需本地 `npm run build`，除非您自行改前端或文档另有说明）。

---

## 命令行（`start-cli.py`）

入口脚本：**`start-cli.py`**（无参时默认执行 **策略扫描 `scan`**，等同 `-sc`）。

```bash
python start-cli.py -h
```

| 用途 | 命令示例 |
|------|----------|
| 查看帮助 | `python start-cli.py -h` |
| 更新数据（renew） | `python start-cli.py -r` |
| 扫描机会（默认） | `python start-cli.py` 或 `python start-cli.py -sc --strategy example` |
| 仅枚举机会 | `python start-cli.py enumerate --strategy example` |
| 枚举器模拟 | `python start-cli.py -se --strategy example` |
| 价格因子模拟 | `python start-cli.py -sp --strategy example` |
| 资金分配模拟 | `python start-cli.py -sa --strategy example` |
| 价格+资金链路 | `python start-cli.py simulate --strategy example` |
| 分析结果摘要 | `python start-cli.py -a` |
| 标签计算 | `python start-cli.py -t` |
| 检查 core 更新（实现中...） | `python start-cli.py -u` |

**`--strategy`**：未指定时，若只有一个 `is_enabled=True` 的策略会自动选用；多个启用时默认取名称排序第一个并 **告警**，建议显式写 `--strategy`。

**说明**：文档与站点中若仍出现旧命令 `start.py`，请以本仓库 **`start-cli.py`** 为准。

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
