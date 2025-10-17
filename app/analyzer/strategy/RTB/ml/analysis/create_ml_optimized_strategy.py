#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于机器学习发现创建优化的RTB策略
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from app.analyzer.strategy.RTB.RTB import ReverseTrendBet
from app.analyzer.strategy.RTB.settings import settings
import json

def create_ml_optimized_strategy():
    """基于ML分析结果创建优化的RTB策略"""
    
    print("🚀 基于机器学习分析创建优化的RTB策略")
    print("="*50)
    
    # ML分析的关键发现
    ml_findings = {
        "反直觉发现": {
            "MA60斜率": "成功案例MA60斜率向下(-0.052)，失败案例向上(0.246)",
            "持续时间": "成功案例平均22.6周，失败案例44.5周",
            "结论": "短期收敛+MA60微跌+MA20向上的组合效果最好"
        },
        "最优特征组合": {
            "MA60斜率": "微跌到微涨 (-0.1 到 0.1)",
            "MA20斜率": "明显向上 (> 0.2)", 
            "收敛持续时间": "短期 (2-4个月)",
            "收敛程度": "充分收敛 (< 0.07)",
            "价格位置": "相对低位"
        }
    }
    
    print("📊 ML分析关键发现:")
    for category, findings in ml_findings.items():
        print(f"\n{category}:")
        for key, value in findings.items():
            print(f"  {key}: {value}")
    
    # 基于ML发现设计新的策略条件
    print("\n🎯 设计ML优化策略条件:")
    print("-"*30)
    
    # 新的策略逻辑
    new_strategy_logic = """
    ML优化RTB策略逻辑:
    
    1. 寻找短期收敛区间 (2-4个月，不是长期整理)
    2. MA60微跌到微涨 (-0.1 到 0.1) - 长期趋势调整结束
    3. MA20明显向上 (> 0.2) - 短期趋势转好
    4. 均线充分收敛 (< 0.07) - 技术面整理充分
    5. 价格相对低位 - 安全边际
    
    核心思想: 在长期上涨趋势中的短期调整结束后买入
    """
    
    print(new_strategy_logic)
    
    # 创建新的策略参数
    ml_optimized_conditions = {
        "ma_convergence": "< 0.07",  # 充分收敛
        "ma60_slope": "-0.1 < x < 0.1",  # 微跌到微涨
        "ma20_slope": "> 0.2",  # 明显向上
        "duration_weeks": "2 < x < 16",  # 短期收敛(2-4个月)
        "position": "< 0.6",  # 相对低位
        "close_to_ma20": "< 5%",  # 接近MA20
    }
    
    print("\n📋 ML优化策略参数:")
    for param, condition in ml_optimized_conditions.items():
        print(f"  {param}: {condition}")
    
    # 创建策略实现建议
    strategy_implementation = """
    # ML优化RTB策略实现建议:
    
    def _calculate_ml_features(self, stock_id: str, data: Dict[str, Any]) -> Dict[str, float]:
        \"\"\"计算ML优化特征\"\"\"
        
        # 使用mark_period找到收敛区间
        convergence_periods = self.mark_convergence_periods(
            records=data['klines']['weekly'],
            convergence_threshold=0.07,
            min_period_length=2
        )
        
        if not convergence_periods:
            return None
            
        # 取最新的收敛区间
        latest_period = convergence_periods[-1]
        
        # 计算特征
        features = {
            'convergence_ratio': latest_period['convergence_ratio'],
            'duration_weeks': latest_period['duration'],
            'ma60_slope': latest_period['ma60_slope'],
            'ma20_slope': latest_period['ma20_slope'],
            'position': latest_period['position'],
            'close_to_ma20': latest_period['close_to_ma20'],
        }
        
        return features
    
    def _check_ml_conditions(self, features: Dict[str, float]) -> bool:
        \"\"\"检查ML优化条件\"\"\"
        
        conditions = [
            features['convergence_ratio'] < 0.07,  # 充分收敛
            -0.1 < features['ma60_slope'] < 0.1,   # MA60微跌到微涨
            features['ma20_slope'] > 0.2,          # MA20明显向上
            2 < features['duration_weeks'] < 16,   # 短期收敛
            features['position'] < 0.6,            # 相对低位
            features['close_to_ma20'] < 5,         # 接近MA20
        ]
        
        return all(conditions)
    """
    
    print("\n💻 策略实现代码:")
    print(strategy_implementation)
    
    # 保存策略配置
    ml_strategy_config = {
        "strategy_name": "RTB_ML_Optimized",
        "version": "V10_ML",
        "description": "基于机器学习分析优化的RTB策略",
        "ml_findings": ml_findings,
        "optimized_conditions": ml_optimized_conditions,
        "expected_improvement": {
            "win_rate": "从38.7%提升到50%+",
            "logic": "短期收敛+长期微调+短期转好",
            "key_insight": "寻找长期上涨趋势中的短期调整结束点"
        }
    }
    
    # 保存到文件
    config_file = '/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/ml_strategy_config.json'
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(ml_strategy_config, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 策略配置已保存到: {config_file}")
    
    return ml_strategy_config

if __name__ == "__main__":
    create_ml_optimized_strategy()
