---
title: use strategy workbench 从界面制定策略
aliases:
  - workbench
  - UI
  - strategy-design
  - 制定策略
  - 工作台
  - 界面回测
summary: 从导航「制定策略」选策略、改参数、分步回测；逻辑代码仍在磁盘上改。
---

# 如何从界面制定策略

主路径是 Web：**制定策略**（`/strategy-design`）。CLI 也能跑回测，但日常调参、看图、对比版本以界面为准。

## 前置条件

- 已安装，能打开 UI
- 至少有一个策略目录（安装后的 demo，或你新建的）

界面**不能**从模板点一下就生成新策略。新建用 CLI，或导入别人的策略包。

```bash
python cli.py -n my_rsi_strategy
```

会在 `userspace/strategies/my_rsi_strategy/` 放下 `strategy.py` 和 `settings.py`。把 `meta.key` 从 `empty_strategy` 改成 `my_rsi_strategy`。刷新制定策略列表即可看到。写钩子见 [如何编写策略](write_strategy.md)。MACD / RSI 见 [用技术指标](use_indicators.md)。

## 选策略

1. 导航点 **制定策略**
2. 按归类筛选或按名称搜索
3. 点标题进入（例如 demo 里的 RSI 超跌反弹）
4. 列表也可 **导入策略包** / **导出**

进入后四块：

| 区域 | 做什么 |
| --- | --- |
| 顶栏 | 名称、当前 version 胶囊、固定、打开文件夹、恢复历史配置、导出 |
| 左侧配置 | 改 `settings.py` 里暴露的参数（日期、goal、资金、成交假设等） |
| 执行 | 当前步 **开始模拟** / **重新模拟** |
| 右侧报告 | 该步跑完后的图和表 |

点 **打开文件夹** 去改 `strategy.py`。UI 只调代码里已经暴露的参数，不能在网页里改 `has_opportunity`。

## 四步怎么走

顶栏步骤条：

1. **枚举机会** — 股票池里有没有信号、分布如何
2. **价格回测** — 按 1 股、先看单笔能不能抓住波动
3. **投资模拟** — 带初始资金、仓位、手续费，看账户
4. **决策模拟** — 你自己选谁、买多少；要先完成枚举 **和** 投资模拟

改了核心参数（阈值、数据依赖等）后，回到**枚举**重跑。点开始模拟会把当前编辑器写回 `settings.py` 再跑。指纹变了才开新磁盘 version，方便对比。

第四步是人机回放，不走「开始模拟」那套并行回测。操作细节见 [使用决策者模式](use_decision_maker_mode.md)。

跑完看图见 [如何读回测报告](read_backtest_report.md)。命令行等价命令见 [运行回测](run_backtest.md)。

## 验证

- 当前步状态变成已完成，右侧出现对应报告
- 顶栏 version 胶囊有编号；改白名单字段再跑会换 version
- 磁盘上 `userspace/strategies/{name}/results/simulations/` 出现该 version 目录

## 常见坑

- **逻辑不在 UI 里。** 改选股条件请编辑 `strategy.py`，保存后再回界面重跑枚举。
- **扫描用的是磁盘上当前的 `settings.py`。** 没有单独的「发布」步骤。调完参数再去导航 **策略选股**。
- 历史 version 若提示仅供查阅：环境变了（升级或钩子源码改了），报告仍可看，不能在这个旧目录上继续跑。
- 额度满时新回测会先被拒绝，不会悄悄删结果；可删未固定的旧 version，或到设置 → 数据范围调保留份数。
