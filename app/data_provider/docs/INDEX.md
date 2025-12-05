# 设计文档索引

本目录包含完整的设计讨论过程和决策记录。

---

## 📚 阅读顺序

### 1️⃣ 必读文档

| 文档 | 说明 | 优先级 |
|-----|------|--------|
| **[../DESIGN.md](../DESIGN.md)** | 🌟 最终设计文档（综合所有讨论） | ⭐⭐⭐⭐⭐ |
| **[../README.md](../README.md)** | 快速入门和概览 | ⭐⭐⭐⭐⭐ |

### 2️⃣ 设计过程文档（按讨论顺序）

| # | 文档 | 讨论的核心问题 | 优先级 |
|---|-----|---------------|--------|
| 1 | [ANALYSIS.md](./ANALYSIS.md) | 现有实现分析 - 梳理所有功能和特殊处理 | ⭐⭐⭐⭐ |
| 2 | [DESIGN_REVIEW.md](./DESIGN_REVIEW.md) | 优缺点评审 - 6个缺点和改进方向 | ⭐⭐⭐⭐ |
| 3 | [DESIGN_V2.md](./DESIGN_V2.md) | 初步设计 - BaseProvider + 适配器方案 | ⭐⭐⭐ |
| 4 | [EXAMPLE_ADJ_FACTOR.md](./EXAMPLE_ADJ_FACTOR.md) | 复权因子示例 - 跨Provider依赖场景 | ⭐⭐⭐⭐ |
| 5 | [DATA_TYPES.md](./DATA_TYPES.md) | Data Type机制 - 动态注册和可发现性 | ⭐⭐⭐⭐ |
| 6 | [DISCOVERABILITY.md](./DISCOVERABILITY.md) | 可发现性设计 - 查询API和命令行工具 | ⭐⭐⭐ |
| 7 | [FLEXIBILITY_AND_GRANULARITY.md](./FLEXIBILITY_AND_GRANULARITY.md) | 灵活性和粒度 - 三层控制和多周期设计 | ⭐⭐⭐⭐ |
| 8 | [PERFORMANCE_CONCURRENCY.md](./PERFORMANCE_CONCURRENCY.md) | 性能和并发 - 多线程与限流机制 | ⭐⭐⭐ |
| 9 | [REDESIGN_RATE_LIMIT.md](./REDESIGN_RATE_LIMIT.md) | 限流重新设计 - API级别限流 ⭐ 关键 | ⭐⭐⭐⭐⭐ |

---

## 🎯 核心讨论主题

### 主题1: 架构设计

**相关文档：**
- ANALYSIS.md - 现状分析
- DESIGN_REVIEW.md - 优缺点
- DESIGN_V2.md - 初步方案
- REDESIGN_RATE_LIMIT.md - 最终方案

**核心决策：**
- ❌ 适配器包装Legacy → ✅ 全新架构（app/data_provider/）
- ❌ data_type级别限流 → ✅ API级别限流

---

### 主题2: 限流机制 ⭐ 最关键

**相关文档：**
- REDESIGN_RATE_LIMIT.md（必读）
- PERFORMANCE_CONCURRENCY.md

**核心问题：**
> Q: 如果日线API 100次/分钟，周线50次/分钟，月线30次/分钟，串行运行时限流应该是多少？
> 
> A: 不是30次，而是每个API独立限流！需要智能并发策略处理。

**解决方案：**
1. RateLimitRegistry - API级别限流注册表
2. SmartConcurrentExecutor - 智能并发执行器
3. 自适应策略 - 根据限流速率选择串行/并行

---

### 主题3: 数据类型粒度

**相关文档：**
- DATA_TYPES.md
- FLEXIBILITY_AND_GRANULARITY.md

**核心决策：**
- ✅ 独立data_type: `stock_kline_daily`, `stock_kline_weekly`, `stock_kline_monthly`
- ✅ 组合data_type: `stock_kline_all`（语法糖）
- ✅ 精确依赖：复权因子只依赖`stock_kline_daily`

---

### 主题4: 依赖管理

**相关文档：**
- EXAMPLE_ADJ_FACTOR.md（必读示例）
- DESIGN_REVIEW.md

**核心问题：**
- ❌ 硬编码依赖（`ak.inject_dependency(tu)`）
- ✅ 声明式依赖（在`get_provider_info()`中声明）
- ✅ 自动协调（DataCoordinator递归处理）

---

### 主题5: 灵活性

**相关文档：**
- FLEXIBILITY_AND_GRANULARITY.md

**三层控制：**
1. Level 1: 完全自动（99%场景）
2. Level 2: 半自动（skip_dependency_check等参数）
3. Level 3: 完全手动（Hook/Event机制）

---

### 主题6: 可发现性

**相关文档：**
- DISCOVERABILITY.md
- DATA_TYPES.md

**解决方案：**
- 运行时查询API（`list_all_data_types()`, `get_data_type_info()`）
- 命令行工具（`--list-data-types`, `--info`）
- 自动生成文档
- 交互式探索（Jupyter）

---

## 📊 关键设计对比

| 特性 | 旧架构 | 新架构（最终） | 改进 |
|-----|--------|---------------|------|
| **架构** | 适配器包装Legacy | 全新重写 | ⭐⭐⭐⭐⭐ |
| **限流对象** | data_type级别 | API级别 | ⭐⭐⭐⭐⭐ |
| **多API协调** | 不支持 | 智能并发 | ⭐⭐⭐⭐⭐ |
| **依赖管理** | 硬编码 | 声明式 | ⭐⭐⭐⭐⭐ |
| **数据粒度** | 粗粒度 | 独立+组合 | ⭐⭐⭐⭐ |
| **可发现性** | 无 | 多层次 | ⭐⭐⭐⭐ |
| **灵活性** | 低 | 三层控制 | ⭐⭐⭐⭐ |

---

## 🔑 关键决策记录

### 决策1: 不使用适配器，全新重写

**文档：** REDESIGN_RATE_LIMIT.md

**原因：**
- 彻底解耦，避免历史包袱
- 架构清晰，易于扩展
- 迁移有用组件，保留核心能力

---

### 决策2: API级别限流（不是data_type级别）

**文档：** REDESIGN_RATE_LIMIT.md（⭐ 关键）

**原因：**
- 一个data_type可能调用多个API
- 不同API限流速率不同
- 支持智能并发策略

**示例：**
```python
# ❌ 错误
rate_limit['stock_kline_all'] = 30  # 最慢的API

# ✅ 正确
rate_limit['tushare.daily'] = 100
rate_limit['tushare.weekly'] = 50
rate_limit['tushare.monthly'] = 30
```

---

### 决策3: 独立data_type + 组合语法糖

**文档：** FLEXIBILITY_AND_GRANULARITY.md

**原因：**
- 灵活性：可单独更新任意周期
- 便利性：提供组合语法糖
- 精确依赖：复权因子只依赖日线

---

### 决策4: 自适应并发策略

**文档：** REDESIGN_RATE_LIMIT.md

**原因：**
- 限流速率相近 → 并行执行（快）
- 限流速率差异大 → 串行执行（避免瓶颈）
- 自动选择，无需手动配置

---

## 🚀 实施路线图

详见 [../DESIGN.md](../DESIGN.md) 的"实施计划"部分。

---

## 💡 如何使用本文档集

### 场景1: 快速了解

**阅读：**
1. ../README.md（5分钟）
2. ../DESIGN.md（30分钟）

### 场景2: 深入理解

**阅读：**
1. ANALYSIS.md - 了解现状
2. DESIGN_REVIEW.md - 了解问题
3. REDESIGN_RATE_LIMIT.md - 了解核心设计
4. ../DESIGN.md - 了解最终方案

### 场景3: 实施开发

**阅读：**
1. ../DESIGN.md - 完整设计
2. EXAMPLE_ADJ_FACTOR.md - 实际示例
3. FLEXIBILITY_AND_GRANULARITY.md - 灵活性设计

### 场景4: 新增Provider

**阅读：**
1. ../DESIGN.md - 核心组件
2. REDESIGN_RATE_LIMIT.md - 限流机制
3. DATA_TYPES.md - 数据类型机制

---

## 📝 文档维护

**更新原则：**
- docs/ 目录的文档是历史记录，**不再更新**
- ../DESIGN.md 是**活文档**，持续更新
- 新的设计决策应添加到 DESIGN.md

---

**最后更新：** 2025-12-05  
**维护者：** @garnet

