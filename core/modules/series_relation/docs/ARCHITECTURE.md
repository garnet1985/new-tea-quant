# SeriesRelation — 架构

**模块：** `modules.series_relation` · **版本：** `0.1.0`

## 职责与边界（结论）

把 2 到 `MAX_SERIES` 条序列放在同一时间轴上，输出**描述性**的两两关系：

- 相关强度与方向（Pearson / Spearman）
- 滞后天数与滞后处的相关（`best_lag_days` / `best_lag_corr` / `lead`）
- 缩放关系（`beta` / `alpha` / `scale_r2`）
- 关系的滚动稳定性（`rolling`）

**不做：** 因果推断、因子有效性判断、买卖建议。相关不等于因果，滞后不等于领先。

## 模块结构图

| 路径 | 层 | 职责 |
|------|----|------|
| `series_relation.py` | 对外 | Facade：`list_infos` / `validate` / `run` |
| `contracts.py` | 契约 | `DiscoveredRelation` 等公开类型 |
| `core/settings.py` | 配置 | 字段校验：`entity`、`max_series`、`transform`、`rolling` |
| `core/discovery.py` | 发现 | 从 data_source 目录与 strategy 产物寻找候选序列 |
| `core/pipeline/load_series.py` | 加载 | 按 `data_key` / `field` 取时间序列 |
| `core/pipeline/load_strategy_sim.py` | 加载 | 读 strategy 产物的组合净值 / 价格累计 |
| `core/pipeline/normalize.py` | 归一化 | zscore 或起点归一 |
| `core/pipeline/transform.py` | 变换 | `none` / `returns` / `diff` |
| `core/pipeline/analyze.py` | 分析 | 两两指标、滚动稳定性、平实结论文本 |
| `core/pipeline/cli_report.py` | 输出 | CLI 报告文本 |
| `core/engines/` | 引擎 | 配对计算的具体实现 |
| `__test__/` | 测试 | 模块公开契约 |

依赖方向：`series_relation.py` → `core/`；`core/pipeline/` → `core/engines/`、`core/settings.py`；反向不成立。

## 数据流（若有）

```
settings.yaml
  → discovery（data_source 候选 + strategy 产物）
  → load_series / load_strategy_sim
  → 日期并集对齐
  → normalize（zscore / 起点归一）
  → transform（none / returns / diff）
  → analyze.pairwise_summary
      ├─ 逐对：corr / lag / beta / shape_ok
      └─ 滚动：mean / recent / sign_flips / stability
  → results/<key>/summary.json
                / findings.md
                / series.json
                / meta.json
```

## 依赖（结论）

| 依赖 | 用途 |
|------|------|
| `modules.data_source` | `data_key` 声明与序列读取 |
| `modules.strategy` | 回测产物的净值与价格累计 |
| `infra` 配置 | 输出目录与日历 |

被依赖方：`cli`（`srel` 子命令）、BFF（`/v1/series-relations/*`）、UI（`seriesRelationPage`）。

`userspace/extensions/series_relation/<key>/results/` 下：

| 文件 | 内容 |
|------|------|
| `summary.json` | 设定、系列清单、两两指标与滚动稳定性 |
| `series.json` | 日历并集与各序列归一化点 |
| `findings.md` | 面向人的解释与配对结论 |
| `meta.json` | 跑批信息与指纹 |

- `best_lag_days` 在**归一化水平值**上扫描 ±20 天。水平值自相关强，相关系数曲线接近平坦，峰值位置对噪声敏感；滞后结论只能作参考，不宜单独作为交易依据。改用去趋势收益率的互相关后才能提升可信度。
- 序列有缺口时按并集对齐，各序列只在自身有值的点参与计算；重叠样本不足时 `reliable=False`，指标不应当作结论。
- `relation` 的符号只描述统计方向，与基本面因果无关。

## 相关文档

- [用户指南](./USER_GUIDE.md)
- [公开 API](../API.md)
- [术语表](../glossary.yaml)
- [设计](./DESIGN.md)
- [决策](./DECISIONS.md)
