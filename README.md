# New Tea Quant（NTQ）- A股量化研究框架

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

想跳过介绍、直接安装？请看 [快速安装 + 运行一个策略](#quick-start)。其他入口：[为什么用 NTQ](#why) · [点亮一颗星](#star) · [常用命令](#cli) · [教程](https://new-tea.cn/zh-hans/more-examples) · [官网](https://new-tea.cn)

## 当前版本（v0.4.x）

最近更新摘要：

**[v0.4.5](CHANGELOG.md)**

- **策略支持回测归因**：使用统计学原理对单因素和机器学习对多因子对回测结果的贡献度进行归因解释。
- 更多更新请参见 [CHANGELOG.md](CHANGELOG.md)。

**接下来**

- **[v0.5.x](ROADMAP.md)**：决策者模式（第四层回测：按交易日回放、自己挑选每日机会）及其报告。
- **[v0.5.x](ROADMAP.md)**：AI 助理（辅助写策略代码、解释回测报告、应用内小百科）。
- 详见 [ROADMAP.md](ROADMAP.md)。

## NTQ 是什么？

**New Tea Quant**（NTQ）是一款对个人开发者友好、轻量级、高性能量化策略回测与研究框架。（**New Tea**这个名字来源于作者的宠物蓝猫，她的名字就叫“新茶”）

NTQ 本质上就做两件事：

- 帮助您把脑海中的选股和交易策略通过代码放入历史数据中验证是否可行。
- 通过代码把您脑海中的选股策略放入最新的市场中进行扫描，发现机会并报告给您。

当然，NTQ 还有很多其他功能，您可以在 [NTQ 还能做什么](#can) 找到更多信息。

<a id="star"></a>
## 请为NTQ点亮一颗星

如果您喜欢NTQ并且愿意支持一下NTQ的发展，请您为这个项目在 [GitHub](https://github.com/garnet1985/new-tea-quant) 或 [Gitee](https://gitee.com/garnet/new-tea-quant) 点亮一颗星。您的支持和肯定就是作者前进的最大动力。

同时，NTQ也需要您的反馈，如果您发现了任何bug，或者有什么想法，欢迎您在[官网留言](https://new-tea.cn/zh-hans/contact)交流。更完整的参与方式见 [如何参与](#participate)。

<a id="why"></a>
## NTQ 和其他平台有什么显著不同？我为什么要用 NTQ？

NTQ 开发的动机是作者本来想自己研究量化，但是碍于市面上各种工具无法完美适配需求，最后自己研发了一款以个人 PC 和 A 股为基底的研究工具。

- **NTQ 是作者帮您默认规避了这些坑的。**

  > 您有想过为什么在回测框架里测试的策略一跑就是最 NB 的收益率，但是去实盘就挨最毒的打吗？那可能是因为：

  - **您的数据可能有幸存者偏差。** 您在那些股票网站可以看到的股票都是至今还活着的，您的策略在回测的时候有把那些最后退市的股票算进去吗？如果您的策略不幸买到了这些股票，它们很可能会导致您产生巨额亏损。如果您的回测中没有算上这些股票，您的收益率和胜率当然会更高。

  - **您仔细了解过复权价格是怎么来的吗？** 它和原始价格有什么区别？如果您自己的回测当中都是使用复权价格来推算收益和止盈止损，那么几乎可以断定回测是不准确的。前复权价格是调整过的价格，可能会导致您的仓位管理过于乐观。而且，如果您使用前复权价格推算收益，在一些极端的情况下，一些股票的前复权价格可能是负数；如果您在负数价格模拟买入，您的收益率一定是负数，无论是不是真的亏损。这些坑您注意到了吗？

  - **就算您的策略真的能盈利，那么是那几个极端的股票带动的，还是大家都在稳步增长？** 您在出现多个机会的时候如何抉择？您的中间数据是不是能持久化、随时查看？您运行完策略之后是不是知道您的收益分布特征？如果您不容易找到这些信息，那么您就无法真正找到那个适合您的策略。

  - **即使您得到了一个可行的策略，这个策略真的适合您吗？** 如果这个策略是在最大要承受 80% 的亏损去搏取 200% 的收益呢？您能承受这种心理压力吗？能保证在只剩 20% 的仓位下严格执行纪律最终变成 200% 吗？还是您更愿意承受 10% 的亏损去赢得 20% 的收益呢？NTQ 有决策者模式（**[v0.5.x](ROADMAP.md)** 即将上线）能帮助您模拟交易日期的推进和仓位变化，让您身临其境，从而选择自己真正能够得心应手的策略。

  - **很多工具都能很好地支持每个股票单独运行自己的回测，但如果回测的时候股票与股票之间有依赖呢？** 比如您要取当天交易量最高的前 5 个股票进行投资，这种情况下单股回测的方式会变得极其复杂和低效。但 NTQ 同时支持单股独立运行和时间切片模式：如果您的股票没有相互依赖，如同大多数框架，NTQ 会高效地完成它们的回测；如果有依赖，不用担心，NTQ 有专门针对这种情况的切片模式，它能让您在不增加太大复杂度（只需要多定义一层筛选函数）的情况下同样高效地完成工作。

  - **您的回测是不是就是回测一遍就完成了？** 只看到收益率、胜率和夏普率这些基本参数就能下定论了？NTQ 做得比这个流程严谨许多。NTQ 一共规划了 4 层回测：第一层是机会枚举，就是帮您找到您的策略在巨大的股票池中能找到的所有机会，它们多还是少？分散还是集中在少数股票等等。第二层是价格因子回测，能验证您的策略是不是能在承受一定风险的时候真正捕获到一只股票的价格波动。第三层是交易模拟，会有一个初始资金，模拟人工交易，看到最终的收益能力、分布和收益情况。第四层是决策者模式（**[v0.5.x](ROADMAP.md)**），对交易日历进行回放，让您自己选择每日扫描出的机会，看看是不是您能严格遵守交易纪律、承受风险并最终完成盈利。当前 UI 可跑前三层。

还有很多很多的大坑小坑，NTQ 在自己的回测引擎内置了各种各样的可交易性模块帮您规避这些风险，让您真正得到可靠的结果，而不是随便找些数据、随便写一些脚本就能跑出的策略。

- **NTQ 做了对个人 PC 的优化。** 其他量化框架（部署在个人 PC 上的）都没有很强的内存管理能力，需要用户自己处理和承担后果。如果您的数据量一大，个人 PC 很可能因为内存不够而导致死机和蓝屏。NTQ 在运行回测任务的时候使用了 CPU 与内存规划，在速度和稳定性之间寻找到了平衡点，让个人 PC 也能运行超过 PC 内存大小的数据回测。

- **NTQ 是深度绑定中国市场的。** 如果您使用的是其他各种流行的框架，它们大部分都是从「美股」或者国外金融市场改造进入「A 股」模式的，改造过程中有很多很多的坑或者错误可能需要发现和买单；而 NTQ 一开始就面向中国 A 股，免去了这些麻烦。

- **NTQ 是配置声明式的。** 不同于很多其他框架，NTQ 的代码量要求较少，大部分是类似 JSON 的配置声明。您的策略由 2 个基本文件组成：`strategy.py` 和 `settings.py`。

在 **`settings.py`** 里，您能配置回测过程中的绝大部分信息：

- 交易基本信息
- 风险控制
- 交易目标
- 回测需要的数据
- 股票池
- ……

完整字段说明见安装后生成的 `userspace/strategies/settings_example.py`。

<details>
<summary><strong>settings.py 配置示例（点击展开）</strong></summary>

比如您要设置一个简单的目标：盈利 30% 就平仓，亏损 20% 就止损：

```python
"goal": {
    "stop_loss": {"stages": [{"ratio": -0.2, "close_invest": True}]},
    "take_profit": {"stages": [{"ratio": 0.3, "close_invest": True}]},
}
```

或者更复杂的多段 + 目标变化配置：如果我买入股票，最多持有 100 个交易日，止损 20%。如果盈利达到 15% 我就设置保护止损到成本就止损。然后到盈利 30% 我就卖出一半，到盈利 50% 我就卖出 40%，剩下的 10% 变成动态止损，当回撤大于 15% 的时候就止损。您只需要这样配置：

```python
"goal": {
    "expiration": {"fixed_window_in_days": 100, "mode": "trading_day"},
    "stop_loss": {"stages": [{"ratio": -0.2, "close_invest": True}]},
    "take_profit": {
        "stages": [
            # 盈 15%：不卖，把止损抬到成本
            {"ratio": 0.15, "exit_ratio": 0, "actions": ["set_protect_loss"]},
            # 盈 30%：卖掉当前仓位的一半（相当于原始仓位的 50%）
            {"ratio": 0.3, "exit_ratio": 0.5},
            # 盈 50%：再卖掉仓位的 40% 其余 10% 交给动态止损
            {"ratio": 0.5, "exit_ratio": 0.4, "actions": ["set_dynamic_loss"]},
        ]
    },
    "protect_loss": {"ratio": 0, "close_invest": True},
    "dynamic_loss": {"ratio": -0.15, "close_invest": True},
}
```

再比如配置回测所需要的数据的例子：
我在回测过程中需要注入日 K 线、公司财务和 CPI 数据，我可以这么配置：

```python
"data": {
    "base": {
        "data_key": "stock.kline.daily",
        "params": {"adjust": "qfq"},
    },
    "required": [
        {"data_key": "stock.finance.quarterly"},
        {"data_key": "macro.cpi"},
    ],
}
```

如果我还需要给 K 线加上 MACD 指标，我可以这样声明：

```python
"data": {
    "base": {
        "data_key": "stock.kline.daily",
        "params": {"adjust": "qfq"},
        "indicators": {
            "macd": [{"fast": 12, "slow": 26, "signal": 9}],
        },
    },
}
```

</details>

---

在 **`strategy.py`** 里，单股入场只需实现 `has_opportunity`（可对照安装后的演示策略 **RSI超跌反弹v1**）；切片筛选、组合挑选和自定义目标按需再写：

- **`has_opportunity(ctx)`**：当日该股票是否有买入机会。能读到「当前日期为止」的数据，做完计算后返回 `True` / `False`（没有机会就 `False`，框架跳过）。
- **`on_calendar_asof(ctx)`**：切片模式（`slice_based`）用。拿到当前日期为止、全部股票的数据，先做初步过滤，返回要进入单股判定的股票 id 列表，随后对这些股票调用 `has_opportunity`。
- **`on_pick_portfolio_member(ctx)`**：处理组合容量。例如最大持股 3 只，当日却扫出 10 个机会，在这里决定选择哪 3 个机会。

另外，您也可以自定义目标：在 `settings.py` 的某一段止盈 / 止损上写 `"custom": "规则名"`，再实现 **`is_take_profit`** / **`is_stop_loss`**，自行决定何时触发、触发后卖多少仓位。

<details>
<summary><strong>strategy.py 钩子示例（点击展开）</strong></summary>

```python
# 举例：如果RSI参数小于20就算是一个机会：
def has_opportunity(self, ctx: StrategyContext) -> bool:
    # 当日这只股票的日 K（含 settings 里声明的指标）；最后一根就是今天
    klines_daily = ctx.data.items.get("stock.kline.daily") or []
    if not klines_daily:
        return False
    # 从所有K线中取最后一根，也就是今天的
    kline_today = klines_daily[-1]
    # 从今日的K线中读取RSI参数
    rsi = kline_today.get("rsi14")  
    # （可选步骤）把当日的RSI数值记录下来，后续会对结果进行归因的时候使用
    ctx.capture("rsi", rsi)  

    # 如果 RSI 存在且小于 20 就返回 True 代表有机会 
    # 通常来说，这个20是定义在settings.core里的，这样UI就可以看到并通过修改参数得到不同的结果
    return rsi is not None and rsi < 20
```

- **`on_calendar_asof(ctx)`**：切片模式（`slice_based`）用。拿到当前日期为止、全部股票的数据，先做初步过滤；筛出的股票 id 放进 `CalendarAsOfResult` 返回，随后对这些股票调用 `has_opportunity`。

```python
# 举例：选出当日换手率最高的 3 只股票，再交给 has_opportunity
def on_calendar_asof(self, ctx: StrategyContext) -> CalendarAsOfResult:
    today = str(ctx.data.now or "")
    ranked = []

    # ctx.data.by_entity：股票池里每一只、截至当天的数据
    for stock_id, payload in (ctx.data.by_entity or {}).items():
        # 换手率在日度指标里，需在 settings.data.required 声明 stock.indicators.daily
        rows = payload.get("stock.indicators.daily") or []
        if not rows:
            continue
        # 最后一条就是今天
        indicator_today = rows[-1]
        turnover = indicator_today.get("turnover_rate")
        if turnover is None:
            continue
        ranked.append((turnover, stock_id))

    # 按换手率从大到小排，取前 3 只
    ranked.sort(reverse=True)
    top3 = [stock_id for _, stock_id in ranked[:3]]

    # CalendarAsOfResult：告诉框架「今天筛出了哪些股票」
    return CalendarAsOfResult(as_of_date=today, stocks=top3)
```

- **`on_pick_portfolio_member(ctx)`**：处理组合容量。例如最大持股 3 只，当日却扫出 10 个机会，在这里决定选择哪 3 个机会。

```python
# 举例：当日机会很多时，挑价格最高的 3 只买入
def on_pick_portfolio_member(self, ctx: StrategyContext):
    # 当日扫出来、还没进组合的机会
    opportunities = ctx.data.items.get("opportunities") or []
    # 组合还剩几个空位（已持仓会占掉槽）
    remaining = (ctx.data.items.get("account") or {}).get("remaining_slots") or 0

    ranked = []
    for opp in opportunities:
        # trigger_price：这只股票当日的信号价（通常是收盘价）
        price = opp.trigger_price
        ranked.append((price, opp))

    # 按价格从高到低排，取前 3 只，且不超过剩余空位
    ranked.sort(key=lambda item: item[0], reverse=True)
    n = min(3, remaining)
    return [opp for _, opp in ranked[:n]]
```

自定义止盈 / 止损：在 `settings.py` 某一段上写 `"custom": "规则名"`，框架就会来问 `is_take_profit` / `is_stop_loss` 今天要不要触发。

```python
# settings.py：这一段止盈不写固定比例，交给 strategy.py 自己判断；close_invest 表示全部平仓
"take_profit": {"stages": [{"custom": "up_20pct", "close_invest": True}]}

# strategy.py
# 举例：相对买入价涨了 20% 就止盈
def is_take_profit(self, ctx: StrategyContext, *, custom: str, stage) -> bool:
    if custom != "up_20pct":
        return False

    # 持仓监控时，框架直接给你今天这根 K 线
    bar = ctx.data.items.get("bar") or {}
    close = bar.get("close")
    # 买入成交价
    entry_price = ctx.data.items.get("entry_price") or 0
    if close is None or not entry_price:
        return False

    return close >= entry_price * 1.2
```

`is_stop_loss` 写法相同，只是把规则写在 `stop_loss.stages` 上。

</details>

### NTQ 和其他平台的不同之处

对比对象是量化圈子里最常用的开源回测框架（不限市场）：[Backtrader](https://www.backtrader.com/)、[Zipline](https://github.com/stefan-jansen/zipline-reloaded)、[vectorbt](https://vectorbt.dev/)、[backtesting.py](https://kernc.github.io/backtesting.py/)。

| | **NTQ** | **Backtrader** | **Zipline** | **vectorbt** | **backtesting.py** |
| --- | --- | --- | --- | --- | --- |
| 定位 | 个人 PC 上的 A 股研究 + 扫描 | 事件驱动通用回测 | 管道式研究回测 | 向量化高速回测 / 因子 | 轻量单标的事件回测 |
| 本机跑全市场 | CPU与内存调度，防止内存溢出 | 内存需要自己管理 | 非常吃内存 | 快但矩阵同样吃内存 | 单标的为主，全市场要自己套 |
| 默认市场心智 | 从 A 股出发 | 通用，默认更像美股玩法 | 美股 / 美元计价心智 | 市场无关，数据自备 | 市场无关，数据自备 |
| 退市 / 幸存者 | 默认 PIT 股票池 | 您喂什么数据就是什么 | 官方数据包较好；自备数据则不管 | 您喂什么数据就是什么 | 您喂什么数据就是什么 |
| 信号价 / 成交价 | 复权做信号，实际价成交 | 喂什么价用什么价 | 常用复权序列，双轨需要自己搞定 | 喂什么价用什么价 | 喂什么价用什么价 |
| 横截面（如 Top-N） | 原生带有横截面切片模式 | 通常自己循环全市场 | 管道能做，不轻松 | 矩阵擅长；可交易性要自补 | 不擅长全市场截面 |
| 回测怎么拆 | 枚举 → 价格 → 资金 → 决策者 | 常见一条净值曲线 | 常见一条回测流程 | 一条向量化回测 | 常见一条净值曲线 |
| 决策者（身临其境） | **[v0.5.x](ROADMAP.md)** 即将上线 | 无 | 无 | 无 | 无 |
| Web 报告 / 逐股路径 | 自带工作台 | 需自己画 | 研究笔记本 | Jupyter / 自己画 | 自带简单图表 |

<a id="participate"></a>
### 如何参与（任选其一）

| 方式 | 适合 |
|------|------|
| [GitHub Issues](https://github.com/garnet1985/new-tea-quant/issues) | Bug、功能建议（推荐，便于跟踪） |
| [Gitee Issues](https://gitee.com/garnet/new-tea-quant/issues) | Bug、功能建议（推荐，便于跟踪） |
| [官网留言](https://new-tea.cn/zh-hans/contact) | 无需注册也可填表单 |
| GitHub / Gitee 私信 | 简短交流、不方便公开的细节 |

提 Issue 时如能附上：**系统（Win / macOS / Linux）、Python 版本、做到第几步、截图或报错摘要**，会大大加快排查。贡献说明见 [CONTRIBUTING.md](CONTRIBUTING.md) · [SUPPORT.md](SUPPORT.md)。

## 使用 NTQ 需要什么技能？

NTQ 能帮助您将您的想法进行验证，您可能需要：

- 了解基本的金融术语和市场规则
- 脑海中能把自己找到的「潜力股」抽象成算法的方式（**[v0.5.x](ROADMAP.md)** 将集成 AI 辅助，当前还不支持）
- 一些基本的 Python 编程能力，能把「想法」落地成代码（**[v0.5.x](ROADMAP.md)** 将加入 AI 辅助写代码，当前还不支持）
- 一些基本的统计学知识，能看懂基本的回测报告（同样，**[v0.5.x](ROADMAP.md)** 会有 AI 辅助解释报告，现阶段还不支持）

## NTQ 不能做什么？

NTQ 是一个回测器，无法提供：

- **持续稳定的数据源**（需要您自己对接数据源）。仓库自带约 3 年、**300 只**股票的演示数据；注册后可在[会员页面](https://new-tea.cn/zh-hans/user/)另下全 A 约 3 年包（见 [数据说明](#data)）。
- **实盘交易。** NTQ 不支持实盘，但提供扫描结果的处理接口（[`adapter`](core/modules/adapter/README.md) 模块）。如果您懂得如何接入第三方交易软件或者平台，可以把扫描得到的机会交给下游处理。

## NTQ 如何跑起来？

NTQ 不需要任何第三方外部服务依赖。只要您的电脑装有 [Python](https://new-tea.cn/zh-hans/install-python)（≥3.9），克隆代码即可一键运行，把时间留给策略，而不是配环境。

对于一般的使用者，只需要下载代码，在命令行里进入 NTQ 的根目录，运行：

```bash
python launcher.py
```

然后按照用户界面进行安装就可以了。

但如果您是开发者，还是建议使用 [**MySQL**](https://dev.mysql.com/downloads/) 或者 [**PostgreSQL**](https://www.postgresql.org/download/) 来存放数据，所以您需要单独安装其中一种数据库。

更完整的步骤见下方 [快速安装 + 运行一个策略](#quick-start)。

<a id="can"></a>
## NTQ 还能做什么？

NTQ 还可以：

- **快捷操作数据库：** NTQ 支持 [DuckDB](https://duckdb.org/)、[MySQL](https://dev.mysql.com/) 和 [PostgreSQL](https://www.postgresql.org/)，并且配有一套轻量级的 [ORM 操作 API](core/infra/db/README.md)。
- **自定义数据源：** NTQ 有接入外部数据源的一套完整工具。一个数据源（比如公司财务数据）可以接入多个数据供应商，并且默认带有限流、等待等模式，支持多种数据存入（增量、覆盖、滚动刷新）模式。说明见 [core/modules/data_source/README.md](core/modules/data_source/README.md)。
- **自定义数据契约：** NTQ 大部分操作是配置完成的，代码较少。那假如我新增加了一张数据表，想通过声明的方式注入回测流程，我该怎么办？NTQ 提供了[数据契约](core/modules/data_contract/README.md)模块：您只需要给您的新数据定义一个唯一的名字（`data_key`），然后定义一个加载逻辑（loader），接下来框架会在回测过程中自动通过名字找到您的 loader 进行数据加载，就可以注入回测了。
- **对回测归因：** 您肯定很想知道您得到当前的结果是什么参数起了作用？它们的作用大不大？是不是决定性的？NTQ 带有机器学习的归因模块，能直接回答您的上述问题。当然，归因只是对于您当前回测的解释，放入不同的股票池或者不同的时间段归因解释可能会不同，不同回测阶段归因解释也可能不同，您需要注意归因解释的范围从而避免过拟合。Quick Start 里有[最短操作路径](#attribution)。
- **适配器：** 扫描出机会后，用 [`adapter`](core/modules/adapter/README.md) 接到您自己的下游（通知、交易软件或其他程序）。框架会提供标准的机会信息，以及回测历史（如果您回测过）。
- **用户界面（UI）：** NTQ 标配了一款 Web UI，可以在您的浏览器里使用。很多结果和操作可以可视化，还可以比较您多次回测的输入参数和输出结果的不同，从而对策略进行针对性微调。
- **命令行入口（CLI）：** 与 UI 类似，NTQ 也提供了一套快捷命令行命令，您可以使用 [`python cli.py`](#cli) 查看说明和所有命令。
- **市场：** 目前 NTQ 仅完整支持中国 A 股，但 [`market_profile`](core/modules/market_profile/README.md) 模块提供了支持其他市场的可能性，作者会逐渐扩充并支持更多的金融市场。

### 请注意

NTQ 本身免费开源，但部分能力依赖您自备资源：

- **数据**：框架提供接入与存储能力，**不含**数据源的付费账号或 token；需在第三方平台注册/购买后自行配置。
- **通知**：短信、邮件、推送等**不在框架内**，用[适配器](core/modules/adapter/README.md)自己接。

更完整的教程见官网 [更多用例](https://new-tea.cn/zh-hans/more-examples)（中文）。许可见文末 [Apache 2.0](LICENSE)（[许可与支持](#license)）。

<a id="quick-start"></a>
## 快速安装 + 运行一个策略

目标：**5 分钟内跑起框架 + 跑通一个演示策略**。

### 前提条件

- 本机需要有 **Python 3.9 或以上**版本。如果您不知道怎么安装，请参考这篇文档：[安装 Python](https://new-tea.cn/zh-hans/install-python)。
- **注意：如果您是开发者**：需要安装 [Node.js](https://nodejs.org/zh-cn)（主要给 UI 用）；数据库建议使用 [MySQL](https://dev.mysql.com/downloads/) 或 [PostgreSQL](https://www.postgresql.org/download/)。（[DuckDB](https://duckdb.org/) 单写模式调试较麻烦）

### 第 1 步：获取代码

任选其一：

- **Git clone**（推荐），任选其一：

```bash
git clone https://github.com/garnet1985/new-tea-quant.git
cd new-tea-quant
```

```bash
git clone https://gitee.com/garnet/new-tea-quant.git
cd new-tea-quant
```

- **下载 ZIP**：在 [GitHub](https://github.com/garnet1985/new-tea-quant) 或 [Gitee](https://gitee.com/garnet/new-tea-quant) 仓库页选择 **Code → Download ZIP**，解压后进入 **`new-tea-quant`** 根目录（与 [`launcher.py`](launcher.py) 同级）。

### 第 2 步：在仓库根目录启动安装向导

在**项目根目录**（能看到 `launcher.py`）打开终端，执行其一：

```bash
python launcher.py
```
Windows PowerShell 可能是：

```bash
python .\launcher.py
```

若系统上 `python` 指向旧版本，可改用：

```bash
python3 launcher.py
```

脚本会：切到仓库根目录、确保虚拟环境、然后**启动 BFF + 前端并打开浏览器**，进入图形化 **Setup 安装向导**（由 BFF setup API 驱动步骤）。

### 第 3 步：在浏览器中按向导完成初始化

按页面提示依次完成即可，基本上都是按照默认方式安装。向导顺序大致是：

1. 安装核心 Python 依赖
2. 初始化 `userspace`
3. 配置数据库（默认 **DuckDB**；开发者可改 MySQL / PostgreSQL，库不存在时程序会尝试新建，与已有库重名会提示）
4. **询问是否导入演示数据**（可跳过；跳过后再自行接入数据源）
5. **询问是否安装机器学习依赖**（归因分析用，可跳过；之后可在「设置 → 安装与维护」补装）
6. 使用统计（允许或暂不分享都会继续）

完成后进入**欢迎页**。再点导航「制定策略」即可。

至此您已经完成了 NTQ 的安装。

### 第 4 步：运行一个 demo

NTQ 自带以下演示资产：

- **数据**：约 **2023-01 ~ 2025-12**、**300 只**股票的三年演示数据，请勿商用。
- **策略**：自带默认 demo 策略，仅供演示，请勿用于实盘。

#### 进入策略页面

在 UI 点击导航「制定策略」，或打开路径 `/strategy-design/`。列表里选一个 demo（例如 **RSI超跌反弹v1 · 基线**），点标题或「进入调试」：

![图 1：导航进入制定策略](docs/images/demo/1.jpg)

![图 2：策略列表](docs/images/demo/2.jpg)

![图 3：策略详情页](docs/images/demo/3.jpg)

策略页面大致由四块组成：

- **策略信息**：顶部全宽区域，展示名称、说明、版本胶囊，以及固定 / 恢复等操作。
- **策略配置**：左侧面板，随回测步骤变化。保存会写回 `settings.py`；回测指纹变了才会开新磁盘 version，便于对比。  
  **注意**：策略**逻辑**不能在 UI 里改，只能在 `userspace/strategies/` 对应目录改代码；UI 仅能调试代码里暴露的参数。（**[v0.5.x](ROADMAP.md)** 将配套 AI 辅助。）
- **执行面板**：当前步骤的执行入口。回测目前分三步（第四步决策者模式计划于 **[v0.5.x](ROADMAP.md)**）：  
  - **枚举**：在历史数据中找出策略机会；  
  - **价格回测**：按 1 股、不计成本，看策略对价格波动的捕获；  
  - **投资组合**：带起始资金、仓位与风控等，更接近真实交易环境。
- **策略报告**：各步骤执行后自动生成；三步各有对应报告。

<a id="attribution"></a>
想看**归因解读**：向导里安装机器学习依赖（或之后在「设置 → 安装与维护」补装），在全局设置打开「归因分析」，再跑回测。报告下方会出现解读。更多说明见官网 [更多用例](https://new-tea.cn/zh-hans/more-examples)。

#### 第一步：机会枚举

结合截图走一遍。枚举跑完后，报告通常分成两部分（后续步骤也类似）：**单股报告**与**全局报告**。

![图 4：枚举后的报告（单股 + 全局）](docs/images/demo/4.jpg)

在表格中点击一只股票，可进入单股 K 线：图上会有 K 线、所用指标，并用标记标出策略抓住的机会（如下图蓝点）：

![图 5：单股 K 线与机会标记](docs/images/demo/5.jpg)

退出单股视图后，在列表下方可看该步骤的整体报告，例如枚举的全局分析（机会在哪些股票上分布、平均持续时长等），用来改进「机会产出」能力：

![图 6：枚举全局报告](docs/images/demo/6.jpg)

#### 第二步：价格回测

价格回测衡量单股价格波动的捕获能力。下图为单股买卖点示意——不强调盈亏，而是直观看入手 / 出手位置，方便调试进出场：

![图 7：价格回测单股 K 线（买卖点）](docs/images/demo/7.jpg)

全局报告里会有买卖价分布、收益等信息；解读时请结合您在配置里设定的目标：

![图 8：价格回测全局报告](docs/images/demo/8.jpg)

#### 第三步：投资组合模拟

投资组合模拟更接近真实交易：可设置仓位、初始资金等，在历史行情上模拟投资，检验策略是否可能真实获利。  
（组合报告目前不支持点击单股下钻，枚举和价格回测可以。）

![图 9：投资组合全局报告](docs/images/demo/9.jpg)

![图 10：收益与回撤等曲线](docs/images/demo/10.jpg)

#### 策略选股：在真实市场中找机会

策略调试完成后，可用 **策略选股** 扫描当前市场机会。从主导航进入「策略选股」即可。

扫描使用策略目录里当前的 `settings.py`（工作台 Persist / Run 会写回该文件）。没有单独的「发布策略」步骤。

要扫描「真实」市场机会，通常还需要：

- **足够新的数据**（现阶段 NTQ 不内置行情源，需自行接入数据源，见 [data_source 模块](core/modules/data_source/README.md)）
- **已启用、完整可用的策略**

进入「策略选股」后，可选用 **严格模式**（数据不够新则不执行），选中策略并点击「开始扫描」。结束后页面会列出策略筛出的当前机会：

![图 11：策略选股 / 扫描](docs/images/demo/11.jpg)

若只想看演示：选择 **「扫描演示」** 模式再扫。应用会假定「今天」是您本地数据最晚交易日的下一天，再按该假想时点跑扫描。

以上是一个简单的策略运行与选股示例；NTQ 还有更多功能等待您继续探索。

<a id="data"></a>
## 数据说明
 
1. 如果您想**获取更多（约 3 年，全 A 股市场）演示数据包**：用于更完整的策略验证/回测，请先[注册并登录会员页面](https://new-tea.cn/zh-hans/user/)下载，移走 [`initialization/data/`](initialization/data/) 里原有 zip 后只放入 **1 个** zip，再执行 `python cli.py id`（强制全量重导加 `-f`，见 [常用命令](#cli)）。可另配库名以并存 demo 与全量数据（安装后见 `userspace/system/config/database/`）。  
2. **自有数据源**：也可自行接入（例如 [Tushare](https://tushare.pro)），详见 [core/modules/data_source/README.md](core/modules/data_source/README.md)。
3. 演示数据与 demo 策略仅供学习研究，请勿用于实盘或商用。


## 一些声明

当前版本仍是非正式 **v0.x**：现阶段不能保证任何 API 的稳定性；进入 1.0 后 API 将基本稳定。（正式版之前，所有 API 最多为 beta。）详见 [CHANGELOG.md](CHANGELOG.md)。

<a id="cli"></a>
## 常用命令（`cli.py`）

分层回测与扫描（完整列表：`python cli.py -h`）：

```bash
python cli.py se --strategy rsi_v1   # 机会枚举
python cli.py sp --strategy rsi_v1   # 价格层
python cli.py so --strategy rsi_v1   # 资金层
python cli.py s  --strategy rsi_v1   # 三层一次跑完
python cli.py sa --strategy rsi_v1   # 展示该 step 最近一次归因（可加 --version）
python cli.py c  --strategy rsi_v1   # 全市场扫描
python cli.py t  --scenario demo/market_cap_tier   # 特征标签
```

建议显式指定 `--strategy`；需要强制重算时加 `-f`。演示 Tag 场景安装后见 `userspace/extensions/tags/demo/market_cap_tier/`。

---

## 几个典型用法（举例）

| 您想做的事 | 建议路径 |
|------------|----------|
| **验证「这个信号有没有」** | Web **制定策略**（见 [Quick Start 第 4 步](#quick-start)）→ 选 demo → **枚举机会** → 看触发次数与分布 |
| **验证「触发后单笔能不能赚」** | 枚举完成后 → **价格回测** → 报告里点单股看买卖点位 |
| **验证「有限资金下还能不能活」** | 价格层 OK 后 → **投资组合模拟** → 看组合曲线与持仓 |
| **每月在全 A 选低价 / Top N** | 参考安装后的 `userspace/strategies/demo/cross_sectional/low_price/`，用 **`slice_based`** 横截面模式 |
| **多个策略共用同一因子** | 先跑 **[Tag](core/modules/tag/README.md)**（[`cli.py t`](#cli)），策略 settings 里引用 Tag 数据 |
| **最新行情筛机会** | 数据更新后 [`cli.py c`](#cli) 或 Web 扫描（通知需 [Adapter](core/modules/adapter/README.md) 自接） |

---

<a id="upgrade"></a>
## 升级

1. 拉取最新 **master**，**保留** `userspace/`（安装后生成，升级时不要覆盖），其余覆盖。  
2. 日常打开 UI：`python launcher.py`（会按需补 UI 依赖）。只更新 CLI / Python 依赖：[`python install.py`](install.py)。升级已安装的应用：`python cli.py u`。若[发布说明](CHANGELOG.md)要求重导数据，见上文 [数据说明](#data)。

---

<a id="license"></a>
## 许可与支持

- **许可证**：[Apache 2.0](LICENSE) · **变更**：[CHANGELOG.md](CHANGELOG.md)
- **反馈 / 贡献**：[SUPPORT.md](SUPPORT.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [SECURITY.md](SECURITY.md)
- **官网**：[new-tea.cn](https://new-tea.cn) · **教程**：[更多用例](https://new-tea.cn/zh-hans/more-examples)

**免责声明**：仅供学习与研究，不构成投资建议；回测结果不代表未来表现。

<details>
<summary>开发者附录（分支、devcli、测试、文档索引）</summary>

**仓库要点：** [`core/`](core/) 框架 · `userspace/` 策略与配置（安装后生成，升级保留）· 演示策略在安装后的 `userspace/strategies/demo/` · [docs/README.md](docs/README.md)

**分支：** `master` 发布；从 `dev` 拉 `feature/*` / `bugfix/*`；`hotfix/*` 仅从 rc 拉。勿直接向 `master` 提 PR。

**开发：** `python devcli.py -h`（`ui` 开发 UI · `uk` 释放端口 · `csc` 清缓存）· Docker：[docs/docker.md](docs/docker.md)

**测试 / 依赖：**

```bash
./venv/bin/python -m pytest   # 需先 pip install -r requirements-dev.txt（含 Flask 等）
python3 -m piptools compile --output-file requirements.txt requirements.in
```

依赖清单：[requirements-dev.txt](requirements-dev.txt) · [requirements.in](requirements.in)

</details>

---

## Fun time：AI 如何评价 NTQ？

> 以下为第三方 AI 在阅读 NTQ 一些核心文件与文档后的评价，仅供娱乐，附**完整回复截图**。**非商业广告**，不代表任何 AI 官方立场；AI 可能过度乐观，请结合本仓库自行判断。  
> 也欢迎用您自己的 AI 评价本工程；请务必先让 AI 阅读核心代码后再评价，否则容易出现严重脱离实际的幻觉。

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
