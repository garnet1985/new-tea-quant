# Analyzer Module - 分析器模块指南

## 概述

分析器模块是Stocks-Py系统的核心，负责股票数据分析、策略执行和信号生成。本指南将详细介绍如何开发和使用分析器，以及如何添加自定义策略。

## 模块架构

```
analyzer/
├── __init__.py              # 模块初始化
├── analyzer.py              # 主分析器类
├── analyzer_service.py      # 分析器服务
├── analyzer_settings.py     # 分析器配置
├── libs/                    # 分析库
│   ├── __init__.py
│   └── base_strategy.py     # 策略基类
├── strategy/                # 策略实现
│   ├── __init__.py
│   ├── historicLow/         # 历史低点策略
│   └── lowPrice/            # 低价策略
└── README.md                # 本文档
```

## 核心组件

### 1. 主分析器 (`analyzer.py`)

主分析器负责协调各个策略的执行，提供统一的接口。

**主要功能:**
- 策略管理和调度
- 数据预处理和后处理
- 结果聚合和输出
- 错误处理和日志记录

**使用方法:**
```python
from app.analyzer import Analyzer

# 创建分析器实例
analyzer = Analyzer()

# 分析单个股票
result = analyzer.analyze_stock('000001.SZ')

# 分析多个股票
results = analyzer.analyze_stocks(['000001.SZ', '000002.SZ'])

# 运行所有策略
all_results = analyzer.run_all_strategies()
```

### 2. 分析器服务 (`analyzer_service.py`)

分析器服务提供后台服务功能，支持定时分析和监控。

**主要功能:**
- 定时任务调度
- 实时监控
- 结果通知
- 性能监控

**使用方法:**
```python
from app.analyzer.analyzer_service import AnalyzerService

# 创建服务实例
service = AnalyzerService()

# 启动监控服务
service.start_monitoring()

# 添加定时任务
service.add_scheduled_task('daily_analysis', '0 9 * * *', daily_analysis_job)

# 停止服务
service.stop()
```

### 3. 策略基类 (`libs/base_strategy.py`)

所有策略都应该继承自策略基类，确保接口一致性和功能完整性。

**基类特性:**
- 统一的策略接口
- 通用的数据处理方法
- 内置的性能监控
- 标准化的结果格式

## 添加自定义策略

### 步骤1: 创建策略目录结构

```bash
# 在 strategy 目录下创建新策略
mkdir -p app/analyzer/strategy/myCustomStrategy
cd app/analyzer/strategy/myCustomStrategy

# 创建必要的文件
touch __init__.py
touch strategy.py
touch strategy_service.py
touch strategy_settings.py
touch strategy_simulator.py
mkdir tables
touch tables/__init__.py
```

### 步骤2: 实现策略逻辑

```python
# strategy.py
from app.analyzer.libs.base_strategy import BaseStrategy
from app.analyzer.strategy.myCustomStrategy.strategy_settings import MyStrategySettings

class MyCustomStrategy(BaseStrategy):
    """我的自定义策略"""
    
    def __init__(self):
        super().__init__()
        self.settings = MyStrategySettings()
        self.strategy_name = "MyCustomStrategy"
        self.description = "基于技术指标的自定义策略"
    
    def analyze(self, stock_data, **kwargs):
        """分析股票数据并生成信号"""
        try:
            # 数据预处理
            processed_data = self._preprocess_data(stock_data)
            
            # 计算技术指标
            indicators = self._calculate_indicators(processed_data)
            
            # 生成交易信号
            signal = self._generate_signal(processed_data, indicators)
            
            # 计算信号强度
            strength = self._calculate_signal_strength(signal, indicators)
            
            # 构建结果
            result = {
                'strategy_name': self.strategy_name,
                'ts_code': stock_data.get('ts_code'),
                'signal': signal,
                'strength': strength,
                'indicators': indicators,
                'timestamp': self._get_current_timestamp(),
                'confidence': self._calculate_confidence(signal, strength)
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"策略分析失败: {e}")
            return self._create_error_result(stock_data.get('ts_code'), str(e))
    
    def _preprocess_data(self, stock_data):
        """数据预处理"""
        processed = stock_data.copy()
        
        # 示例：计算收益率
        if 'close' in processed and len(processed['close']) > 1:
            processed['returns'] = self._calculate_returns(processed['close'])
        
        return processed
    
    def _calculate_indicators(self, data):
        """计算技术指标"""
        indicators = {}
        
        if 'close' in data and len(data['close']) > 0:
            # 计算移动平均线
            indicators['ma5'] = self._calculate_ma(data['close'], 5)
            indicators['ma20'] = self._calculate_ma(data['close'], 20)
            
            # 计算RSI
            indicators['rsi'] = self._calculate_rsi(data['close'], 14)
        
        return indicators
    
    def _generate_signal(self, data, indicators):
        """生成交易信号"""
        if not indicators:
            return 'HOLD'
        
        # 示例信号逻辑：金叉死叉
        ma5 = indicators.get('ma5', [])
        ma20 = indicators.get('ma20', [])
        
        if len(ma5) >= 2 and len(ma20) >= 2:
            # 金叉：MA5上穿MA20
            if ma5[-1] > ma20[-1] and ma5[-2] <= ma20[-2]:
                return 'BUY'
            # 死叉：MA5下穿MA20
            elif ma5[-1] < ma20[-1] and ma5[-2] >= ma20[-2]:
                return 'SELL'
        
        return 'HOLD'
    
    def _calculate_signal_strength(self, signal, indicators):
        """计算信号强度 (0.0-1.0)"""
        if signal == 'HOLD':
            return 0.0
        
        strength = 0.5  # 基础强度
        
        # 根据指标值调整强度
        if 'rsi' in indicators and len(indicators['rsi']) > 0:
            rsi = indicators['rsi'][-1]
            if signal == 'BUY' and rsi < 30:
                strength += 0.3  # 超卖区域
            elif signal == 'SELL' and rsi > 70:
                strength += 0.3  # 超买区域
        
        return min(strength, 1.0)
    
    def _calculate_confidence(self, signal, strength):
        """计算信号置信度"""
        if signal == 'HOLD':
            return 0.0
        
        confidence = strength * 0.8
        historical_accuracy = self._get_historical_accuracy()
        confidence += historical_accuracy * 0.2
        
        return min(confidence, 1.0)
    
    def _calculate_returns(self, prices):
        """计算收益率"""
        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)
        return returns
    
    def _calculate_ma(self, prices, period):
        """计算移动平均线"""
        if len(prices) < period:
            return []
        
        ma_values = []
        for i in range(period - 1, len(prices)):
            ma = sum(prices[i-period+1:i+1]) / period
            ma_values.append(ma)
        
        return ma_values
    
    def _calculate_rsi(self, prices, period):
        """计算RSI指标"""
        if len(prices) < period + 1:
            return []
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        rsi_values = []
        for i in range(period, len(gains) + 1):
            avg_gain = sum(gains[i-period:i]) / period
            avg_loss = sum(losses[i-period:i]) / period
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            rsi_values.append(rsi)
        
        return rsi_values
    
    def _get_historical_accuracy(self):
        """获取历史准确性"""
        return 0.7
    
    def _get_current_timestamp(self):
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
```

### 步骤3: 创建策略服务

```python
# strategy_service.py
from app.analyzer.strategy.myCustomStrategy.strategy import MyCustomStrategy
from app.analyzer.strategy.myCustomStrategy.strategy_settings import MyStrategySettings
from app.data_source import DataSourceManager
import logging

class MyCustomStrategyService:
    """我的自定义策略服务"""
    
    def __init__(self):
        self.strategy = MyCustomStrategy()
        self.settings = MyStrategySettings()
        self.data_source = DataSourceManager()
        self.logger = logging.getLogger(__name__)
    
    def run_strategy(self, ts_codes=None):
        """运行策略"""
        try:
            if ts_codes is None:
                ts_codes = self._get_stock_list()
            
            results = []
            for ts_code in ts_codes:
                try:
                    stock_data = self._get_stock_data(ts_code)
                    result = self.strategy.analyze(stock_data)
                    
                    if result and 'error' not in result:
                        results.append(result)
                        self._save_result(result)
                        
                        if self._should_send_notification(result):
                            self._send_notification(result)
                    
                except Exception as e:
                    self.logger.error(f"分析股票 {ts_code} 失败: {e}")
                    continue
            
            return results
            
        except Exception as e:
            self.logger.error(f"策略服务运行失败: {e}")
            raise
    
    def _get_stock_list(self):
        """获取股票列表"""
        return self.settings.get_stock_list()
    
    def _get_stock_data(self, ts_code):
        """获取股票数据"""
        data = self.data_source.get_stock_data(ts_code, 'daily')
        data['ts_code'] = ts_code
        return data
    
    def _save_result(self, result):
        """保存结果到数据库"""
        try:
            pass
        except Exception as e:
            self.logger.error(f"保存结果失败: {e}")
    
    def _should_send_notification(self, result):
        """判断是否需要发送通知"""
        return (result.get('signal') in ['BUY', 'SELL'] and 
                result.get('strength', 0) > self.settings.notification_threshold)
    
    def _send_notification(self, result):
        """发送通知"""
        try:
            message = self._format_notification_message(result)
            self.logger.info(f"发送通知: {message}")
        except Exception as e:
            self.logger.error(f"发送通知失败: {e}")
    
    def _format_notification_message(self, result):
        """格式化通知消息"""
        return f"""
策略信号通知
股票代码: {result.get('ts_code')}
信号类型: {result.get('signal')}
信号强度: {result.get('strength', 0):.2f}
置信度: {result.get('confidence', 0):.2f}
时间: {result.get('timestamp')}
        """.strip()
```

### 步骤4: 创建策略配置

```python
# strategy_settings.py
import os
from typing import List, Dict, Any

class MyStrategySettings:
    """我的自定义策略配置"""
    
    def __init__(self):
        self.load_settings()
    
    def load_settings(self):
        """加载配置"""
        self.enabled = True
        self.strategy_name = "MyCustomStrategy"
        self.description = "基于技术指标的自定义策略"
        
        self.ma_short_period = 5
        self.ma_long_period = 20
        self.rsi_period = 14
        
        self.buy_threshold = 0.6
        self.sell_threshold = 0.4
        self.notification_threshold = 0.7
        
        self.stock_pool = self._get_stock_pool()
        
        self.execution_interval = 300
        self.max_concurrent = 10
        self.retry_count = 3
        
        self._load_from_env()
    
    def _load_from_env(self):
        """从环境变量加载配置"""
        if os.getenv('MY_STRATEGY_ENABLED'):
            self.enabled = os.getenv('MY_STRATEGY_ENABLED').lower() == 'true'
        
        if os.getenv('MY_STRATEGY_MA_SHORT'):
            self.ma_short_period = int(os.getenv('MY_STRATEGY_MA_SHORT'))
        
        if os.getenv('MY_STRATEGY_MA_LONG'):
            self.ma_long_period = int(os.getenv('MY_STRATEGY_MA_LONG'))
    
    def _get_stock_pool(self) -> List[str]:
        """获取股票池"""
        return [
            '000001.SZ',  # 平安银行
            '000002.SZ',  # 万科A
            '000858.SZ',  # 五粮液
            '002415.SZ',  # 海康威视
            '600036.SH',  # 招商银行
            '600519.SH',  # 贵州茅台
        ]
    
    def get_stock_list(self) -> List[str]:
        """获取股票列表"""
        return self.stock_pool
    
    def is_enabled(self) -> bool:
        """检查策略是否启用"""
        return self.enabled
    
    def get_parameters(self) -> Dict[str, Any]:
        """获取策略参数"""
        return {
            'ma_short_period': self.ma_short_period,
            'ma_long_period': self.ma_long_period,
            'rsi_period': self.rsi_period,
            'buy_threshold': self.buy_threshold,
            'sell_threshold': self.sell_threshold,
            'notification_threshold': self.notification_threshold
        }
```

### 步骤5: 注册策略到分析器

```python
# 在 analyzer.py 中添加策略注册
from app.analyzer.strategy.myCustomStrategy.strategy import MyCustomStrategy

class Analyzer:
    def __init__(self):
        # ... 现有代码 ...
        
        # 注册新策略
        self.register_strategy(MyCustomStrategy())
    
    def register_strategy(self, strategy):
        """注册新策略"""
        if strategy.strategy_name not in self.strategies:
            self.strategies[strategy.strategy_name] = strategy
            self.logger.info(f"策略 {strategy.strategy_name} 注册成功")
        else:
            self.logger.warning(f"策略 {strategy.strategy_name} 已存在，跳过注册")
```

## 策略测试

### 1. 单元测试

```python
# tests/test_my_custom_strategy.py
import unittest
from unittest.mock import Mock, patch
from app.analyzer.strategy.myCustomStrategy.strategy import MyCustomStrategy

class TestMyCustomStrategy(unittest.TestCase):
    
    def setUp(self):
        self.strategy = MyCustomStrategy()
        
        self.mock_stock_data = {
            'ts_code': '000001.SZ',
            'close': [10.0, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9,
                     11.0, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.9, 12.0],
            'volume': [1000000] * 21
        }
    
    def test_strategy_initialization(self):
        """测试策略初始化"""
        self.assertEqual(self.strategy.strategy_name, "MyCustomStrategy")
        self.assertEqual(self.strategy.description, "基于技术指标的自定义策略")
    
    def test_data_preprocessing(self):
        """测试数据预处理"""
        processed_data = self.strategy._preprocess_data(self.mock_stock_data)
        
        self.assertIn('returns', processed_data)
        self.assertEqual(len(processed_data['returns']), 20)
    
    def test_indicator_calculation(self):
        """测试指标计算"""
        processed_data = self.strategy._preprocess_data(self.mock_stock_data)
        indicators = self.strategy._calculate_indicators(processed_data)
        
        self.assertIn('ma5', indicators)
        self.assertIn('ma20', indicators)
        self.assertIn('rsi', indicators)
    
    def test_signal_generation(self):
        """测试信号生成"""
        processed_data = self.strategy._preprocess_data(self.mock_stock_data)
        indicators = self.strategy._calculate_indicators(processed_data)
        
        signal = self.strategy._generate_signal(processed_data, indicators)
        
        self.assertIn(signal, ['BUY', 'SELL', 'HOLD'])
    
    def test_full_analysis(self):
        """测试完整分析流程"""
        result = self.strategy.analyze(self.mock_stock_data)
        
        self.assertIsNotNone(result)
        self.assertIn('strategy_name', result)
        self.assertIn('ts_code', result)
        self.assertIn('signal', result)
        self.assertIn('strength', result)
        self.assertIn('confidence', result)
```

## 最佳实践

### 1. 策略设计原则

- **单一职责**: 每个策略只负责一个特定的分析逻辑
- **可配置性**: 策略参数应该可配置，支持不同市场环境
- **可测试性**: 策略逻辑应该易于测试和验证
- **可扩展性**: 策略应该支持参数调整和功能扩展

### 2. 性能考虑

- **数据缓存**: 缓存计算结果，避免重复计算
- **批量处理**: 批量处理数据，提高效率
- **异步执行**: 使用异步处理，提高响应性
- **资源管理**: 合理管理内存和CPU资源

### 3. 错误处理

- **异常捕获**: 捕获并处理所有可能的异常
- **日志记录**: 记录详细的错误信息和上下文
- **降级策略**: 提供降级策略，确保系统稳定
- **监控告警**: 设置监控告警，及时发现问题

## 常见问题和解决方案

### 1. 策略执行失败

**问题**: 策略执行时出现错误
**解决**: 检查数据格式、参数配置和异常处理

### 2. 性能问题

**问题**: 策略执行速度慢
**解决**: 优化算法、使用缓存、并行处理

### 3. 信号质量差

**问题**: 策略生成的信号质量不高
**解决**: 优化参数、增加过滤条件、回测验证

## 联系支持

如有问题或建议，请查看：
- [utils/db/README.md](../../../utils/db/README.md) - 数据库模块文档
- [app/analyzer/strategy/README.md](strategy/README.md) - 策略模块文档
- 代码注释和错误日志
- 项目Issues和Discussions
