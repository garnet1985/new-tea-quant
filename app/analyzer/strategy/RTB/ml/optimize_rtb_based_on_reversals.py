#!/usr/bin/env python3
"""
基于重大反转点分析优化RTB策略

根据平安银行重大反转点的特征分析，优化RTB策略参数
"""

import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger
import json


def optimize_rtb_based_on_reversals():
    """基于重大反转点分析优化RTB策略"""
    logger.info("🎯 基于重大反转点分析优化RTB策略")
    
    # 读取重大反转点数据
    csv_path = Path(__file__).parent / "major_reversals_000001_SZ.csv"
    if not csv_path.exists():
        logger.error(f"❌ 文件不存在: {csv_path}")
        return
    
    df = pd.read_csv(csv_path)
    logger.info(f"✅ 成功加载 {len(df)} 个重大反转点")
    
    # 分析反转点特征
    analyze_reversal_features(df)
    
    # 生成优化建议
    generate_optimization_suggestions(df)
    
    # 生成新的RTB参数配置
    generate_optimized_rtb_config(df)


def analyze_reversal_features(df):
    """分析反转点特征"""
    logger.info("\n" + "="*60)
    logger.info("🔍 重大反转点特征深度分析")
    logger.info("="*60)
    
    # 价格位置分析
    logger.info(f"\n📍 价格位置分析:")
    logger.info(f"  平均2年价格位置: {df['price_position_2y'].mean():.3f}")
    logger.info(f"  价格位置中位数: {df['price_position_2y'].median():.3f}")
    logger.info(f"  价格位置25%分位: {df['price_position_2y'].quantile(0.25):.3f}")
    logger.info(f"  价格位置75%分位: {df['price_position_2y'].quantile(0.75):.3f}")
    logger.info(f"  价格位置<0.1的比例: {(df['price_position_2y'] < 0.1).mean()*100:.1f}%")
    logger.info(f"  价格位置<0的比例: {(df['price_position_2y'] < 0).mean()*100:.1f}%")
    
    # 前期跌幅分析
    logger.info(f"\n📉 前期跌幅分析:")
    logger.info(f"  平均前期跌幅: {df['decline_from_peak'].mean()*100:.1f}%")
    logger.info(f"  跌幅中位数: {df['decline_from_peak'].median()*100:.1f}%")
    logger.info(f"  跌幅25%分位: {df['decline_from_peak'].quantile(0.25)*100:.1f}%")
    logger.info(f"  跌幅75%分位: {df['decline_from_peak'].quantile(0.75)*100:.1f}%")
    logger.info(f"  跌幅>50%的比例: {(df['decline_from_peak'] > 0.5).mean()*100:.1f}%")
    
    # 均线收敛分析
    logger.info(f"\n📊 均线收敛分析:")
    logger.info(f"  平均均线收敛: {df['ma_convergence'].mean():.3f}")
    logger.info(f"  收敛中位数: {df['ma_convergence'].median():.3f}")
    logger.info(f"  收敛25%分位: {df['ma_convergence'].quantile(0.25):.3f}")
    logger.info(f"  收敛75%分位: {df['ma_convergence'].quantile(0.75):.3f}")
    logger.info(f"  收敛<0.1的比例: {(df['ma_convergence'] < 0.1).mean()*100:.1f}%")
    
    # RSI分析
    logger.info(f"\n📈 RSI分析:")
    logger.info(f"  平均RSI: {df['rsi'].mean():.1f}")
    logger.info(f"  RSI中位数: {df['rsi'].median():.1f}")
    logger.info(f"  RSI25%分位: {df['rsi'].quantile(0.25):.1f}")
    logger.info(f"  RSI75%分位: {df['rsi'].quantile(0.75):.1f}")
    logger.info(f"  RSI<30的比例: {(df['rsi'] < 30).mean()*100:.1f}%")
    logger.info(f"  RSI<20的比例: {(df['rsi'] < 20).mean()*100:.1f}%")
    
    # 波动性分析
    logger.info(f"\n📊 波动性分析:")
    logger.info(f"  平均波动性: {df['volatility'].mean():.3f}")
    logger.info(f"  波动性中位数: {df['volatility'].median():.3f}")
    logger.info(f"  波动性25%分位: {df['volatility'].quantile(0.25):.3f}")
    logger.info(f"  波动性75%分位: {df['volatility'].quantile(0.75):.3f}")


def generate_optimization_suggestions(df):
    """生成优化建议"""
    logger.info("\n" + "="*60)
    logger.info("💡 RTB策略优化建议")
    logger.info("="*60)
    
    # 基于数据分析的建议
    suggestions = []
    
    # 1. 历史分位数建议
    price_position_75th = df['price_position_2y'].quantile(0.75)
    suggestions.append({
        'parameter': 'historical_percentile',
        'current_value': 0.6,
        'suggested_value': round(price_position_75th, 2),
        'reason': f'基于重大反转点分析，75%的反转点价格位置在{price_position_75th:.2f}以下'
    })
    
    # 2. 均线收敛建议
    ma_convergence_75th = df['ma_convergence'].quantile(0.75)
    suggestions.append({
        'parameter': 'ma_convergence',
        'current_value': 0.25,
        'suggested_value': round(ma_convergence_75th, 2),
        'reason': f'基于重大反转点分析，75%的反转点均线收敛度在{ma_convergence_75th:.2f}以下'
    })
    
    # 3. RSI建议
    rsi_75th = df['rsi'].quantile(0.75)
    suggestions.append({
        'parameter': 'rsi_signal',
        'current_value': 80,
        'suggested_value': round(rsi_75th, 0),
        'reason': f'基于重大反转点分析，75%的反转点RSI在{rsi_75th:.0f}以下'
    })
    
    # 4. 前期跌幅建议（需要新增参数）
    decline_25th = df['decline_from_peak'].quantile(0.25)
    suggestions.append({
        'parameter': 'decline_from_peak_threshold',
        'current_value': 'N/A',
        'suggested_value': round(decline_25th, 2),
        'reason': f'基于重大反转点分析，建议新增前期跌幅参数，25%的反转点跌幅在{decline_25th:.2f}以上'
    })
    
    # 5. 波动性建议
    volatility_75th = df['volatility'].quantile(0.75)
    suggestions.append({
        'parameter': 'volatility_threshold',
        'current_value': 'N/A',
        'suggested_value': round(volatility_75th, 3),
        'reason': f'基于重大反转点分析，建议新增波动性参数，75%的反转点波动性在{volatility_75th:.3f}以下'
    })
    
    # 显示建议
    for suggestion in suggestions:
        logger.info(f"\n🔧 {suggestion['parameter']}:")
        logger.info(f"  当前值: {suggestion['current_value']}")
        logger.info(f"  建议值: {suggestion['suggested_value']}")
        logger.info(f"  理由: {suggestion['reason']}")
    
    return suggestions


def generate_optimized_rtb_config(df):
    """生成优化的RTB配置"""
    logger.info("\n" + "="*60)
    logger.info("⚙️ 生成优化的RTB策略配置")
    logger.info("="*60)
    
    # 基于数据分析计算优化参数
    optimized_config = {
        'strategy_name': 'RTB_V21_ReversalBased',
        'version': 'V21.0',
        'description': '基于重大反转点分析优化的RTB策略',
        'parameters': {
            # 基于重大反转点分析的参数
            'historical_percentile_threshold': round(df['price_position_2y'].quantile(0.75), 2),
            'ma_convergence_threshold': round(df['ma_convergence'].quantile(0.75), 2),
            'rsi_threshold': round(df['rsi'].quantile(0.75), 0),
            'decline_from_peak_threshold': round(df['decline_from_peak'].quantile(0.25), 2),
            'volatility_threshold': round(df['volatility'].quantile(0.75), 3),
            
            # 保持原有的其他参数
            'ma20_slope_min': -0.15,
            'ma60_slope_min': -0.15,
            'volume_trend_min': -0.6,
            'amount_ratio_min': 0.5,
            'price_change_pct_min': -6.0,
            'close_to_ma20_min': -5.0,
            'duration_weeks_max': 20,
            'convergence_ratio_min': 0.06,
            'oscillation_position_threshold': 0.7,
            'volume_confirmation_min': 0.5,
        },
        'statistics': {
            'based_on_reversals': len(df),
            'avg_reversal_gain': round(df['reversal_gain'].mean() * 100, 1),
            'max_reversal_gain': round(df['reversal_gain'].max() * 100, 1),
            'avg_duration_weeks': round(df['reversal_duration'].mean(), 1),
        }
    }
    
    # 保存配置
    config_path = Path(__file__).parent / "rtb_v21_reversal_based_config.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(optimized_config, f, ensure_ascii=False, indent=2)
    
    logger.info(f"💾 优化配置已保存到: {config_path}")
    
    # 显示配置摘要
    logger.info(f"\n📋 优化配置摘要:")
    logger.info(f"  策略版本: {optimized_config['strategy_name']}")
    logger.info(f"  基于反转点: {optimized_config['statistics']['based_on_reversals']} 个")
    logger.info(f"  平均反转收益: {optimized_config['statistics']['avg_reversal_gain']}%")
    logger.info(f"  平均持续时间: {optimized_config['statistics']['avg_duration_weeks']} 周")
    
    logger.info(f"\n🎯 关键参数:")
    logger.info(f"  历史分位数阈值: {optimized_config['parameters']['historical_percentile_threshold']}")
    logger.info(f"  均线收敛阈值: {optimized_config['parameters']['ma_convergence_threshold']}")
    logger.info(f"  RSI阈值: {optimized_config['parameters']['rsi_threshold']}")
    logger.info(f"  前期跌幅阈值: {optimized_config['parameters']['decline_from_peak_threshold']}")
    logger.info(f"  波动性阈值: {optimized_config['parameters']['volatility_threshold']}")
    
    return optimized_config


if __name__ == "__main__":
    optimize_rtb_based_on_reversals()
