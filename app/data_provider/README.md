# Data Provider

数据提供者模块 - 统一管理所有数据源（Tushare、AKShare等）

---

## 🎯 核心特性

- ✅ **统一接口**：BaseProvider统一所有数据源
- ✅ **声明式依赖**：Provider声明依赖，自动协调
- ✅ **API级别限流**：智能处理多API限流
- ✅ **动态挂载**：新增Provider无需修改代码
- ✅ **智能并发**：自适应串行/并行策略
- ✅ **多层灵活性**：自动/半自动/手动三层控制

---

## 📋 快速开始

### 安装

```bash
# 依赖已包含在项目主 requirements.txt 中
cd /Users/garnet/Desktop/stocks-py
source venv/bin/activate
```

### 基本使用

```python
from app.data_provider import DataProviderManager

# 初始化
manager = DataProviderManager(data_manager)
manager.initialize()

# 更新所有数据（自动处理依赖）
await manager.renew_all(end_date='20250101')

# 更新指定数据（自动处理依赖）
await manager.renew_data_type('adj_factor', end_date='20250101')
```

---

## 📊 架构概览

```
DataProviderManager
    ↓
ProviderRegistry + RateLimitRegistry + DataCoordinator
    ↓
TushareProvider | AKShareProvider | ...
```

---

## 📂 目录结构

```
app/data_provider/
├── core/               # 核心组件
├── providers/          # 各个Provider
├── utils/              # 工具类
├── config/             # 配置文件
├── DESIGN.md          # 详细设计文档 ⭐
└── README.md          # 本文件
```

---

## 📖 文档

- **[DESIGN.md](./DESIGN.md)** - 完整设计文档（必读）
  - 架构设计
  - 核心组件
  - 实施计划
  - 使用示例

---

## 🚀 实施状态

| 阶段 | 状态 | 说明 |
|-----|------|------|
| **Phase 1** | ⏳ 待开始 | 核心组件 |
| **Phase 2** | ⏳ 待开始 | 工具迁移 |
| **Phase 3** | ⏳ 待开始 | TushareProvider |
| **Phase 4** | ⏳ 待开始 | AKShareProvider |
| **Phase 5** | ⏳ 待开始 | 集成测试 |

---

## 💡 核心设计思想

### 1. 限流对象是API，不是data_type

```python
# ❌ 错误
rate_limit_by_data_type['stock_kline_all'] = 30  # 最慢的API

# ✅ 正确
rate_limit_by_api['tushare.daily'] = 100
rate_limit_by_api['tushare.weekly'] = 50
rate_limit_by_api['tushare.monthly'] = 30
```

### 2. 独立data_type + 组合语法糖

```python
# 独立
'stock_kline_daily'     # 只更新日线
'stock_kline_weekly'    # 只更新周线
'stock_kline_monthly'   # 只更新月线

# 组合（语法糖）
'stock_kline_all'       # 更新所有周期
```

### 3. 声明式依赖 + 自动协调

```python
# Provider声明
dependencies=[
    Dependency(
        provider='tushare',
        data_types=['stock_kline_daily']
    )
]

# 自动协调
await coordinator.coordinate_update('adj_factor', end_date)
# → 自动检查并更新stock_kline_daily
```

---

## 🤝 贡献指南

### 新增Provider

1. 继承 `BaseProvider`
2. 实现必需方法
3. 注册API限流
4. 挂载到Registry

详见 [DESIGN.md](./DESIGN.md)

---

**维护者：** @garnet  
**最后更新：** 2025-12-05

