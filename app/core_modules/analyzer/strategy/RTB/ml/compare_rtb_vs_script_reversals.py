#!/usr/bin/env python3
"""
对比RTB策略找到的反转点和脚本找到的反转点
分析哪些反转点被过滤了以及原因
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

from app.analyzer.strategy.RTB.feature_identity.reversal_data_generator_enhanced import EnhancedReversalDataGenerator
from app.analyzer.strategy.RTB.RTB import ReverseTrendBet
from app.analyzer.strategy.RTB.settings import settings
from app.data_manager.data_manager import DataManager

def load_rtb_trading_results():
    """加载RTB策略的交易结果"""
    results_dir = Path("/Users/garnet/Desktop/stocks-py/app/analyzer/strategy/RTB/tmp/2025_10_21-261")
    
    if not results_dir.exists():
        print(f"❌ RTB结果目录不存在: {results_dir}")
        return None
    
    rtb_reversals = []
    
    # 遍历所有股票结果文件
    for file_path in results_dir.glob("*.json"):
        if file_path.name.startswith("0_session_summary"):
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            stock_info = data.get('stock', {})
            stock_code = stock_info.get('id', '')
            stock_name = stock_info.get('name', '')
            
            # 获取投资记录
            investments = data.get('investments', [])
            for investment in investments:
                entry_date = investment.get('start_date')
                entry_price = investment.get('purchase_price')
                roi = investment.get('roi', 0)
                
                if entry_date and entry_price:
                    rtb_reversals.append({
                        'stock_code': stock_code,
                        'stock_name': stock_name,
                        'entry_date': entry_date,
                        'entry_price': entry_price,
                        'roi': roi * 100,  # 转换为百分比
                        'source': 'RTB'
                    })
                    
        except Exception as e:
            print(f"❌ 读取文件 {file_path} 时出错: {e}")
            continue
    
    print(f"✅ 加载了 {len(rtb_reversals)} 个RTB反转点")
    return rtb_reversals

def load_script_reversals():
    """加载脚本找到的反转点"""
    try:
        # 使用反转数据生成器
        generator = EnhancedReversalDataGenerator()
        
        # 获取股票列表（使用RTB相同的采样方式）
        stock_list = generator.get_sample_list()
        print(f"📊 获取到 {len(stock_list)} 只股票")
        
        script_reversals = []
        
        # 只处理前10只股票作为示例（避免运行时间过长）
        for i, stock in enumerate(stock_list[:10]):
            stock_code = stock['id'] if isinstance(stock, dict) else stock
            print(f"🔄 处理股票 {i+1}/10: {stock_code}")
            
            try:
                # 获取反转点
                reversals = generator.identify_reversal_for_stock(stock_code)
                
                for reversal in reversals:
                    script_reversals.append({
                        'stock_code': stock_code,
                        'stock_name': reversal.get('stock_name', ''),
                        'entry_date': reversal.get('date'),
                        'entry_price': reversal.get('price'),
                        'roi': reversal.get('gain', 0),
                        'source': 'Script'
                    })
                    
            except Exception as e:
                print(f"❌ 处理股票 {stock_code} 时出错: {e}")
                continue
        
        print(f"✅ 加载了 {len(script_reversals)} 个脚本反转点")
        return script_reversals
        
    except Exception as e:
        print(f"❌ 加载脚本反转点时出错: {e}")
        return []

def compare_reversals(rtb_reversals, script_reversals):
    """对比RTB和脚本找到的反转点"""
    
    # 转换为DataFrame
    rtb_df = pd.DataFrame(rtb_reversals)
    script_df = pd.DataFrame(script_reversals)
    
    if rtb_df.empty or script_df.empty:
        print("❌ 没有找到足够的反转点数据进行对比")
        return
    
    print("\n" + "="*60)
    print("📊 反转点对比分析")
    print("="*60)
    
    # 基本统计
    print(f"🔍 RTB策略找到的反转点: {len(rtb_df)}")
    print(f"🔍 脚本找到的反转点: {len(script_df)}")
    
    # 按股票分组统计
    rtb_by_stock = rtb_df.groupby('stock_code').size()
    script_by_stock = script_df.groupby('stock_code').size()
    
    print(f"\n📈 RTB策略平均每只股票反转点数: {rtb_by_stock.mean():.2f}")
    print(f"📈 脚本平均每只股票反转点数: {script_by_stock.mean():.2f}")
    
    # 找出被过滤的反转点
    filtered_reversals = []
    
    for stock_code in script_df['stock_code'].unique():
        script_stock_reversals = script_df[script_df['stock_code'] == stock_code]
        rtb_stock_reversals = rtb_df[rtb_df['stock_code'] == stock_code]
        
        # 检查每个脚本反转点是否在RTB中
        for _, script_reversal in script_stock_reversals.iterrows():
            script_date = script_reversal['entry_date']
            script_price = script_reversal['entry_price']
            
            # 检查是否有相同日期的RTB反转点
            same_date_rtb = rtb_stock_reversals[
                rtb_stock_reversals['entry_date'] == script_date
            ]
            
            if same_date_rtb.empty:
                # 这个反转点被过滤了
                filtered_reversals.append({
                    'stock_code': stock_code,
                    'stock_name': script_reversal['stock_name'],
                    'entry_date': script_date,
                    'entry_price': script_price,
                    'roi': script_reversal['roi'],
                    'reason': '被RTB过滤'
                })
    
    print(f"\n🚫 被过滤的反转点数量: {len(filtered_reversals)}")
    print(f"📊 过滤率: {len(filtered_reversals) / len(script_df) * 100:.1f}%")
    
    # 分析被过滤反转点的特征
    if filtered_reversals:
        filtered_df = pd.DataFrame(filtered_reversals)
        
        print(f"\n📈 被过滤反转点的ROI分布:")
        print(f"  平均ROI: {filtered_df['roi'].mean():.2f}%")
        print(f"  中位数ROI: {filtered_df['roi'].median():.2f}%")
        print(f"  最大ROI: {filtered_df['roi'].max():.2f}%")
        print(f"  最小ROI: {filtered_df['roi'].min():.2f}%")
        
        # 按股票统计被过滤的反转点
        filtered_by_stock = filtered_df.groupby('stock_code').size()
        print(f"\n📊 被过滤反转点最多的前5只股票:")
        for stock_code, count in filtered_by_stock.nlargest(5).items():
            stock_name = filtered_df[filtered_df['stock_code'] == stock_code]['stock_name'].iloc[0]
            print(f"  {stock_code} ({stock_name}): {count}个")
    
    return filtered_reversals

def analyze_filtering_reasons(filtered_reversals):
    """分析过滤原因"""
    if not filtered_reversals:
        print("❌ 没有被过滤的反转点可分析")
        return
    
    print("\n" + "="*60)
    print("🔍 过滤原因分析")
    print("="*60)
    
    # 使用RTB策略检查被过滤的反转点
    from utils.db.db_manager import DatabaseManager
    db_manager = DatabaseManager()
    rtb_strategy = ReverseTrendBet(db_manager)
    data_mgr = DataManager(is_verbose=False)
    
    failed_conditions = {}
    
    for i, reversal in enumerate(filtered_reversals[:5]):  # 只分析前5个
        stock_code = reversal['stock_code']
        entry_date = reversal['entry_date']
        
        print(f"\n🔄 分析被过滤的反转点 {i+1}/5: {stock_code} {entry_date}")
        
        try:
            # 获取该日期的K线数据
            klines = data_mgr.get_kline_data(
                stock_code=stock_code,
                start_date=entry_date,
                end_date=entry_date,
                freq='W'
            )
            
            if klines.empty:
                print(f"  ❌ 无法获取K线数据")
                continue
            
            # 计算特征
            features = rtb_strategy._calculate_ml_enhanced_features(klines, entry_date)
            
            if features is None:
                print(f"  ❌ 无法计算特征")
                continue
            
            # 检查每个条件
            conditions = [
                ('market_cap', features['market_cap'] < 1200000, f"市值 {features['market_cap']:.0f} < 1200000"),
                ('pe_ratio', features['pe_ratio'] < 80, f"PE {features['pe_ratio']:.2f} < 80"),
                ('pb_ratio', features['pb_ratio'] < 5.0, f"PB {features['pb_ratio']:.2f} < 5.0"),
                ('rsi', features['rsi'] > 15 and features['rsi'] < 85, f"RSI {features['rsi']:.2f} 在 15-85 之间"),
                ('price_percentile', features['price_percentile'] > 0.05 and features['price_percentile'] < 0.80, f"价格分位数 {features['price_percentile']:.3f} 在 0.05-0.80 之间"),
                ('volatility', features['volatility'] > 0.01 and features['volatility'] < 0.30, f"波动率 {features['volatility']:.3f} 在 0.01-0.30 之间"),
                ('volume_ratio_before', features['volume_ratio_before'] >= 1.0, f"反转前成交量比率 {features['volume_ratio_before']:.2f} >= 1.0"),
                ('volume_ratio_after', features['volume_ratio_after'] >= 1.0, f"反转后成交量比率 {features['volume_ratio_after']:.2f} >= 1.0"),
                ('ma_convergence', features['ma_convergence'] < 0.15, f"均线收敛度 {features['ma_convergence']:.3f} < 0.15"),
                ('price_vs_ma20', -0.15 < features['price_vs_ma20'] < 0.15, f"价格vsMA20 {features['price_vs_ma20']:.3f} 在 ±0.15 之间"),
                ('price_vs_ma60', -0.20 < features['price_vs_ma60'] < 0.20, f"价格vsMA60 {features['price_vs_ma60']:.3f} 在 ±0.20 之间"),
                ('monthly_drop_rate', features['monthly_drop_rate'] > 0.01 and features['monthly_drop_rate'] < 0.70, f"月线跌幅 {features['monthly_drop_rate']:.3f} 在 0.01-0.70 之间"),
                ('ma20_slope', features['ma20_slope'] > -0.05, f"MA20斜率 {features['ma20_slope']:.4f} > -0.05"),
            ]
            
            failed_conditions_for_this = []
            for condition_name, condition_result, condition_desc in conditions:
                if not condition_result:
                    failed_conditions_for_this.append(condition_name)
                    print(f"  ❌ {condition_desc}")
                else:
                    print(f"  ✅ {condition_desc}")
            
            # 统计失败的条件
            for condition in failed_conditions_for_this:
                failed_conditions[condition] = failed_conditions.get(condition, 0) + 1
            
        except Exception as e:
            print(f"  ❌ 分析时出错: {e}")
            continue
    
    # 输出最常见的失败条件
    if failed_conditions:
        print(f"\n📊 最常见的失败条件:")
        for condition, count in sorted(failed_conditions.items(), key=lambda x: x[1], reverse=True):
            print(f"  {condition}: {count}次")

def main():
    """主函数"""
    print("🚀 开始对比RTB策略和脚本找到的反转点")
    
    # 加载RTB反转点
    rtb_reversals = load_rtb_trading_results()
    if not rtb_reversals:
        print("❌ 无法加载RTB反转点")
        return
    
    # 加载脚本反转点
    script_reversals = load_script_reversals()
    if not script_reversals:
        print("❌ 无法加载脚本反转点")
        return
    
    # 对比反转点
    filtered_reversals = compare_reversals(rtb_reversals, script_reversals)
    
    # 分析过滤原因
    if filtered_reversals:
        analyze_filtering_reasons(filtered_reversals)
    
    print("\n✅ 分析完成！")

if __name__ == "__main__":
    main()
