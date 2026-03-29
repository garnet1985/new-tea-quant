# New Tea Quant（NTQ）- A股量化交易研究框架

作者：Garnet

## 为什么选择 NTQ？

您是不是心里有一些对股票操作策略的想法需要验证？比如是不是周线的RSI低于20我就可以买入？MACD的金叉银叉会有作用吗？追逐热门股票到底有多大胜率？我能不能把这些想法验证一下制定一个我自己的策略，然后用这个策略去扫描实时行情，找到我的投资机会？

当然可以，在NTQ里，这些都可以实现！

**NTQ**（New Tea Quant）是专门为了验证您的想法而诞生的一个量化策略框架，除了验证您的想法，这套框架还包含了一套完整的研究策略所需要的基础建设，可以单机使用。框架所有核心运算都支持多进程和多线程，只要您的电脑配置不是很低，框架都能高效地为您验证您的策略并且将策略应用的实时行情并把您的策略找到的机会反馈给您。

**特点** 框架不但能帮助您验证想法，并且提供了详细的日志和中间值，用多层方法验证策略的可行性，让您清晰看到策略如果不可行问题在哪里，可行的地方在哪里，让您能够更加精准地定位和调试。任何中间产生的数据都可回溯，结果都能复现。 

**请注意** NTQ本身是免费的，但里边有些功能是需要您对接第三方平台的，例如：
- **数据获取**：NTQ包含数据获取的功能，但不包括数据获取的付费/免费认证，您需要在第三方平台购买/注册数据后方可接入NTQ
- **机会通知**：如果您想要把您的策略扫描到的机会以某种方式进行通知、学习、交易等，此框架无法提供功能，需要您对接您的第三方平台（例如短信，邮件，云，交易软件等等）来完成后续动作，框架默认只在命令行里显示结果。

**另外** 此框架需要您有一些轻微的编程基础，或者使用AI辅助您。整个项目使用Python语言和PostgreSQL或者MySQL完成，您需要在您的本机上装有相应的语言和数据库软件（Python，PostgreSQL和MySQL都是免费的）

本项目 **Apache 2.0 开源**，您可以自由学习、改造与扩展。**更完整的教程、概念说明与可视化阅读体验**在官方网站：**[new-tea.cn](https://new-tea.cn)**（中文）。

## 请注意
当前版本仍然是非正式版本 **v0.1.0** 框架现阶段不能保证任何API的稳定性，当版本进入1.0之后，API将基本稳定。详见 [CHANGELOG.md](CHANGELOG.md)。

## 有演示数据让我试试水吗？
有的。您可以在**[new-tea.cn](https://new-tea.cn)**注册会员后获取一份演示数据（仅供演示）和更多演示策略（框架默认带了一个演示策略），您可以按照指示下载到本地放入相应位置然后运行install.py进行安装

完成会员注册后可以在 **[new-tea.cn/zh-hans/user](https://new-tea.cn/zh-hans/user)** 下找到演示数据和策略，按照内容提示放在相应的位置安装即可。

## 开源仓库里包含什么？

| 内容 | 说明 |
|------|------|
| **框架代码** | `core/` 与命令行工具，可本地运行 |
| **示例策略** | 仅内置 **`example`** 策略，用于对照配置与接口 |
| **演示行情等数据** | **默认不包含**；需自行接入数据源（如 Tushare）或从官网获取 |

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

---

## 快速搭起来框架（本地）

**环境**：Python **3.9+**，数据库任选 PostgreSQL（推荐）/ MySQL；建议 **8GB+** 内存。

```bash
git clone <仓库地址>
cd new-tea-quant
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
python install.py                 # 或: pip install -r requirements.txt
```

1. **数据库**：复制并编辑 `userspace/config/database/*.example.json` → 对应 `*.json`（勿提交真实密码）。说明见 [userspace/config/README.md](userspace/config/README.md)。  
2. **数据源（若不用官网 Demo 数据）**：例如 Tushare——在 `userspace/data_source/providers/tushare/` 放置 `auth_token.txt`（一行），或设置环境变量 `TUSHARE_TOKEN`。详见 [userspace/data_source/README.md](userspace/data_source/README.md)。  
3. **策略**：默认仅 `example`；其它策略与数据请通过 **官网会员资源** 或自行开发。配置模板：[userspace/strategies/settings_example.py](userspace/strategies/settings_example.py)。

更细的安装与配置也可对照仓库内 [docs/getting-started/installation.md](docs/getting-started/installation.md)；**以官网 [new-tea.cn](https://new-tea.cn) 的「快速开始」为准**。

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
