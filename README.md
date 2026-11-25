# New Tea Quant（NTQ）- A股量化研究框架

<br/>

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/2026-01/logo_0.png" alt="New Tea Quant Logo" width="220" />
</p>

<p align="center">
  <a href="CHANGELOG.md"><img alt="Version" src="https://img.shields.io/badge/version-0.6.0-8A2BE2"></a>&nbsp;
  <a href="#"><img alt="Platform" src="https://img.shields.io/badge/platform-mac%20%7C%20linux%20%7C%20win-4CAF50"></a>&nbsp;
  <a href="#"><img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white"></a>&nbsp;
  <a href="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml"><img alt="Build" src="https://github.com/garnet1985/new-tea-quant/actions/workflows/ci.yml/badge.svg"></a>&nbsp;
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-NTQ%20%7C%20commercial%20by%20authorization-007EC6"></a>
</p>

> For an English introduction, please see **[here](README_en.md)**.

作者：Garnet Xin & 他的 AI 小伙伴

<a href="https://github.com/garnet1985/new-tea-quant"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-new--tea--quant-181717?logo=github&logoColor=white"></a>&nbsp;
<a href="https://gitee.com/garnet/new-tea-quant"><img alt="Gitee" src="https://img.shields.io/badge/Gitee-new--tea--quant-C71D23?logo=gitee&logoColor=white"></a>&nbsp;
<a href="https://new-tea.cn"><img alt="Website" src="https://img.shields.io/badge/website-new--tea.cn-009688?logo=google-chrome&logoColor=white"></a>

想直接安装？→ [一键安装](#一键安装)　·　[官网安装说明](https://new-tea.cn/zh-hans/setup)　·　[快速了解（图文）](https://new-tea.cn/zh-hans/quick-intro)　·　[教程](https://new-tea.cn/zh-hans/more-examples)　·　[注册会员](https://new-tea.cn/zh-hans/user/register)

---

## 当前版本（v0.6.0）

**使用条款更新**：0.5.3 及更早版本仍按 Apache-2.0，可自由使用。自 0.6.0 起采用 NTQ 条款：非商用仍遵循 Apache-2.0 原则；商用需作者授权。详见 [LICENSE](LICENSE) 与官网 [使用条款](https://new-tea.cn/zh-hans/disclaimer)。

**新茶量化 AI agent 上线了**：您只需要在 [官网注册会员](https://new-tea.cn/zh-hans/user/register) 后，每个月就会有一定额度的免费 AI agent 额度（猫粮）。新茶助手可以帮助您完成 app 里的任何操作，也包括写代码。会员凭证如何装载，见下方 [导入会员凭证](#导入会员凭证)。

摘要见 **[CHANGELOG.md](CHANGELOG.md)**。本版含破坏性改动（策略钩子、指标命名、库表、扫描后处理配置格式、Python ≥ 3.11、NTQ 许可证等）。

**0.6.x 及之后的版本中**：新茶量化将不再继续增加新的大块功能，之后的更新可能更多集中于：

- API 的锁定（锁定后不会带来破坏性改动）
- AI 智能体的开发
- 代码的清理与优化
- 文档整理与优化

---

## 新茶量化是什么？

新茶量化（New Tea Quant 或 NTQ）是一款 AI 赋能、对个人开发者友好、声明式驱动、插件化扩展的量化策略回测与研究框架。（**New Tea** 来自作者的宠物蓝猫「新茶」，也是应用内 AI 助理的名字。）

新茶量化本质上就做两件事：

- 把量化后的选股与交易策略放入历史数据中验证是否可行（验证「量化」准则）
- 把策略放入最新市场扫描，发现机会并报告给您（用「量化」准则找机会）

### 边界在哪里？

开源免费版只提供策略验证、调试及相关能力：

- **不包含**外部数据源（默认自带 2023-01-01 ～ 2025-12-31 的 300 只样本股演示数据）
- **不包含**自带的 AI 大模型（[注册会员](https://new-tea.cn/zh-hans/user/register) 后可使用新茶自带 AI，每月有一定免费额度）
- **不包含**扫描机会后的执行模块（如自动下单、短信等；会员可有一定额度的邮件发送服务）

[注册会员](https://new-tea.cn/zh-hans/user/register) 后会从「开源框架」进入「产品边界」，额外得到：

- 更多演示数据（300 只 → 全市场约 5800+ 只，时间范围不变；在应用 **设置 → 安装与维护** 中导入）
- 每月一定免费额度的 AI 用量（猫粮）
- 扫描机会后处理的邮件发送额度（一次性）

所有演示数据请勿商用。AI 回复仅供参考，新茶量化不对任何结果负责。

---

## 一键安装

进入**项目根目录**，然后：

```bash
python3 launcher.py
```

按 UI 提示安装即可（最简单是全部选默认）。更细的图文步骤见 [安装新茶量化](https://new-tea.cn/zh-hans/setup)。

**请注意**

- 安装与启动是同一条命令；若已安装过，会跳过安装直接启动。
- 本机 Python 命令可能不同（`python` / `python3`），启动器路径写法也可能不同（`launcher.py` / `./launcher.py`）。若上述命令失败，请尝试不同组合。
- 0.5.x 最低 Python 为 3.9；自 0.6.0 起为 **3.11**。建议 3.11–3.12：过新的 Python 上部分依赖可能尚无 wheel。可用 `python3 --version` 查看版本。

---

## 导入会员凭证

如果您想获得更多新茶量化的服务，包括：

- 更多演示数据（从 300 只股票变成全市场约 5800+ 只、3 年数据）
- 新茶 AI 助手（每月赠送一定额度）
- 扫描后处理的邮件发送演示额度（一次性）

可在官网 [注册会员](https://new-tea.cn/zh-hans/user/register)，再用通用凭证把本机应用与官网服务关联起来。官网图文版见 [安装说明 · 导入会员凭证](https://new-tea.cn/zh-hans/setup)。

1. 完成 [注册](https://new-tea.cn/zh-hans/user/register) 后，在主页最右上角点击会员头像，进入个人主页：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2012.01.06.png" alt="进入个人主页" width="800" />
</p>

2. 在个人信息下方可以看到猫粮（AI 额度）和**通用凭证**（官网展示可能已脱敏；您自己的应是一串随机文字）。复制通用凭证：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2012.02.22.png" alt="复制通用凭证" width="800" />
</p>

3. 打开新茶量化应用，进入 **设置 → 会员**，找到通用凭证入口，粘贴后装载；成功时会有绿色标签提示：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2012.04.39.png" alt="设置中粘贴通用凭证" width="800" />
</p>

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2012.11.36.png" alt="凭证装载成功" width="800" />
</p>

**注意**：通用凭证相当于产品使用密码，请妥善保管。一旦泄漏，请马上回官网刷新凭证，再重新导入。

---

## 新茶量化能做什么？

下列功能都可通过新茶 AI 助手完成，也可由本地智能体（如 Workbuddy、Harness、TreaWorker、豆包等）直接调用。更完整的图文见 [快速了解](https://new-tea.cn/zh-hans/quick-intro)。

**注意**

- 安装是默认数据库为 DuckDB，同一时刻只能有一个进程写入。若本机用户界面与第三方智能体同时跑 NTQ，可能因为互相争抢而导致一方失败；注意使用的时候建议只开启一个应用。MySQL / PostgreSQL 则没有这个问题。

### 量化策略的制定与回测

通常有 **2 种方式**制定策略：

- 在用户空间按示例建立策略，在 `strategy.py` 写入发现机会的逻辑，在 `settings.py` 写入参数。
- 直接使用新茶 AI 助手，讨论需求并让它完成代码并报告结果。

同样有 **2 种调试方式**：

- 改动 `settings.py` 得到不同结果。任何配置改动都会生成策略新版本，可随时对比并在版本间切换。
- 通过对话指挥 AI 助手改参数调试。

回测共 **4 步**，每步可单独运行并有各自报告；AI 也可帮您完成任一步：

- **机会盘点**：在历史数据中找齐机会，盘点多寡与集中度，验证策略找机会的能力与特性。
- **价格回测**：过滤重复机会后，看这些机会能否完成投资目标，检验策略是否具备基本盈利能力。
- **投资模拟**：给定虚拟仓位与资金管理策略，模拟能否抓住上一步的盈利空间——最接近实盘的自动模拟。
- **决策模拟**：与上一步相同，但改由您亲自决定投谁、投多少。这是验证策略是否适合您的关键一步，也覆盖许多回测工具忽略的「临场抗压」对判断的影响。

另外还有：

- **参数归因**：看参数如何影响结果方向与敏感度（需安装机器学习插件）。
- **滚动对照**：对不同时间段滚动回测并对比结果。

#### 策略调试界面

制定策略界面：顶部是策略信息，左侧是参数，右侧是执行面板与报告。

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.01.25.png" alt="制定策略界面" width="800" />
</p>

价格回测的报告：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.50.30.png" alt="价格回测报告" width="800" />
</p>

点开一只股票的回测结果，可清晰看到机会的入口与出口：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.51.15.png" alt="单股回测入口出口" width="800" />
</p>

对比相同策略不同版本之间的结果差异：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.52.03.png" alt="策略版本对比" width="800" />
</p>

也可以对比改了哪些参数导致结果差异：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.53.13.png" alt="参数差异对比" width="800" />
</p>

价格层归因报告示例——反映参数调成不同数字时结果会如何变化：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.55.02.png" alt="价格层归因报告" width="800" />
</p>

滚动对照——在不同时间段回测并对比：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.56.08.png" alt="滚动对照" width="800" />
</p>

决策者模式——模拟时间推进，由您亲自做投资决策：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2011.18.20.png" alt="决策者模式界面" width="800" />
</p>

随着时间推进，可看到决策在之后的盈亏状态，用自己的策略在历史中模拟实盘：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2011.19.57.png" alt="决策者模式盈亏推进" width="800" />
</p>

也可以直接让新茶 AI 助手完成回测：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.57.02.png" alt="AI 助手回测对话" width="480" />
</p>

AI 助手汇报的回测结果：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2015.58.07.png" alt="AI 助手回测结果" width="480" />
</p>

### 策略选股

调试好的策略可用来扫描市场上满足条件的股票；再通过[扫描后处理](#扫描机会后续处理)接入自动交易、过滤、通知、机器学习等。若无后续处理，界面上仍能看到扫描结果。

**注意**

- 目前只提供演示数据；要拿最新数据需自行接入数据源。
- 扫描后处理需自行配置或接入；会员默认有一定数量的通知邮件演示额度。

策略选股界面：演示模式会用配置的最新交易日扫描（模拟）；严格模式会探测现实中的最新交易日，数据不足则拒绝扫描。

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.09.37.png" alt="策略选股界面" width="800" />
</p>

扫描结果报告；可再经扫描后处理做过滤、通知、交易、分析等：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.12.59.png" alt="扫描结果报告" width="800" />
</p>

### 特征标签

可简单理解成量化里的「因子」：用代码把特征抽象出来，绑定到实体上。例如市值超过 50 亿为「大」、否则为「小」，提前算好后可广泛用于任意策略，不必在策略里现算。积累特征值，本质上就是积累自己的因子库。

特征标签列表与可产出标签：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.14.58.png" alt="特征标签列表" width="800" />
</p>

产出标签可按类型可视化：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.15.21.png" alt="特征标签可视化" width="800" />
</p>

### 数据源接入（外部）

提供接入外部数据源的框架：多线程、按您定义的限流规则拉取以防被禁，支持配置化接入、错误重试、断点续传等。

数据源界面——可查看接入了哪些源、如何更新、是否最新：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.17.12.png" alt="数据源接入界面" width="800" />
</p>

### 数据契约

「配置驱动」的主体之一：用契约标准化数据结构和读取方式，需要数据时只要「声明」即可自动注入。

数据契约列表——可声明注入的数据、key、类型等：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.19.03.png" alt="数据契约列表" width="800" />
</p>

### 走势关联

用来看多条序列的相关性与延迟：A 与 B 是否反向、是否领先滞后，或宏观事件如何影响市场资金等。

走势关联界面（示例：两只银行股与一只酒股的收盘价）：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.20.56.png" alt="走势关联界面" width="800" />
</p>

对比结果：两只银行更接近同向（相关度约 0.73），酒与银行接近反向（相关度为负）：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.22.19.png" alt="走势关联结果" width="800" />
</p>

### 扫描机会后续处理

文档中也称扫描后处理：扫描结束后如何处理机会。可创建多个方案，每个方案从可执行单元（adapter）中选取能力；扫描结束后自动按依赖排序执行。

**注意**

- 开箱可用的单元目前只有 2 个：**presenter**（展示机会时读取回测表现）、**ntq email service**（经官网发通知邮件；会员一次性演示额度，用完为止）。
- 其余单元多为演示，需自行写代码或取得第三方认证后使用。

方案列表（含步骤与可用状态）：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.24.50.png" alt="扫描后处理方案列表" width="800" />
</p>

小处理单元列表：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.25.13.png" alt="扫描后处理单元列表" width="800" />
</p>

制定方案并放入一个或多个单元，系统会按依赖自动排序执行：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-24%2016.25.35.png" alt="扫描后处理方案编辑" width="800" />
</p>

### 设置

个人偏好与系统配置（含会员凭证、演示数据截断日、缓存清理等）。[官网注册会员](https://new-tea.cn/zh-hans/user/register) 后可使用部分 AI / 邮件额度；凭证装载步骤见 [导入会员凭证](#导入会员凭证)。

### 命令行

主要功能均支持命令行直接运行，按角色使用不同入口：

```bash
python cli.py     # 用户：集中了日常命令，下图为帮助
python devcli.py  # 开发者：开发快捷指令，下图为帮助
```

用户 `cli.py` 帮助：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2011.25.38.png" alt="cli.py 帮助" width="800" />
</p>

开发者 `devcli.py` 帮助：

<p align="center">
  <img src="https://new-tea.cn/sites/default/files/inline-images/%E6%88%AA%E5%B1%8F2026-11-25%2011.25.22.png" alt="devcli.py 帮助" width="800" />
</p>

可脱离 UI 使用，或二次开发。

---

## 请为 NTQ 点亮一颗星

[GitHub](https://github.com/garnet1985/new-tea-quant) · [Gitee](https://gitee.com/garnet/new-tea-quant)　·　反馈：[官网留言](https://new-tea.cn/zh-hans/contact)

## 许可与支持

详见 [LICENSE](LICENSE) 与官网 [使用条款](https://new-tea.cn/zh-hans/disclaimer)。非商用与商用条款以许可证与 [CHANGELOG](CHANGELOG.md) 为准。

---
