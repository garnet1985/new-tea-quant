#!/usr/bin/env python3
"""
详细分析黑名单股票的财务特征差异
"""
import sys
from pathlib import Path
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Any

# Add the project root to the Python path
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))
sys.path.append('.')

from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader

def get_blacklist_stocks():
    """获取黑名单股票列表"""
    blacklist_stocks = [
        '603188.SH', '600169.SH', '300370.SZ', '600333.SH', '601198.SH',
        '000677.SZ', '600094.SH', '002570.SZ', '601002.SH', '603698.SH',
        '002513.SZ', '300388.SZ', '600348.SH', '600108.SH', '600638.SH',
        '000759.SZ', '002608.SZ', '601992.SH', '002278.SZ'
    ]
    return blacklist_stocks

def get_random_sample_stocks():
    """获取随机样本股票用于对比"""
    good_performers = [
        '300105.SZ', '600396.SH', '600251.SH', '002708.SZ', '000678.SZ',
        '600780.SH', '600805.SH', '300022.SZ', '600854.SH', '300359.SZ',
        '000001.SZ', '000002.SZ', '000858.SZ', '002415.SZ', '300059.SZ',
        '600000.SH', '600036.SH', '600519.SH', '600887.SH', '000858.SZ'
    ]
    return good_performers

def analyze_stock_financials(stock_ids: List[str], db_manager, data_loader) -> Dict[str, Dict]:
    """分析股票的财务指标"""
    print(f"📊 分析{len(stock_ids)}只股票的财务指标...")
    
    financial_data = {}
    
    for i, stock_id in enumerate(stock_ids):
        try:
            print(f"  处理 {i+1}/{len(stock_ids)}: {stock_id}")
            
            # 获取股票基本信息
            stock_info = data_loader.load_stock_list()
            stock_details = next((s for s in stock_info if s['id'] == stock_id), None)
            
            if not stock_details:
                print(f"    ❌ 未找到股票信息: {stock_id}")
                continue
            
            # 获取最新的财务数据
            try:
                # 获取最新K线数据（包含财务指标）
                klines = data_loader.load_klines(
                    stock_id=stock_id,
                    term='daily',
                    adjust='qfq'
                )
                
                if not klines:
                    print(f"    ❌ 无K线数据: {stock_id}")
                    continue
                
                # 获取最新一条K线的财务数据
                latest_kline = klines[-1]
                
                # 提取财务指标
                financial_metrics = {
                    'stock_id': stock_id,
                    'stock_name': stock_details.get('name', ''),
                    'industry': stock_details.get('industry', ''),
                    'market_cap': latest_kline.get('total_market_value', None),
                    'pe_ratio': latest_kline.get('pe', None),
                    'pb_ratio': latest_kline.get('pb', None),
                    'ps_ratio': latest_kline.get('ps', None),
                    'turnover_rate': latest_kline.get('turnover_rate', None),
                    'volume_ratio': latest_kline.get('volume_ratio', None),
                    'close': latest_kline.get('close', None),
                    'volume': latest_kline.get('volume', None),
                    'amount': latest_kline.get('amount', None),
                    'total_share': latest_kline.get('total_share', None),
                    'float_share': latest_kline.get('float_share', None),
                }
                
                financial_data[stock_id] = financial_metrics
                
            except Exception as e:
                print(f"    ❌ 获取财务数据失败 {stock_id}: {e}")
                continue
                
        except Exception as e:
            print(f"❌ 处理股票失败 {stock_id}: {e}")
            continue
    
    return financial_data

def detailed_analysis(blacklist_data: Dict, sample_data: Dict):
    """详细分析财务数据模式"""
    print(f"\n📈 详细财务数据分析:")
    
    # 转换为DataFrame便于分析
    blacklist_df = pd.DataFrame(list(blacklist_data.values()))
    sample_df = pd.DataFrame(list(sample_data.values()))
    
    print(f"黑名单股票数量: {len(blacklist_df)}")
    print(f"样本股票数量: {len(sample_df)}")
    
    # 详细分析各项财务指标
    financial_metrics = ['market_cap', 'pe_ratio', 'pb_ratio', 'ps_ratio', 'turnover_rate', 'volume_ratio']
    
    print(f"\n🔍 详细财务指标对比分析:")
    print(f"{'指标':<15} {'黑名单均值':<12} {'样本均值':<12} {'差异':<10} {'差异%':<10} {'显著性':<8}")
    print("-" * 85)
    
    for metric in financial_metrics:
        if metric in blacklist_df.columns and metric in sample_df.columns:
            # 过滤掉无效值
            blacklist_values = pd.to_numeric(blacklist_df[metric], errors='coerce').dropna()
            sample_values = pd.to_numeric(sample_df[metric], errors='coerce').dropna()
            
            if len(blacklist_values) > 0 and len(sample_values) > 0:
                blacklist_mean = blacklist_values.mean()
                sample_mean = sample_values.mean()
                difference = blacklist_mean - sample_mean
                
                # 计算差异百分比
                if sample_mean != 0:
                    diff_percent = (difference / abs(sample_mean)) * 100
                else:
                    diff_percent = 0
                
                # 简单的显著性判断（基于标准差）
                blacklist_std = blacklist_values.std()
                sample_std = sample_values.std()
                
                if abs(difference) > (blacklist_std + sample_std) / 2:
                    significance = "显著"
                else:
                    significance = "不显著"
                
                print(f"{metric:<15} {blacklist_mean:<12.2f} {sample_mean:<12.2f} {difference:<10.2f} {diff_percent:<10.1f}% {significance:<8}")
            else:
                print(f"{metric:<15} {'N/A':<12} {'N/A':<12} {'N/A':<10} {'N/A':<10} {'N/A':<8}")
    
    # 分析市值分布
    print(f"\n💰 市值分布分析:")
    analyze_market_cap_distribution(blacklist_df, sample_df)
    
    # 分析估值指标
    print(f"\n📊 估值指标分析:")
    analyze_valuation_metrics(blacklist_df, sample_df)
    
    # 分析交易活跃度
    print(f"\n📈 交易活跃度分析:")
    analyze_trading_activity(blacklist_df, sample_df)
    
    # 分析行业特征
    print(f"\n🏭 行业特征分析:")
    analyze_industry_characteristics(blacklist_df, sample_df)

def analyze_market_cap_distribution(blacklist_df: pd.DataFrame, sample_df: pd.DataFrame):
    """分析市值分布"""
    blacklist_caps = pd.to_numeric(blacklist_df['market_cap'], errors='coerce').dropna()
    sample_caps = pd.to_numeric(sample_df['market_cap'], errors='coerce').dropna()
    
    if len(blacklist_caps) > 0 and len(sample_caps) > 0:
        print(f"黑名单市值分布:")
        print(f"  平均值: {blacklist_caps.mean():,.0f}万元")
        print(f"  中位数: {blacklist_caps.median():,.0f}万元")
        print(f"  最小值: {blacklist_caps.min():,.0f}万元")
        print(f"  最大值: {blacklist_caps.max():,.0f}万元")
        
        print(f"样本市值分布:")
        print(f"  平均值: {sample_caps.mean():,.0f}万元")
        print(f"  中位数: {sample_caps.median():,.0f}万元")
        print(f"  最小值: {sample_caps.min():,.0f}万元")
        print(f"  最大值: {sample_caps.max():,.0f}万元")
        
        # 市值区间分析
        print(f"\n市值区间分布:")
        cap_ranges = [
            (0, 500000, "小盘股(<50亿)"),
            (500000, 2000000, "中盘股(50-200亿)"),
            (2000000, 10000000, "大盘股(200-1000亿)"),
            (10000000, float('inf'), "超大盘股(>1000亿)")
        ]
        
        for min_cap, max_cap, label in cap_ranges:
            blacklist_count = len(blacklist_caps[(blacklist_caps >= min_cap) & (blacklist_caps < max_cap)])
            sample_count = len(sample_caps[(sample_caps >= min_cap) & (sample_caps < max_cap)])
            print(f"  {label}: 黑名单={blacklist_count}只, 样本={sample_count}只")

def analyze_valuation_metrics(blacklist_df: pd.DataFrame, sample_df: pd.DataFrame):
    """分析估值指标"""
    metrics = ['pe_ratio', 'pb_ratio', 'ps_ratio']
    
    for metric in metrics:
        blacklist_values = pd.to_numeric(blacklist_df[metric], errors='coerce').dropna()
        sample_values = pd.to_numeric(sample_df[metric], errors='coerce').dropna()
        
        if len(blacklist_values) > 0 and len(sample_values) > 0:
            print(f"\n{metric}分析:")
            print(f"  黑名单: 均值={blacklist_values.mean():.2f}, 中位数={blacklist_values.median():.2f}")
            print(f"  样本: 均值={sample_values.mean():.2f}, 中位数={sample_values.median():.2f}")
            
            # 极端值分析
            blacklist_extreme = len(blacklist_values[(blacklist_values < 0) | (blacklist_values > 100)])
            sample_extreme = len(sample_values[(sample_values < 0) | (sample_values > 100)])
            print(f"  极端值数量: 黑名单={blacklist_extreme}, 样本={sample_extreme}")

def analyze_trading_activity(blacklist_df: pd.DataFrame, sample_df: pd.DataFrame):
    """分析交易活跃度"""
    metrics = ['turnover_rate', 'volume_ratio']
    
    for metric in metrics:
        blacklist_values = pd.to_numeric(blacklist_df[metric], errors='coerce').dropna()
        sample_values = pd.to_numeric(sample_df[metric], errors='coerce').dropna()
        
        if len(blacklist_values) > 0 and len(sample_values) > 0:
            print(f"\n{metric}分析:")
            print(f"  黑名单: 均值={blacklist_values.mean():.2f}, 中位数={blacklist_values.median():.2f}")
            print(f"  样本: 均值={sample_values.mean():.2f}, 中位数={sample_values.median():.2f}")

def analyze_industry_characteristics(blacklist_df: pd.DataFrame, sample_df: pd.DataFrame):
    """分析行业特征"""
    print(f"黑名单股票行业分布:")
    blacklist_industries = blacklist_df['industry'].value_counts()
    for industry, count in blacklist_industries.items():
        print(f"  {industry}: {count}只")
    
    print(f"\n样本股票行业分布:")
    sample_industries = sample_df['industry'].value_counts()
    for industry, count in sample_industries.items():
        print(f"  {industry}: {count}只")
    
    # 找出黑名单中特有的行业
    blacklist_only = set(blacklist_industries.index) - set(sample_industries.index)
    sample_only = set(sample_industries.index) - set(blacklist_industries.index)
    
    if blacklist_only:
        print(f"\n黑名单特有行业: {', '.join(blacklist_only)}")
    if sample_only:
        print(f"样本特有行业: {', '.join(sample_only)}")

def main():
    print("🚀 详细分析黑名单股票财务特征...")
    
    # 初始化数据库和加载器
    db = DatabaseManager()
    db.initialize()
    data_loader = DataLoader(db)
    
    try:
        # 获取黑名单股票
        blacklist_stocks = get_blacklist_stocks()
        print(f"📋 黑名单股票: {len(blacklist_stocks)}只")
        
        # 获取样本股票
        sample_stocks = get_random_sample_stocks()
        print(f"📊 样本股票: {len(sample_stocks)}只")
        
        # 分析财务数据
        blacklist_financials = analyze_stock_financials(blacklist_stocks, db, data_loader)
        sample_financials = analyze_stock_financials(sample_stocks, db, data_loader)
        
        # 详细分析模式
        detailed_analysis(blacklist_financials, sample_financials)
        
        print(f"\n💡 结论:")
        print("✅ 成功分析了黑名单和样本股票的详细财务特征")
        print("📊 请查看上方的详细对比分析结果")
            
    except Exception as e:
        print(f"❌ 分析失败: {e}")
    finally:
        if db.is_sync_connected:
            db.disconnect()

if __name__ == "__main__":
    main()
