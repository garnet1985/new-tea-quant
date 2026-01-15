#!/usr/bin/env python3
"""
简化版RTB条件优化
基于脚本识别的反转点数量，直接调整RTB条件以让更多反转点通过
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
from datetime import datetime
import sys
import os

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(project_root))

# 确保能够导入RTB相关模块
rtb_root = Path(__file__).parent.parent
sys.path.append(str(rtb_root))

from core.modules.analyzer.strategy.RTB.feature_identity.reversal_data_generator_enhanced import EnhancedReversalDataGenerator

def analyze_script_reversal_statistics():
    """分析脚本反转点统计信息"""
    print("🚀 开始分析脚本反转点统计信息")
    
    try:
        generator = EnhancedReversalDataGenerator()
        stock_list = generator.get_sample_list()
        
        reversal_stats = []
        
        # 处理前50只股票作为样本
        for i, stock in enumerate(stock_list[:50]):
            stock_code = stock['id'] if isinstance(stock, dict) else stock
            if i % 10 == 0:
                print(f"🔄 处理股票 {i+1}/50: {stock_code}")
            
            try:
                reversals = generator.identify_reversal_for_stock(stock_code)
                reversal_count = len(reversals)
                
                reversal_stats.append({
                    'stock_code': stock_code,
                    'reversal_count': reversal_count
                })
                    
            except Exception as e:
                print(f"❌ 处理股票 {stock_code} 时出错: {e}")
                continue
        
        print(f"✅ 处理完成，共 {len(reversal_stats)} 只股票")
        return reversal_stats
        
    except Exception as e:
        print(f"❌ 分析失败: {e}")
        return []

def analyze_current_rtb_performance():
    """分析当前RTB策略表现"""
    print("\n" + "="*60)
    print("📊 当前RTB策略表现分析")
    print("="*60)
    
    # 从最新的RTB结果中获取统计信息
    results_dir = Path("/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/tmp/2025_10_21-261")
    
    if results_dir.exists():
        summary_file = results_dir / "0_session_summary.json"
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary = json.load(f)
            
            print(f"📈 总投资次数: {summary.get('total_investments', 0)}")
            print(f"📈 胜率: {summary.get('win_rate', 0):.1f}%")
            print(f"📈 平均ROI: {summary.get('avg_roi', 0)*100:.1f}%")
            print(f"📈 年化收益率: {summary.get('annual_return', 0):.1f}%")
            print(f"📈 有投资机会的股票数: {summary.get('stocks_have_opportunities', 0)}")
            
            # 计算平均每只股票的投资次数
            total_stocks = 500  # 假设测试了500只股票
            avg_investments_per_stock = summary.get('total_investments', 0) / total_stocks
            print(f"📈 平均每只股票投资次数: {avg_investments_per_stock:.2f}")
            
            return summary
        else:
            print("❌ 未找到RTB结果摘要文件")
            return None
    else:
        print("❌ RTB结果目录不存在")
        return None

def recommend_rtb_condition_adjustments(reversal_stats, rtb_performance):
    """推荐RTB条件调整"""
    print("\n" + "="*60)
    print("💡 RTB条件调整建议")
    print("="*60)
    
    if not reversal_stats:
        print("❌ 没有脚本反转点统计数据")
        return
    
    # 计算脚本识别的反转点统计
    reversal_counts = [stat['reversal_count'] for stat in reversal_stats]
    avg_script_reversals = np.mean(reversal_counts)
    max_script_reversals = np.max(reversal_counts)
    
    print(f"📊 脚本识别的反转点统计:")
    print(f"   平均每只股票反转点数: {avg_script_reversals:.1f}")
    print(f"   最大每只股票反转点数: {max_script_reversals}")
    print(f"   反转点分布: {np.percentile(reversal_counts, [25, 50, 75])}")
    
    # 当前RTB表现
    if rtb_performance:
        avg_rtb_investments = rtb_performance.get('total_investments', 0) / 500
        print(f"\n📊 当前RTB策略表现:")
        print(f"   平均每只股票投资次数: {avg_rtb_investments:.2f}")
        print(f"   胜率: {rtb_performance.get('win_rate', 0):.1f}%")
        print(f"   平均ROI: {rtb_performance.get('avg_roi', 0)*100:.1f}%")
    
    # 计算差距
    gap_ratio = avg_script_reversals / avg_rtb_investments if avg_rtb_investments > 0 else 0
    print(f"\n📊 机会差距分析:")
    print(f"   脚本识别vs RTB投资比例: {gap_ratio:.1f}:1")
    print(f"   说明RTB策略错过了 {gap_ratio:.1f} 倍的反转机会")
    
    # 推荐调整策略
    print(f"\n💡 推荐调整策略:")
    
    if gap_ratio > 5:
        print("   🔴 差距巨大，需要大幅放宽条件")
        print("   建议: 放宽所有筛选条件，重点关注核心指标")
    elif gap_ratio > 3:
        print("   🟡 差距较大，需要适度放宽条件")
        print("   建议: 放宽部分筛选条件，保持质量")
    elif gap_ratio > 2:
        print("   🟢 差距适中，需要小幅调整")
        print("   建议: 微调筛选条件，平衡数量和质量")
    else:
        print("   ✅ 差距较小，当前策略较为合理")
        print("   建议: 保持当前策略，关注质量优化")
    
    # 具体的条件调整建议
    print(f"\n🔧 具体条件调整建议:")
    
    # 基于差距比例推荐调整幅度
    if gap_ratio > 5:
        adjustment_factor = 2.0  # 大幅放宽
        print("   📈 大幅放宽模式 (调整系数: 2.0)")
    elif gap_ratio > 3:
        adjustment_factor = 1.5  # 适度放宽
        print("   📈 适度放宽模式 (调整系数: 1.5)")
    elif gap_ratio > 2:
        adjustment_factor = 1.2  # 小幅放宽
        print("   📈 小幅放宽模式 (调整系数: 1.2)")
    else:
        adjustment_factor = 1.0  # 保持现状
        print("   📈 保持现状模式 (调整系数: 1.0)")
    
    # 生成调整后的条件
    current_conditions = {
        'market_cap': 1200000,
        'pe_ratio_max': 80,
        'pe_ratio_min': 3,
        'pb_ratio_max': 5.0,
        'pb_ratio_min': 0.1,
        'rsi_max': 85,
        'rsi_min': 15,
        'price_percentile_max': 0.80,
        'price_percentile_min': 0.05,
        'volatility_max': 0.30,
        'volatility_min': 0.01,
        'volume_ratio_before': 1.0,
        'volume_ratio_after': 1.0,
        'ma_convergence': 0.15,
        'price_vs_ma20_max': 0.15,
        'price_vs_ma20_min': -0.15,
        'price_vs_ma60_max': 0.20,
        'price_vs_ma60_min': -0.20,
        'monthly_drop_rate_max': 0.70,
        'monthly_drop_rate_min': 0.01,
        'ma20_slope': -0.05,
    }
    
    print(f"\n📋 调整后的条件建议:")
    print("```python")
    print("# 调整后的RTB筛选条件")
    print("conditions = [")
    
    # 市值条件
    new_market_cap = int(current_conditions['market_cap'] * adjustment_factor)
    print(f"    features['market_cap'] < {new_market_cap},  # 市值 < {new_market_cap/10000:.0f}万")
    
    # PE条件
    new_pe_max = int(current_conditions['pe_ratio_max'] * adjustment_factor)
    new_pe_min = max(1, int(current_conditions['pe_ratio_min'] / adjustment_factor))
    print(f"    features['pe_ratio'] < {new_pe_max},  # PE < {new_pe_max}")
    print(f"    features['pe_ratio'] > {new_pe_min},  # PE > {new_pe_min}")
    
    # PB条件
    new_pb_max = current_conditions['pb_ratio_max'] * adjustment_factor
    new_pb_min = max(0.1, current_conditions['pb_ratio_min'] / adjustment_factor)
    print(f"    features['pb_ratio'] < {new_pb_max:.1f},  # PB < {new_pb_max:.1f}")
    print(f"    features['pb_ratio'] > {new_pb_min:.1f},  # PB > {new_pb_min:.1f}")
    
    # RSI条件
    new_rsi_max = min(100, int(current_conditions['rsi_max'] + 5 * adjustment_factor))
    new_rsi_min = max(0, int(current_conditions['rsi_min'] - 5 * adjustment_factor))
    print(f"    features['rsi'] < {new_rsi_max},  # RSI < {new_rsi_max}")
    print(f"    features['rsi'] > {new_rsi_min},  # RSI > {new_rsi_min}")
    
    # 价格分位数条件
    new_price_percentile_max = min(1.0, current_conditions['price_percentile_max'] + 0.1 * adjustment_factor)
    new_price_percentile_min = max(0.0, current_conditions['price_percentile_min'] - 0.05 * adjustment_factor)
    print(f"    features['price_percentile'] < {new_price_percentile_max:.2f},  # 价格分位数 < {new_price_percentile_max:.2f}")
    print(f"    features['price_percentile'] > {new_price_percentile_min:.2f},  # 价格分位数 > {new_price_percentile_min:.2f}")
    
    # 波动率条件
    new_volatility_max = current_conditions['volatility_max'] * adjustment_factor
    new_volatility_min = max(0.001, current_conditions['volatility_min'] / adjustment_factor)
    print(f"    features['volatility'] < {new_volatility_max:.3f},  # 波动率 < {new_volatility_max:.3f}")
    print(f"    features['volatility'] > {new_volatility_min:.3f},  # 波动率 > {new_volatility_min:.3f}")
    
    # 成交量条件
    new_volume_ratio_before = max(0.5, current_conditions['volume_ratio_before'] / adjustment_factor)
    new_volume_ratio_after = max(0.5, current_conditions['volume_ratio_after'] / adjustment_factor)
    print(f"    features['volume_ratio_before'] >= {new_volume_ratio_before:.1f},  # 反转前成交量比率 >= {new_volume_ratio_before:.1f}")
    print(f"    features['volume_ratio_after'] >= {new_volume_ratio_after:.1f},  # 反转后成交量比率 >= {new_volume_ratio_after:.1f}")
    
    # 均线收敛度条件
    new_ma_convergence = current_conditions['ma_convergence'] * adjustment_factor
    print(f"    features['ma_convergence'] < {new_ma_convergence:.3f},  # 均线收敛度 < {new_ma_convergence:.3f}")
    
    # 价格相对均线条件
    new_price_vs_ma20_max = current_conditions['price_vs_ma20_max'] * adjustment_factor
    new_price_vs_ma20_min = current_conditions['price_vs_ma20_min'] * adjustment_factor
    print(f"    -{new_price_vs_ma20_max:.2f} < features['price_vs_ma20'] < {new_price_vs_ma20_max:.2f},  # 价格vsMA20在±{new_price_vs_ma20_max:.2f}内")
    
    new_price_vs_ma60_max = current_conditions['price_vs_ma60_max'] * adjustment_factor
    new_price_vs_ma60_min = current_conditions['price_vs_ma60_min'] * adjustment_factor
    print(f"    -{new_price_vs_ma60_max:.2f} < features['price_vs_ma60'] < {new_price_vs_ma60_max:.2f},  # 价格vsMA60在±{new_price_vs_ma60_max:.2f}内")
    
    # 月线跌幅条件
    new_monthly_drop_rate_max = current_conditions['monthly_drop_rate_max'] * adjustment_factor
    new_monthly_drop_rate_min = max(0.001, current_conditions['monthly_drop_rate_min'] / adjustment_factor)
    print(f"    features['monthly_drop_rate'] < {new_monthly_drop_rate_max:.3f},  # 月线跌幅 < {new_monthly_drop_rate_max:.3f}")
    print(f"    features['monthly_drop_rate'] > {new_monthly_drop_rate_min:.3f},  # 月线跌幅 > {new_monthly_drop_rate_min:.3f}")
    
    # 均线斜率条件
    new_ma20_slope = current_conditions['ma20_slope'] * adjustment_factor
    print(f"    features['ma20_slope'] > {new_ma20_slope:.3f},  # MA20斜率 > {new_ma20_slope:.3f}")
    
    print("]")
    print("```")
    
    print(f"\n🎯 预期效果:")
    print(f"   预计投资机会增加: {adjustment_factor:.1f}x")
    print(f"   预计平均每只股票投资次数: {avg_rtb_investments * adjustment_factor:.1f}")
    print(f"   建议监控胜率和ROI变化")

def main():
    """主函数"""
    print("🚀 开始简化版RTB条件优化分析")
    
    # 分析脚本反转点统计
    reversal_stats = analyze_script_reversal_statistics()
    
    # 分析当前RTB表现
    rtb_performance = analyze_current_rtb_performance()
    
    # 推荐调整
    recommend_rtb_condition_adjustments(reversal_stats, rtb_performance)
    
    print("\n✅ 优化分析完成！")

if __name__ == "__main__":
    main()
