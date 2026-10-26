# modules.indicator — 决定

**版本：** `0.2.0`

本文件列出本模块的关键选型回顾。每条决定独立编号。
相关：[ARCHITECTURE.md](./ARCHITECTURE.md) · [DESIGN.md](./DESIGN.md)

---

## DEC-01：决策 1：代理 pandas-ta-classic，不自研公式

**背景（Context）**  
指标数量多、维护成本高。

**决策（Decision）**  
以 **`pandas-ta-classic`** 为唯一实现源，**`Indicator`** 只做转换与调用。

**理由（Rationale）**  
与社区实现一致，减少数值偏差争议。

**影响（Consequences）**  
库版本升级可能带来列名或默认参数变化，需在升级后回归测试。

---

---

## DEC-02：决策 2：静态服务类、无缓存

**背景（Context）**  
不同调用方对窗口与参数组合需求差异大。

**决策（Decision）**  
**不**在模块内缓存计算结果；每次调用重新算。

**理由（Rationale）**  
避免错误共享与内存占用不可控；需要缓存时在 Strategy/Tag 层做。

**影响（Consequences）**  
高频重复计算需调用方优化。

---

---

## DEC-03：决策 3：错误返回 None

**背景（Context）**  
指标失败不应拖垮整条扫描链路。

**决策（Decision）**  
捕获异常、打日志，返回 **`None`**。

**理由（Rationale）**  
与现有调用方习惯一致（见 `calculate` 实现）。

**影响（Consequences）**  
调用方必须判空。

---

---

## DEC-04：决策 4：RSI 仅依赖 close

**背景（Context）**  
部分数据只有收盘价序列。

**决策（Decision）**  
**`rsi`** 单独路径，不强制完整 OHLC DataFrame。

**理由（Rationale）**  
提高可用性，避免无意义的 `high/low` 依赖。

**影响（Consequences）**  
与 **`calculate('rsi', ...)`** 行为需保持 mentally一致（均基于 close）。

---

---

## DEC-05：决策 5：进程内延迟加载 + verify_series 补丁

**背景（Context）**  
首次导入 TA 库成本高；默认不足长度告警在批量扫描时噪音大。

**决策（Decision）**  
`_init_ta` 短路缓存模块对象；加载时打一次性中文 DEBUG monkeypatch。

**理由（Rationale）**  
预热可控、日志可读，且不改变跳过语义。

**影响（Consequences）**  
依赖 pandas-ta 内部 `utils._core` 路径；库大改版时需回归补丁。


## 相关文档

- [架构](./ARCHITECTURE.md)
- [设计思路](./DESIGN.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
