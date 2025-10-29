# Stocks-Py - A股量化策略回测框架

## 项目概述

Stocks-Py 是一个专注于A股市场的量化策略回测框架，提供完整的策略开发、回测、分析和优化功能。系统采用插件化策略设计，支持灵活的投资目标管理和自定义结算逻辑。

## 核心特性

- 🎯 **投资目标管理系统**: 灵活的分阶段止盈止损、动态止损、保本止损配置
- 🔌 **插件化策略**: 策略模块独立，包含逻辑、配置、分析和结果
- 📊 **完整回测框架**: 多进程模拟、投资生命周期管理、完整的收益分析
- 🧠 **自定义结算**: 支持策略自定义止盈止损逻辑
- 📈 **多策略支持**: RTB反转策略、HL历史低点、动量策略、均值回归等
- 🗄️ **自动数据管理**: 统一的数据加载接口，支持Tushare、AKShare
- ⚙️ **配置化策略**: 零代码实现复杂止盈止损逻辑

## 系统架构

```
stocks-py/
├── app/                       # 核心应用模块
│   ├── analyzer/             # 策略分析框架
│   │   ├── strategy/         # 策略实现
│   │   │   ├── RTB/          # 反转策略 (ML增强版)
│   │   │   ├── HL/           # 历史低点策略
│   │   │   ├── Momentum/     # 动量策略
│   │   │   ├── MeanReversion/# 均值回归策略
│   │   │   ├── Random/       # 随机策略
│   │   │   └── example/      # 示例策略
│   │   ├── components/       # 核心组件
│   │   │   ├── simulator/    # 模拟器
│   │   │   ├── investment/   # 投资管理
│   │   │   └── base_strategy.py  # 策略基类
│   │   └── analyzer.py       # 分析器入口
│   ├── data_loader/          # 数据加载器
│   ├── data_source/          # 数据源管理
│   │   └── providers/        # 数据提供商
│   │       ├── tushare/      # Tushare API
│   │       └── akshare/      # AKShare API
│   └── conf/                 # 配置管理
├── utils/                     # 通用工具
│   ├── db/                   # 数据库管理
│   ├── worker/               # 多进程/多线程工具
│   └── progress/             # 进度追踪
├── config/                    # 配置文件
├── tools/                     # 辅助工具
├── fed/                       # 前端界面 (React)
├── bff/                       # 后端API (Flask)
└── start.py                   # 应用入口
```

## 快速开始

### 1. 环境要求

- Python 3.9+
- MySQL 5.7+ / MariaDB
- 8GB+ RAM (推荐)

### 2. 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd stocks-py

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置数据库

编辑 `config/app_config.json`:
```json
{
    "database": {
        "host": "localhost",
        "user": "root",
        "password": "your_password",
        "database": "stocks_py",
        "port": 3306
    }
}
```

### 4. 配置数据源

#### Tushare配置
```bash
# 创建token文件
echo "your_tushare_token" > app/data_source/providers/tushare/auth/token.txt
```

### 5. 运行策略回测

```bash
# 运行示例策略
python start.py

# 选择策略（RTB/HL/Momentum等）
# 输入采样数量
# 查看回测结果
```

## 核心概念

### 投资目标管理系统

这是框架的核心特性，允许通过配置实现复杂的止盈止损逻辑：

```python
# settings.py
"goal": {
    "stop_loss": {
        # 止损阶段
        "stages": [
            {"name": "loss20%", "ratio": -0.2, "close_invest": True}
        ],
        # 保本止损（盈利后回调到成本价）
        "break_even": {"name": "break_even", "ratio": 0},
        # 动态止损（从最高点回调）
        "dynamic": {"name": "dynamic", "ratio": -0.1}
    },
    "take_profit": {
        # 止盈阶段
        "stages": [
            {"name": "win10%", "ratio": 0.1, "sell_ratio": 0.2},
            {"name": "win20%", "ratio": 0.2, "sell_ratio": 0.2, "set_stop_loss": "break_even"},
            {"name": "win30%", "ratio": 0.3, "sell_ratio": 0.2},
            {"name": "win40%", "ratio": 0.4, "sell_ratio": 0.2, "set_stop_loss": "dynamic"}
        ]
    }
}
```

**特性**:
- ✅ 分阶段止盈止损
- ✅ 盈利后切换止损策略（保本/动态）
- ✅ 自动仓位管理（sell_ratio）
- ✅ 配置化，零代码

### 插件化策略

每个策略是独立的模块：

```
Momentum/
├── Momentum.py          # 策略逻辑
├── settings.py          # 策略配置
├── README.md            # 策略文档
└── tmp/                 # 回测结果
```

### 自定义结算逻辑

策略可以覆盖默认的结算逻辑：

```python
# Momentum策略示例：周期调仓
@staticmethod
def should_take_profit(...) -> Tuple[bool, Dict]:
    # 自定义止盈逻辑
    if is_last_day_of_period():
        return True, close_all_positions()
    return False, investment
```

## 内置策略

### 1. RTB (Reverse Trend Bet) - 反转策略
**理念**: 识别趋势反转点，买入反转上涨的股票

**核心参数** (基于ML分析):
- 波动率: 2%-15%
- 反转后成交量放大: ≥1.5倍
- 均线收敛度: <5%
- 价格相对均线位置: ±5-8%

**特点**:
- ML增强版本，基于7407个样本训练
- 小盘股偏好（成功率89.1% > 大盘股86.6%）
- 完整的分阶段止盈止损

### 2. HL (HistoricLow) - 历史低点策略
**理念**: 在股票接近历史低点时买入

**特点**:
- 基于3/5/8年历史低点分析
- 动态建仓比例（凯莉公式）
- 完整的统计分析

### 3. Momentum - 动量策略
**理念**: 周期调仓，买入过去L天涨幅最大的股票

**特点**:
- 支持月度/季度/年度调仓
- 动量计算：`(MA_short - MA_long) / MA_long`
- 横截面动量，选择前N%股票

### 4. MeanReversion - 均值回归策略
**理念**: 价格偏离均值时买入，回归均值时卖出

**特点**:
- 基于历史分位数的偏离度计算
- 动态止盈止损

### 5. Random - 随机策略
**理念**: 作为基准策略，随机买入股票

**特点**:
- 5%随机投资概率
- 动态止损（基于20日波动率）

## 策略开发

### 创建新策略

1. **创建策略目录**
```bash
mkdir app/analyzer/strategy/MyStrategy
cd app/analyzer/strategy/MyStrategy
```

2. **实现策略类**
```python
# MyStrategy.py
from app.analyzer.components.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self):
        self.name = "MyStrategy"
        self.key = "MS"
        self.version = "1.0.0"
        super().__init__()
    
    @staticmethod
    def scan_opportunity(stock_info, required_data, settings):
        # 扫描投资机会
        # 返回 Opportunity 或 None
        pass
```

3. **配置策略参数**
```python
# settings.py
settings = {
    "name": "MyStrategy",
    "core": {
        # 策略核心参数
    },
    "simulation": {
        "start_date": "20080101",
        "end_date": "",
        "sampling_amount": 10,  # 采样数量
    },
    "goal": {
        # 止盈止损配置
    }
}
```

### 策略生命周期

```python
# 1. 前置处理
on_before_simulate(stock_list, settings)

# 2. 扫描机会
scan_opportunity(stock_info, required_data, settings)

# 3. 自定义结算（可选）
should_stop_loss(...) / should_take_profit(...)

# 4. 汇总处理
on_summarize_session(base_session_summary, stock_summaries, settings)

# 5. 报告生成
present_extra_session_report(session_summary, settings)
```

## 数据管理

### 统一数据加载

```python
from app.data_loader import DataLoader

data_loader = DataLoader()

# 加载K线数据
klines = data_loader.load_klines(
    stock_id='000001.SZ',
    start_date='20200101',
    end_date='20231231',
    frequency='daily'  # daily/weekly/monthly
)
```

### 数据源

- **Tushare**: 专业金融数据API（主要）
- **AKShare**: 开源金融数据接口（备用）

## 回测结果

### 查看结果

```bash
# 结果保存在策略的tmp目录
cd app/analyzer/strategy/RTB/tmp/

# 最新会话目录
ls -lt | head

# 查看汇总
cat 0_session_summary.json

# 查看股票明细
cat 000001.SZ.json
```

### 结果指标

- 总投资数
- 胜率
- 平均ROI
- 年均收益率
- 平均持仓天数
- ROI分布
- 投资时长分布
- 止盈止损触发统计

## 进阶功能

### 自定义报告

```python
@staticmethod
def present_extra_session_report(session_summary, settings):
    """自定义报告输出"""
    print("\n🎯 自定义报告")
    # 你的报告逻辑
```

### 自动分析

```python
# settings.py
"simulation": {
    "analysis": True  # 自动运行分析
}

# 实现analysis方法
def analysis(self):
    # 分析逻辑
    return analysis_result
```

## 性能优化

- **多进程模拟**: 自动并行化处理多只股票
- **批量数据加载**: 一次性加载所需数据
- **内存优化**: 及时释放不需要的数据
- **进度追踪**: 实时显示处理进度

## 开发指南

### 代码规范
- 遵循PEP 8
- 使用类型注解
- 添加适当的日志
- 最小化注释（只注释必要部分）

### 提交规范
```
feat: 添加新功能
fix: 修复bug
refactor: 代码重构
docs: 更新文档
chore: 构建工具变动
```

## 更新日志

### v3.0.0 (2024-XX-XX)
- 重构策略框架，支持插件化策略
- 新增投资目标管理系统
- 新增自定义结算逻辑支持
- 新增Momentum、MeanReversion策略
- 优化RTB策略（ML增强版）
- 完善文档和示例

### v2.0.0 (2023-XX-XX)
- 从Node.js迁移到Python
- 重构系统架构
- 添加多数据源支持

## 许可证

MIT License

---

**免责声明**: 本项目仅供学习和研究使用，不构成投资建议。投资有风险，入市需谨慎。
