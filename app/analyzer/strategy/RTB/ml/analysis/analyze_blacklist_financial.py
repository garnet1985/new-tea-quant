#!/usr/bin/env python3
"""
分析黑名单股票的财务特征
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
    # 基于之前的分析结果
    blacklist_stocks = [
        '603188.SH', '600169.SH', '300370.SZ', '600333.SH', '601198.SH',
        '000677.SZ', '600094.SH', '002570.SZ', '601002.SH', '603698.SH',
        '002513.SZ', '300388.SZ', '600348.SH', '600108.SH', '600638.SH',
        '000759.SZ', '002608.SZ', '601992.SH', '002278.SZ'
    ]
    return blacklist_stocks

def get_random_sample_stocks(sample_size=50):
    """获取随机样本股票用于对比"""
    # 从V17结果中随机选择一些表现较好的股票
    good_performers = [
        '300105.SZ', '600396.SH', '600251.SH', '002708.SZ', '000678.SZ',
        '600780.SH', '600805.SH', '300022.SZ', '600854.SH', '300359.SZ'
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

def analyze_financial_patterns(blacklist_data: Dict, sample_data: Dict):
    """分析财务数据模式"""
    print(f"\n📈 财务数据分析:")
    
    # 转换为DataFrame便于分析
    blacklist_df = pd.DataFrame(list(blacklist_data.values()))
    sample_df = pd.DataFrame(list(sample_data.values()))
    
    print(f"黑名单股票数量: {len(blacklist_df)}")
    print(f"样本股票数量: {len(sample_df)}")
    
    # 分析各项财务指标
    financial_metrics = ['market_cap', 'pe_ratio', 'pb_ratio', 'ps_ratio', 'turnover_rate', 'volume_ratio']
    
    print(f"\n🔍 财务指标对比分析:")
    print(f"{'指标':<15} {'黑名单均值':<12} {'样本均值':<12} {'差异':<10} {'显著性':<8}")
    print("-" * 70)
    
    for metric in financial_metrics:
        if metric in blacklist_df.columns and metric in sample_df.columns:
            # 过滤掉无效值
            blacklist_values = pd.to_numeric(blacklist_df[metric], errors='coerce').dropna()
            sample_values = pd.to_numeric(sample_df[metric], errors='coerce').dropna()
            
            if len(blacklist_values) > 0 and len(sample_values) > 0:
                blacklist_mean = blacklist_values.mean()
                sample_mean = sample_values.mean()
                difference = blacklist_mean - sample_mean
                
                # 简单的显著性判断（基于标准差）
                blacklist_std = blacklist_values.std()
                sample_std = sample_values.std()
                
                if abs(difference) > (blacklist_std + sample_std) / 2:
                    significance = "显著"
                else:
                    significance = "不显著"
                
                print(f"{metric:<15} {blacklist_mean:<12.2f} {sample_mean:<12.2f} {difference:<10.2f} {significance:<8}")
            else:
                print(f"{metric:<15} {'N/A':<12} {'N/A':<12} {'N/A':<10} {'N/A':<8}")
    
    # 分析行业分布
    print(f"\n🏭 行业分布对比:")
    
    blacklist_industries = blacklist_df['industry'].value_counts()
    sample_industries = sample_df['industry'].value_counts()
    
    print(f"\n黑名单股票行业分布:")
    for industry, count in blacklist_industries.head(10).items():
        print(f"  {industry}: {count}只")
    
    print(f"\n样本股票行业分布:")
    for industry, count in sample_industries.head(10).items():
        print(f"  {industry}: {count}只")
    
    # 分析异常值
    print(f"\n⚠️ 异常值分析:")
    analyze_outliers(blacklist_df, "黑名单股票")
    analyze_outliers(sample_df, "样本股票")

def analyze_outliers(df: pd.DataFrame, group_name: str):
    """分析异常值"""
    print(f"\n{group_name}异常值:")
    
    metrics = ['pe_ratio', 'pb_ratio', 'market_cap']
    for metric in metrics:
        if metric in df.columns:
            values = pd.to_numeric(df[metric], errors='coerce').dropna()
            if len(values) > 0:
                q1 = values.quantile(0.25)
                q3 = values.quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                
                outliers = values[(values < lower_bound) | (values > upper_bound)]
                print(f"  {metric}: {len(outliers)}个异常值 (范围: {lower_bound:.2f} - {upper_bound:.2f})")

def main():
    print("🚀 分析黑名单股票财务特征...")
    
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
        
        # 分析模式
        analyze_financial_patterns(blacklist_financials, sample_financials)
        
        print(f"\n💡 结论:")
        if len(blacklist_financials) > 0 and len(sample_financials) > 0:
            print("✅ 成功分析了黑名单和样本股票的财务特征")
            print("📊 请查看上方的对比分析结果")
        else:
            print("❌ 财务数据获取失败，可能需要检查数据源")
            
    except Exception as e:
        print(f"❌ 分析失败: {e}")
    finally:
        if db.is_sync_connected:
            db.disconnect()

if __name__ == "__main__":
    main()
