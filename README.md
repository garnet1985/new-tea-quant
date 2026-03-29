# New Tea Quant（NTQ）

## 为什么选择 NTQ？

如果你做 **A 股量化研究**，希望有一套 **边界清晰** 的本地框架：把 **数据源、指标、策略、标签** 拆开组合，而不是把所有逻辑堆在一个脚本里；并且希望从 **机会枚举 → 价格因子回放 → 资金约束下的组合模拟** 一条链路跑通——NTQ 就是为这种工作方式准备的。

本项目 **Apache 2.0 开源**，你可以自由学习、改造与扩展。**更完整的教程、概念说明与可视化阅读体验**在官方网站：**[new-tea.cn](https://new-tea.cn)**（中文）。建议把官网当作 **主文档入口**，本仓库的 `docs/` 作为离线补充。

当前版本 **v0.1.0**（`python -c "import core; print(core.__version__)"`）。详见 [CHANGELOG.md](CHANGELOG.md)。

---

## 开源仓库里默认有什么？

| 内容 | 说明 |
|------|------|
| **框架代码** | `core/` 与命令行工具，可本地运行 |
| **示例策略** | 仅内置 **`example`** 策略，用于对照配置与接口 |
| **演示行情等数据** | **默认不包含**；需自行接入数据源（如 Tushare）或从官网获取 |

**在 [new-tea.cn](https://new-tea.cn) 注册会员后**，可按官网说明 **下载 Demo 数据包**，以及 **momentum、random** 等额外策略资源，解压到本仓库约定的 `userspace/` 等路径后即可使用（具体步骤以 **官网当前页面** 为准）。

---

## 快速搭起来（本地）

**环境**：Python **3.9+**，数据库任选 PostgreSQL（推荐）/ MySQL / SQLite；建议 **8GB+** 内存。

```bash
git clone <你的仓库地址>
cd new-tea-quant
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
python install.py                 # 或: pip install -r requirements.txt
```

1. **数据库**：复制并编辑 `userspace/config/database/*.example.json` → 对应 `*.json`（勿提交真实密码）。说明见 [userspace/config/README.md](userspace/config/README.md)。  
2. **数据源（若不用官网 Demo 数据）**：例如 Tushare——在 `userspace/data_source/providers/tushare/` 放置 `auth_token.txt`（一行），或设置环境变量 `TUSHARE_TOKEN`。详见 [userspace/data_source/README.md](userspace/data_source/README.md)。  
3. **策略**：默认仅 `example`；其它策略与数据请通过 **官网会员资源** 或自行开发。配置模板：[userspace/strategies/settings_example.py](userspace/strategies/settings_example.py)。

更细的安装与配置也可对照仓库内 [docs/getting-started/installation.md](docs/getting-started/installation.md)；**以官网 [new-tea.cn](https://new-tea.cn) 的「快速开始」为准**。

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

若你希望 **捐赠或商业合作**，请以 **官网** 当前公示的联系方式或页面为准（若有单独「支持我们」入口，以站内说明为准）。

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
