#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析ML分析的样本多样性和覆盖度
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from utils.db.db_manager import DatabaseManager
from app.data_loader import DataLoader
import pandas as pd

def analyze_sample_diversity():
    """分析样本多样性和覆盖度"""
    
    print("🔍 分析ML分析的样本多样性和覆盖度")
    print("="*50)
    
    # 初始化数据库
    db = DatabaseManager()
    data_loader = DataLoader(db)
    
    # 获取所有股票数量
    stock_list_table = db.get_table_instance('stock_list')
    all_stocks = stock_list_table.load_filtered_stock_list()
    total_stocks = len(all_stocks)
    
    print(f"📊 数据库总股票数: {total_stocks}")
    
    # 分析股票分布
    sz_stocks = [s for s in all_stocks if s['id'].endswith('.SZ')]
    sh_stocks = [s for s in all_stocks if s['id'].endswith('.SH')]
    
    print(f"📊 深市股票数: {len(sz_stocks)} ({len(sz_stocks)/total_stocks*100:.1f}%)")
    print(f"📊 沪市股票数: {len(sh_stocks)} ({len(sh_stocks)/total_stocks*100:.1f}%)")
    
    # 我们的测试样本
    test_stocks = ['000001.SZ', '000002.SZ', '000006.SZ', '000007.SZ', '000011.SZ']
    print(f"\n📊 测试样本数: {len(test_stocks)}")
    print(f"📊 样本覆盖率: {len(test_stocks)/total_stocks*100:.4f}%")
    
    # 检查样本多样性
    print(f"\n🎯 样本多样性分析:")
    print("-"*30)
    
    # 市场分布
    sz_count = sum(1 for s in test_stocks if s.endswith('.SZ'))
    sh_count = sum(1 for s in test_stocks if s.endswith('.SH'))
    print(f"📈 市场分布: 深市{sz_count}只, 沪市{sh_count}只")
    
    # 行业分布
    print(f"📈 行业分布:")
    industry_count = {}
    for stock_id in test_stocks:
        stock_info = next((s for s in all_stocks if s['id'] == stock_id), None)
        if stock_info:
            industry = stock_info.get('industry', '未知')
            industry_count[industry] = industry_count.get(industry, 0) + 1
            print(f"  {stock_id}: {stock_info.get('name', '未知')} - {industry}")
    
    print(f"\n📊 行业分布统计: {industry_count}")
    
    # 样本代表性评估
    print(f"\n📊 样本代表性评估:")
    print("-"*30)
    
    diversity_score = 0
    issues = []
    
    # 1. 样本数量评估
    if len(test_stocks) < 10:
        diversity_score -= 2
        issues.append("样本数量过少(<10只)")
    elif len(test_stocks) < 50:
        diversity_score -= 1
        issues.append("样本数量偏少(<50只)")
    else:
        diversity_score += 1
    
    # 2. 市场分布评估
    if sh_count == 0:
        diversity_score -= 2
        issues.append("缺少沪市样本")
    elif sz_count == 0:
        diversity_score -= 2
        issues.append("缺少深市样本")
    else:
        diversity_score += 1
    
    # 3. 行业分布评估
    unique_industries = len(set(industry_count.keys()))
    if unique_industries < 3:
        diversity_score -= 2
        issues.append(f"行业过于集中(仅{unique_industries}个行业)")
    elif unique_industries < 5:
        diversity_score -= 1
        issues.append(f"行业多样性不足({unique_industries}个行业)")
    else:
        diversity_score += 1
    
    # 4. 覆盖度评估
    coverage_rate = len(test_stocks) / total_stocks * 100
    if coverage_rate < 0.1:
        diversity_score -= 2
        issues.append(f"覆盖度过低({coverage_rate:.3f}%)")
    elif coverage_rate < 1.0:
        diversity_score -= 1
        issues.append(f"覆盖度偏低({coverage_rate:.3f}%)")
    else:
        diversity_score += 1
    
    print(f"📊 多样性评分: {diversity_score}/4")
    
    if issues:
        print(f"⚠️ 发现的问题:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"✅ 样本多样性良好")
    
    # 建议改进方案
    print(f"\n💡 改进建议:")
    print("-"*30)
    
    if len(test_stocks) < 50:
        print("1. 增加样本数量到至少50只股票")
    
    if sh_count == 0:
        print("2. 添加沪市股票样本")
    
    if unique_industries < 5:
        print("3. 增加行业多样性，覆盖至少5个不同行业")
    
    if coverage_rate < 1.0:
        print(f"4. 提高样本覆盖度到至少1% (当前{coverage_rate:.3f}%)")
    
    # 推荐扩展样本
    print(f"\n🎯 推荐扩展样本:")
    print("-"*30)
    
    # 按行业推荐
    industry_recommendations = {}
    for stock in all_stocks:
        industry = stock.get('industry', '未知')
        if industry not in industry_recommendations:
            industry_recommendations[industry] = []
        industry_recommendations[industry].append(stock)
    
    print("推荐添加的股票样本:")
    added_count = 0
    for industry, stocks in industry_recommendations.items():
        if added_count >= 10:  # 最多推荐10只
            break
        if len(stocks) > 0:
            # 优先选择沪市股票
            sh_stocks_in_industry = [s for s in stocks if s['id'].endswith('.SH')]
            if sh_stocks_in_industry:
                recommended_stock = sh_stocks_in_industry[0]
            else:
                recommended_stock = stocks[0]
            
            if recommended_stock['id'] not in test_stocks:
                print(f"  {recommended_stock['id']}: {recommended_stock.get('name', '未知')} - {industry}")
                added_count += 1
    
    return {
        'total_stocks': total_stocks,
        'sample_size': len(test_stocks),
        'coverage_rate': coverage_rate,
        'diversity_score': diversity_score,
        'issues': issues,
        'test_stocks': test_stocks
    }

if __name__ == "__main__":
    result = analyze_sample_diversity()
    
    print(f"\n📋 分析总结:")
    print("="*30)
    print(f"总股票数: {result['total_stocks']}")
    print(f"样本数: {result['sample_size']}")
    print(f"覆盖率: {result['coverage_rate']:.4f}%")
    print(f"多样性评分: {result['diversity_score']}/4")
    print(f"问题数量: {len(result['issues'])}")
    
    if result['diversity_score'] < 2:
        print("\n⚠️ 结论: 当前样本多样性不足，建议扩展样本后再进行ML分析")
    elif result['diversity_score'] < 3:
        print("\n⚠️ 结论: 当前样本多样性一般，建议适当扩展样本")
    else:
        print("\n✅ 结论: 当前样本多样性良好，ML分析结果相对可靠")
