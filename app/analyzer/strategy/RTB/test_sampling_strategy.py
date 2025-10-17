#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试800样本的抽样策略
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

import numpy as np
from utils.db.db_manager import DatabaseManager

def test_sampling_strategy():
    """测试抽样策略"""
    
    print("🧪 测试800样本的抽样策略")
    print("="*50)
    
    # 初始化数据库
    db = DatabaseManager()
    
    # 获取所有股票
    stock_list_table = db.get_table_instance('stock_list')
    all_stocks = stock_list_table.load_filtered_stock_list()
    total_stocks = len(all_stocks)
    
    print(f"📊 数据库总股票数: {total_stocks}")
    
    # 按行业分类
    industry_stocks = {}
    for stock in all_stocks:
        industry = stock.get('industry', '其他')
        if industry not in industry_stocks:
            industry_stocks[industry] = []
        industry_stocks[industry].append(stock)
    
    print(f"📊 行业数量: {len(industry_stocks)}")
    
    # 显示前20个最大的行业
    industry_sizes = [(industry, len(stocks)) for industry, stocks in industry_stocks.items()]
    industry_sizes.sort(key=lambda x: x[1], reverse=True)
    
    print(f"📊 前20个最大行业:")
    for i, (industry, size) in enumerate(industry_sizes[:20]):
        print(f"  {i+1:2d}. {industry}: {size}只股票")
    
    # 测试抽样策略
    target_size = 800
    selected_stocks = []
    
    # 1. 分层抽样：确保每个行业都有代表
    industry_allocations = {}
    remaining_target = target_size
    
    for industry, size in industry_sizes:
        if remaining_target <= 0:
            break
        # 每个行业最多分配 min(行业大小, 剩余目标/剩余行业数*2)
        remaining_industries = len([x for x in industry_sizes if x[0] not in industry_allocations])
        max_allocation = min(size, remaining_target // max(remaining_industries, 1) * 2)
        allocation = min(max_allocation, remaining_target)
        industry_allocations[industry] = allocation
        remaining_target -= allocation
    
    print(f"\n📊 抽样分配结果:")
    print(f"📊 分配到样本的行业数: {len([k for k, v in industry_allocations.items() if v > 0])}")
    print(f"📊 总分配样本数: {sum(industry_allocations.values())}")
    
    # 显示前20个行业的分配情况
    print(f"📊 前20个行业样本分配:")
    for i, (industry, size) in enumerate(industry_sizes[:20]):
        allocation = industry_allocations.get(industry, 0)
        if allocation > 0:
            print(f"  {i+1:2d}. {industry}: {allocation}只样本 (共{size}只股票)")
    
    # 2. 从每个行业随机选择股票
    np.random.seed(42)  # 固定随机种子
    
    for industry, allocation in industry_allocations.items():
        if allocation <= 0:
            continue
            
        stocks = industry_stocks[industry]
        np.random.shuffle(stocks)
        
        # 平衡沪深两市
        sh_stocks = [s for s in stocks if s['id'].endswith('.SH')]
        sz_stocks = [s for s in stocks if s['id'].endswith('.SZ')]
        
        # 按比例选择
        sh_count = min(len(sh_stocks), allocation // 2)
        sz_count = min(len(sz_stocks), allocation - sh_count)
        
        for i in range(sh_count):
            if len(selected_stocks) < target_size:
                selected_stocks.append(sh_stocks[i]['id'])
        
        for i in range(sz_count):
            if len(selected_stocks) < target_size:
                selected_stocks.append(sz_stocks[i]['id'])
    
    # 3. 如果还不够，完全随机补充
    if len(selected_stocks) < target_size:
        remaining_stocks = [s for s in all_stocks if s['id'] not in selected_stocks]
        np.random.shuffle(remaining_stocks)
        
        for stock in remaining_stocks:
            if len(selected_stocks) >= target_size:
                break
            selected_stocks.append(stock['id'])
    
    # 分析最终样本分布
    sz_count = sum(1 for s in selected_stocks if s.endswith('.SZ'))
    sh_count = sum(1 for s in selected_stocks if s.endswith('.SH'))
    
    print(f"\n📊 最终样本分析:")
    print(f"📊 样本总数: {len(selected_stocks)}")
    print(f"📊 深市: {sz_count}只 ({sz_count/len(selected_stocks)*100:.1f}%)")
    print(f"📊 沪市: {sh_count}只 ({sh_count/len(selected_stocks)*100:.1f}%)")
    print(f"📊 覆盖率: {len(selected_stocks)/total_stocks*100:.2f}%")
    
    # 行业分布
    sample_industry_count = {}
    for stock_id in selected_stocks:
        stock_info = next((s for s in all_stocks if s['id'] == stock_id), None)
        if stock_info:
            industry = stock_info.get('industry', '其他')
            sample_industry_count[industry] = sample_industry_count.get(industry, 0) + 1
    
    print(f"📊 样本行业分布: {len(sample_industry_count)}个行业")
    
    # 显示前15个行业在样本中的分布
    print(f"📊 样本中前15个行业分布:")
    sample_industry_sizes = [(industry, count) for industry, count in sample_industry_count.items()]
    sample_industry_sizes.sort(key=lambda x: x[1], reverse=True)
    
    for i, (industry, count) in enumerate(sample_industry_sizes[:15]):
        total_in_industry = next((size for ind, size in industry_sizes if ind == industry), 0)
        coverage = count / total_in_industry * 100 if total_in_industry > 0 else 0
        print(f"  {i+1:2d}. {industry}: {count}只样本 (行业覆盖率: {coverage:.1f}%)")
    
    # 多样性评分
    diversity_score = 0
    issues = []
    
    # 1. 样本数量评估
    if len(selected_stocks) >= 800:
        diversity_score += 1
    else:
        issues.append(f"样本数量不足({len(selected_stocks)}/800)")
    
    # 2. 市场分布评估
    if sh_count > 0 and sz_count > 0:
        diversity_score += 1
    else:
        issues.append("市场分布不均")
    
    # 3. 行业分布评估
    unique_industries = len(sample_industry_count)
    if unique_industries >= 50:
        diversity_score += 1
    else:
        issues.append(f"行业多样性不足({unique_industries}个行业)")
    
    # 4. 覆盖度评估
    coverage_rate = len(selected_stocks) / total_stocks * 100
    if coverage_rate >= 15:
        diversity_score += 1
    else:
        issues.append(f"覆盖度偏低({coverage_rate:.1f}%)")
    
    print(f"\n📊 多样性评分: {diversity_score}/4")
    
    if issues:
        print(f"⚠️ 发现的问题:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print(f"✅ 样本多样性优秀")
    
    return {
        'total_stocks': total_stocks,
        'sample_size': len(selected_stocks),
        'coverage_rate': coverage_rate,
        'diversity_score': diversity_score,
        'industry_count': len(sample_industry_count),
        'sh_ratio': sh_count / len(selected_stocks) * 100,
        'sz_ratio': sz_count / len(selected_stocks) * 100
    }

if __name__ == "__main__":
    result = test_sampling_strategy()
    
    print(f"\n🎯 抽样策略测试总结:")
    print("="*30)
    print(f"总股票数: {result['total_stocks']}")
    print(f"样本数: {result['sample_size']}")
    print(f"覆盖率: {result['coverage_rate']:.2f}%")
    print(f"行业覆盖: {result['industry_count']}个行业")
    print(f"沪深比例: 沪{result['sh_ratio']:.1f}% / 深{result['sz_ratio']:.1f}%")
    print(f"多样性评分: {result['diversity_score']}/4")
    
    if result['diversity_score'] >= 3:
        print("\n✅ 抽样策略优秀，可以开始大规模分析")
    else:
        print("\n⚠️ 抽样策略需要优化")
