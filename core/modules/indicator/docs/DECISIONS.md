# Indicator 设计决策

**版本：** `0.2.0`

---

## 决策 1：代理 pandas-ta-classic，不自研公式

**背景（Context）**  
指标数量多、维护成本高。

**决策（Decision）**  
以 **`pandas-ta-classic`** 为唯一实现源，**`IndicatorService`** 只做转换与调用。

**理由（Rationale）**  
与社区实现一致，减少数值偏差争议。

**影响（Consequences）**  
库版本升级可能带来列名或默认参数变化，需在升级后回归测试。

---

## 决策 2：静态服务类、无缓存

**背景（Context）**  
不同调用方对窗口与参数组合需求差异大。

**决策（Decision）**  
**不**在模块内缓存计算结果；每次调用重新算。

**理由（Rationale）**  
避免错误共享与内存占用不可控；需要缓存时在 Strategy/Tag 层做。

**影响（Consequences）**  
高频重复计算需调用方优化。

---

## 决策 3：错误返回 None

**背景（Context）**  
指标失败不应拖垮整条扫描链路。

**决策（Decision）**  
捕获异常、打日志，返回 **`None`**。

**理由（Rationale）**  
与现有调用方习惯一致（见 `calculate` 实现）。

**影响（Consequences）**  
调用方必须判空。

---

## 决策 4：RSI 仅依赖 close

**背景（Context）**  
部分数据只有收盘价序列。

**决策（Decision）**  
**`rsi`** 单独路径，不强制完整 OHLC DataFrame。

**理由（Rationale）**  
提高可用性，避免无意义的 `high/low` 依赖。

**影响（Consequences）**  
与 **`calculate('rsi', ...)`** 行为需保持 mentally一致（均基于 close）。
