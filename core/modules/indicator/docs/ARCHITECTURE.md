# Indicator 架构文档

**版本：** `0.2.0`

---

## 模块介绍

`modules.indicator` 仅暴露 **`IndicatorService`**：类方法集合，**延迟导入** **`pandas_ta_classic`**，将业务侧 **K 线字典列表** 转为 **OHLCV DataFrame**，调用 TA 库函数后把结果序列化回 **Python 原生列表**，供策略与标签在无 DataFrame 的代码路径上使用。

---

## 模块目标

- **不 fork** TA 实现，保持与 **pandas-ta-classic** 行为一致。
- **输入统一**为 `List[Dict]`（与 DataManager K 线行结构接近）。
- **失败可观测**：异常记日志并返回 **`None`**（不抛给调用方，见实现）。

---

## 工作拆分

- **`indicator_service.py`**：`_init_ta`、`_klines_to_dataframe`、`_result_to_list`、`calculate`、便捷封装、`list_indicators`、`get_indicator_help`。

---

## 依赖说明

见 `module_info.yaml`（无 NTQ 模块依赖）；运行需 **pandas**、**pandas-ta-classic**。

---

## 模块职责与边界

**职责（In scope）**

- 单股票（或单序列）上的指标数值计算与格式转换。

**边界（Out of scope）**

- 不负责拉 K 线、不负责持久化指标序列、不负责多标的批处理调度（由调用方循环或上层模块负责）。

---

## 架构 / 流程图

```mermaid
flowchart LR
  K[List Dict klines]
  DF[DataFrame OHLCV]
  TA[pandas-ta-classic]
  OUT[List or Dict lists]
  K --> DF
  DF --> TA
  TA --> OUT
```

---

## 相关文档

- [DESIGN.md](DESIGN.md)
- [API.md](API.md)
- [DECISIONS.md](DECISIONS.md)
- [可用指标表](../AVAILABLE_INDICATORS.md)
