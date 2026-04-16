<p align="center">
  <img src="https://new-tea.cn/sites/default/files/2026-01/logo_0.png" alt="New Tea Quant Logo" width="220" />
</p>

<p align="center">
  <a href="CHANGELOG.md"><img alt="Version" src="https://img.shields.io/badge/version-0.2.1-8A2BE2"></a>&nbsp;
  <a href="#"><img alt="Platform" src="https://img.shields.io/badge/platform-mac%20%7C%20linux%20%7C%20win-4CAF50"></a>&nbsp;
  <a href="#"><img alt="Python" src="https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white"></a>&nbsp;
  <a href="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml"><img alt="Build" src="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml/badge.svg"></a>&nbsp;
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache%202.0-007EC6"></a>
</p>

# New Tea Quant（NTQ）- A股量化交易研究框架
作者：Garnet Xin  
GitHub：<https://github.com/garnet1985/new-tea-quant> · Gitee：<https://gitee.com/garnet/new-tea-quant>

> For an English introduction, please see **[README_en.md](README_en.md)**.

> ## ⭐ 支持一下项目
> 如果您对项目有兴趣，并想持续关注，欢迎为仓库点亮一个 Star！  
> 这是我第一次尝试做开源项目，您的认可就是我前进的最大动力，谢谢您！

## NTQ 是什么？

您是不是心里有一些对股票操作策略的想法需要验证？比如是不是周线的RSI低于20我就可以买入？MACD的金叉银叉会有作用吗？追逐热门股票到底有多大胜率？我能不能把这些想法验证一下制定一个我自己的策略，然后用这个策略去扫描实时行情，找到我的投资机会？

当然可以，在NTQ里，这些都可以实现！

**NTQ**（New Tea Quant）是专门为了验证您的想法而诞生的一个量化策略框架，除了验证您的想法，这套框架还包含了一套完整的研究策略所需要的基础建设，可以单机使用。框架所有核心运算都支持多进程和多线程，只要您的电脑配置不是很低，框架都能高效地为您验证您的策略并且将策略应用的实时行情并把您的策略找到的机会反馈给您。

**特点** 框架不但能帮助您验证想法，并且提供了详细的日志和中间值，用多层方法验证策略的可行性，让您清晰看到策略如果不可行问题在哪里，可行的地方在哪里，让您能够更加精准地定位和调试。任何中间产生的数据都可回溯，结果都能复现。 

**请注意** NTQ本身是免费的，但里边有些功能是需要您对接第三方平台的，例如：
- **数据获取**：NTQ包含数据获取的功能，但不包括数据获取的付费/免费认证，您需要在第三方平台购买/注册数据后方可接入NTQ
- **机会通知**：如果您想要把您的策略扫描到的机会以某种方式进行通知、学习、交易等，此框架无法提供功能，需要您对接您的第三方平台（例如短信，邮件，云，交易软件等等）来完成后续动作，框架默认只在命令行里显示结果。

**另外** 此框架需要您有一些轻微的编程基础，或者使用AI辅助您。整个项目使用Python语言和PostgreSQL或者MySQL完成，您需要在您的本机上装有相应的语言和数据库软件（Python，PostgreSQL和MySQL都是免费的）

本项目 **Apache 2.0 开源**，您可以自由学习、改造与扩展。**更完整的教程、概念说明与可视化阅读体验**在官方网站：**[new-tea.cn](https://new-tea.cn)**（中文）。


## 快速安装（5分钟跑起来）

目标：**5 分钟内跑起框架 + 跑通 `example` 策略**。

### 前提条件

- 本机已安装可用的 Python 3.9+。  
- 本机已有可用数据库（MySQL 或 PostgreSQL）。

### 第 1 步：下载代码

可通过 `git clone`，也可以直接下载 zip：

```bash
git clone <仓库地址>
cd new-tea-quant
```

### 第 2 步：完成数据库设置

- 先创建一个新的数据库。  
- 在 `userspace/config/database` 填写数据库配置：  
  - 复制 `common.example.json` 并重命名为 `common.json`，填写要使用的数据库类型（MySQL 或 PostgreSQL）。  
  - 复制对应数据库配置文件并去掉 `.example`（例如 `mysql.example.json` -> `mysql.json`），填写数据库名、用户名、密码等连接信息。

### 第 3 步：安装并验证

```bash
python install.py
```

安装成功后，执行以下命令测试 `example` 策略：

```bash
python start-cli.py -sp
```

看到结果即表示已成功跑起第一个策略。

### 更多常用命令

查看帮助：

```bash
python start-cli.py -h
```

带资金的策略模拟：

```bash
python start-cli.py -sa
```

生成特征标签：

```bash
python start-cli.py -t
```

您也可以修改 `userspace/strategies/` 下的 settings 或 worker，自定义策略算法与目标。

Have fun `^_^`

### 数据说明（请先看）

1. **仓库内置小数据**：只覆盖部分表，用于快速启动和演示。  
2. **获取更多(3年)演示数据包**：用于更完整的策略验证/回测，请在 **[new-tea.cn](https://new-tea.cn)** 注册后下载放入setup/init_data后运行 python install.py 安装。（注意需要清空文件夹后再放入你的数据包，文件夹内只能有1个zip包）  
3. **自有数据源**：也可自行接入（如 Tushare），详见 [userspace/data_source/README.md](userspace/data_source/README.md)。

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
| **框架代码** | `core/` 与命令行工具，可本地运行 |
| **示例策略** | 仅内置 **`example`** 策略，用于对照配置与接口 |
| **演示行情等数据** | 包含一份可快速启动的小数据；更完整数据可从官网下载 |

## 如何联系到我？

您可以在以下网址给我留言（不用注册也可）：

**[new-tea.cn/zh-hans/contact](https://new-tea.cn/zh-hans/contact)**

框架是由我一人完成，工程量巨大，如有问题请您包容并及时反馈，谢谢您使用 NTQ。

## 分支策略是什么？

- **master**：最新版本，拒绝任何直接的 PR 或者提交

- **dev**：可从中建立分析，dev 会和 master 同步，到合适时机后会 merge 入 master 并且在 master 上建立 rc 分支用于 release，之后 release 代码会回到 dev

- **bugfix**：请使用 `bugfix/your-change` 的方式命名，否则无法 merge

- **feature**：请使用 `feature/your-change` 的方式命名，否则无法 merge

- **hotfix**：请使用 `hotfix/your-change` 的方式命名，否则无法 merge，分支只能从 rc 分支拉取

**Docker**：可用仓库内 `Dockerfile` 与 `docker-compose.yml` 拉起 PostgreSQL 与运行环境，步骤见 [docker/README.md](docker/README.md)。

## 有了新版本如何升级？

下载最新的master到您的本地，保留您本地的userspace文件夹，其他的都替换成新版本的文件即可。

---

## 命令行（`start-cli.py`）

入口脚本：**`start-cli.py`**（无参时默认执行与 `simulate_enum` 等价流程）。

```bash
python start-cli.py -h
```

| 用途 | 命令示例 |
|------|----------|
| 查看帮助 | `python start-cli.py -h` |
| 更新数据（renew） | `python start-cli.py -r` |
| 仅枚举机会 | `python start-cli.py enumerate --strategy example` |
| 枚举器模拟 | `python start-cli.py -se --strategy example` |
| 价格因子模拟 | `python start-cli.py -sp --strategy example` |
| 资金分配模拟 | `python start-cli.py -sa --strategy example` |
| 扫描机会 | `python start-cli.py -c --strategy example` |
| 分析结果摘要 | `python start-cli.py -a` |
| 标签计算 | `python start-cli.py -t` |

**`--strategy`**：未指定时，若只有一个 `is_enabled=True` 的策略会自动选用；多个启用时默认取名称排序第一个并 **告警**，建议显式写 `--strategy`。

**说明**：文档与站点中若仍出现旧命令 `start.py`，请以本仓库 **`start-cli.py`** 为准。

---

## 如何运行测试？

可以通过运行下列代码来实现，如果您要提交一个PR，请务必保证UT能跑过。

```bash
python -m pytest
```

## 支持、反馈与捐赠

- **文档与会员资源（Demo 数据、扩展策略等）**：[new-tea.cn](https://new-tea.cn)  
- **问题反馈、Issue / PR 预期**：[SUPPORT.md](SUPPORT.md)  
- **参与贡献**：[CONTRIBUTING.md](CONTRIBUTING.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)  
- **安全披露**：[SECURITY.md](SECURITY.md)  

若您希望 **捐赠或商业合作**，请以 **官网** 当前公示的联系方式或页面为准（若有单独「支持我们」入口，以站内说明为准）。

---

## 许可证与免责

本项目采用 **Apache License 2.0**，见 [LICENSE](LICENSE)。

**免责声明**：仅供学习与研究，不构成任何投资建议；回测结果不代表未来表现。

---

<details>
<summary>仓库内文档与归档</summary>

- 离线文档索引：[docs/README.md](docs/README.md)  
- 历史超长 README 归档：[docs/archive/README-root-before-slim-2026-03.md](docs/archive/README-root-before-slim-2026-03.md)（部分内容可能已过时，以本页与 <code>start-cli.py -h</code> 为准）

</details>
