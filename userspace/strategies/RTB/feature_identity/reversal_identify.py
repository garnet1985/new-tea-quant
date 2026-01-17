#!/usr/bin/env python3
"""
反转点识别模块

实现月线+周线分层识别方法：
1. 加载整个时间的月K线数据
2. 在月K线数据上找到波谷（使用现有的find_valleys方法）
3. 记录这些反转点然后在周线上遍历它们
4. 在遍历周线的反转点时在两边各加一些K线，然后找到最准确的最低点
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from loguru import logger
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.append(str(project_root))

from core.modules.analyzer.analyzer_service import AnalyzerService
from core.infra.project_context import ConfigManager


def identify_major_reversals(stock_id: str = "000001.SZ", 
                           start_date: str = None, 
                           end_date: str = None) -> List[Dict[str, Any]]:
    """
    识别重大反转点的主函数
    
    Args:
        stock_id: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        
    Returns:
        List[Dict]: 重大反转点列表
    """
    logger.info(f"🎯 开始识别 {stock_id} 重大反转点（分层识别版本）")
    
    # 设置默认日期
    if start_date is None:
        start_date = ConfigManager.get_default_start_date()
    if end_date is None:
        end_date = "20241231"
    
    try:
        # 初始化数据加载器
        from core.infra.db import DatabaseManager
        from core.modules.data_manager import DataManager
        
        data_mgr = DataManager()
        
        # 第一步：加载整个时间的月K线数据
        logger.info("📊 第一步：加载月K线数据")
        monthly_klines = data_mgr.stock.kline.load_qfq(stock_id, 'monthly', start_date, end_date)
        if monthly_klines:
            monthly_klines = []
        
        if len(monthly_klines) < 12:
            logger.error(f"❌ 月线数据不足: {len(monthly_klines)} 条")
            return []
        
        logger.info(f"✅ 成功加载 {len(monthly_klines)} 条月线数据")
        
        # 第二步：在月K线数据上找到波谷
        logger.info("🔍 第二步：在月线数据上找到波谷")
        monthly_valleys = find_monthly_valleys(monthly_klines)
        
        if not monthly_valleys:
            logger.warning("⚠️ 未找到月线波谷")
            return []
        
        logger.info(f"✅ 识别出 {len(monthly_valleys)} 个月线波谷")
        
        # 第三步：在周线上精确定位反转点
        logger.info("🎯 第三步：在周线上精确定位反转点")
        weekly_klines = kline_loader.load_weekly_qfq(stock_id, start_date, end_date)
        
        if len(weekly_klines) < 100:
            logger.error(f"❌ 周线数据不足: {len(weekly_klines)} 条")
            return []
        
        logger.info(f"✅ 成功加载 {len(weekly_klines)} 条周线数据")
        
        # 第四步：遍历月线波谷，在周线上找到最准确的最低点
        major_reversals = find_precise_reversals_from_valleys(weekly_klines, monthly_valleys)
        
        logger.info(f"✅ 最终识别出 {len(major_reversals)} 个重大反转点")
        
        return major_reversals
        
    except Exception as e:
        logger.error(f"❌ 识别失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def find_monthly_valleys(monthly_klines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    在月K线数据上找到波谷（使用现有的find_valleys方法）
    
    Args:
        monthly_klines: 月K线数据列表
        
    Returns:
        List[Dict]: 月线波谷列表
    """
    
    # 使用现有的find_valleys方法
    # 参数调整：min_drop_threshold=0.20 (20%跌幅), local_range_days=2 (左右2个月), lookback_days=18 (前18个月)
    valleys = AnalyzerService.find_valleys(
        daily_data=monthly_klines,
        min_drop_threshold=0.20,  # 最小20%跌幅（降低阈值包含2020年3月）
        local_range_days=2,       # 左右2个月范围
        lookback_days=18          # 前18个月内找峰值（扩大窗口）
    )
    
    # 过滤和排序波谷
    filtered_valleys = []
    for valley in valleys:
        # 确保跌幅足够大
        if valley['drop_rate'] >= 0.20:
            filtered_valleys.append({
                'date': valley['date'],
                'price': valley['price'],
                'drop_rate': valley['drop_rate'],
                'left_peak': valley['left_peak'],
                'left_peak_date': valley['left_peak_date'],
                'monthly_record': valley['record']
            })
    
    # 按日期排序
    filtered_valleys.sort(key=lambda x: x['date'])
    
    logger.info(f"✅ 月线波谷识别完成，共找到 {len(filtered_valleys)} 个波谷")

    return filtered_valleys


def find_precise_reversals_from_valleys(weekly_klines: List[Dict[str, Any]], 
                                       monthly_valleys: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    遍历月线波谷，在周线上找到最准确的最低点
    
    Args:
        weekly_klines: 周K线数据列表
        monthly_valleys: 月线波谷列表
        
    Returns:
        List[Dict]: 精确的重大反转点列表
    """
    
    major_reversals = []
    
    for i, valley in enumerate(monthly_valleys, 1):
        valley_date = valley['date']
        # logger.info(f"🔍 处理月线波谷 #{i}: {valley_date}")
        
        # 在月线波谷附近±3个月范围内搜索周线数据
        search_range_weeks = 24  # 约6个月
        
        # 找到月线波谷对应的周线数据位置
        valley_week_index = find_week_index_by_date(weekly_klines, valley_date)
        
        if valley_week_index is None:
            logger.warning(f"⚠️ 未找到月线波谷 {valley_date} 对应的周线数据")
            continue
        
        # 在波谷前后搜索范围
        search_start = max(0, valley_week_index - search_range_weeks)
        search_end = min(len(weekly_klines), valley_week_index + search_range_weeks)
        
        # 在搜索范围内找到最准确的最低点
        search_data = weekly_klines[search_start:search_end]
        # logger.info(f"   搜索范围: {len(search_data)} 条周线数据")
        
        precise_reversal = find_most_precise_reversal_in_range(search_data, valley)
        
        if precise_reversal:
            major_reversals.append(precise_reversal)
            # logger.info(f"✅ 找到精确反转点: {precise_reversal['date']}, "
            #            f"价格: {precise_reversal['price']:.2f}, "
            #            f"收益: {precise_reversal['reversal_gain']:.1%}")
    
    logger.info(f"✅ 精确反转点识别完成，共找到 {len(major_reversals)} 个反转点")
    return major_reversals


def find_week_index_by_date(weekly_klines: List[Dict[str, Any]], target_date: str) -> Optional[int]:
    """
    根据日期找到对应的周线数据索引
    
    Args:
        weekly_klines: 周K线数据列表
        target_date: 目标日期
        
    Returns:
        Optional[int]: 对应的索引，如果没找到返回None
    """
    # 处理不同的日期格式
    if len(target_date) == 8:  # YYYYMMDD格式
        target_dt = datetime.strptime(target_date, '%Y%m%d')
    else:  # YYYY-MM-DD格式
        target_dt = datetime.strptime(target_date, '%Y-%m-%d')
    
    for i, kline in enumerate(weekly_klines):
        # 处理周线数据的日期格式
        if len(kline['date']) == 8:  # YYYYMMDD格式
            kline_dt = datetime.strptime(kline['date'], '%Y%m%d')
        else:  # YYYY-MM-DD格式
            kline_dt = datetime.strptime(kline['date'], '%Y-%m-%d')
        
        # 找到最接近的周线数据
        if abs((kline_dt - target_dt).days) <= 7:  # 一周内
            return i
    
    return None


def find_most_precise_reversal_in_range(search_klines: List[Dict[str, Any]], 
                                       valley_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    在指定范围内找到最准确的反转点
    
    Args:
        search_klines: 搜索范围内的周K线数据
        valley_info: 月线波谷信息
        
    Returns:
        Optional[Dict]: 最准确的反转点信息
    """
    if len(search_klines) < 10:
        return None
    
    best_reversal = None
    best_score = 0
    
    # logger.info(f"   在 {len(search_klines)} 条周线中搜索反转点...")
    
    # 在搜索范围内寻找最佳反转点
    min_future_weeks = min(10, len(search_klines) // 3)  # 动态调整未来周数
    for i in range(5, len(search_klines) - min_future_weeks):  # 确保有足够的历史和未来数据
        current_date = search_klines[i]['date']
        current_price = search_klines[i]['close']
        
        # 计算未来收益
        future_weeks = min(20, len(search_klines) - i - 1)  # 动态调整未来周数
        future_data = search_klines[i+1:i+1+future_weeks]
        if len(future_data) == 0:
            continue
            
        # 尝试不同的字段名
        high_prices = []
        for k in future_data:
            if 'high' in k:
                high_prices.append(k['high'])
            elif 'highest' in k:
                high_prices.append(k['highest'])
            else:
                # 如果没有high字段，使用close价格
                high_prices.append(k['close'])
        
        max_future_price = max(high_prices) if high_prices else current_price
        reversal_gain = (max_future_price - current_price) / current_price
        
        # 计算技术指标得分（基于价格位置和技术形态，不考虑收益）
        score = calculate_reversal_score(search_klines[i], reversal_gain, valley_info)
        
        # 选择得分最高的反转点（基于技术形态，不限制收益）
        if score > best_score:
            best_score = score
            best_reversal = {
                'date': current_date,
                'price': current_price,
                'reversal_gain': reversal_gain,
                'reversal_duration': len(future_data),
                'max_future_price': max_future_price,
                'monthly_valley_date': valley_info['date'],
                'monthly_drop_rate': valley_info['drop_rate'],
                'score': score,
                'technical_indicators': {
                    'rsi': calculate_rsi_for_week(search_klines, i),
                    'volatility': calculate_volatility_for_week(search_klines, i),
                    'price_position': calculate_price_position(search_klines, i)
                }
            }
    
    return best_reversal


def calculate_reversal_score(week_data: Dict[str, Any], reversal_gain: float, 
                           valley_info: Dict[str, Any]) -> float:
    """
    计算反转点得分（基于视觉上的大波谷识别）
    
    Args:
        week_data: 当前周的数据
        reversal_gain: 反转收益（仅用于记录，不作为评分标准）
        valley_info: 月线波谷信息
        
    Returns:
        float: 反转点得分（0-100）
    """
    score = 0
    
    # 1. 价格位置得分（相对月线波谷）- 最重要的指标
    price_ratio = week_data['close'] / valley_info['price']
    if 0.95 <= price_ratio <= 1.05:  # 非常接近月线波谷价格
        score += 40
    elif 0.90 <= price_ratio <= 1.10:  # 接近月线波谷价格
        score += 30
    elif 0.85 <= price_ratio <= 1.15:  # 相对接近
        score += 20
    elif 0.80 <= price_ratio <= 1.20:  # 还算接近
        score += 10
    
    # 2. 月线波谷跌幅得分（跌幅越大，反转点越重要）
    if valley_info['drop_rate'] >= 0.50:
        score += 25
    elif valley_info['drop_rate'] >= 0.40:
        score += 20
    elif valley_info['drop_rate'] >= 0.30:
        score += 15
    elif valley_info['drop_rate'] >= 0.20:
        score += 10
    
    # 3. 价格在历史分位数中的位置（越低越好）
    price_position = calculate_price_position([week_data], 0)
    if price_position <= 0.05:  # 历史最低5%
        score += 20
    elif price_position <= 0.10:  # 历史最低10%
        score += 15
    elif price_position <= 0.15:  # 历史最低15%
        score += 10
    elif price_position <= 0.20:  # 历史最低20%
        score += 5
    
    # 4. RSI超卖得分
    rsi = calculate_rsi_for_week([week_data], 0)
    if rsi <= 20:  # 极度超卖
        score += 15
    elif rsi <= 30:  # 超卖
        score += 10
    elif rsi <= 40:  # 相对超卖
        score += 5
    
    return score


def calculate_rsi_for_week(weekly_klines: List[Dict[str, Any]], index: int) -> float:
    """计算RSI指标"""
    if index < 14:
        return 50.0  # 默认值
    
    prices = [k['close'] for k in weekly_klines[max(0, index-14):index+1]]
    
    if len(prices) < 2:
        return 50.0
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(-change)
    
    if not gains or not losses:
        return 50.0
    
    avg_gain = sum(gains) / len(gains)
    avg_loss = sum(losses) / len(losses)
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_volatility_for_week(weekly_klines: List[Dict[str, Any]], index: int) -> float:
    """计算波动率"""
    if index < 20:
        return 0.03  # 默认值
    
    prices = [k['close'] for k in weekly_klines[max(0, index-20):index+1]]
    
    if len(prices) < 2:
        return 0.03
    
    returns = []
    for i in range(1, len(prices)):
        ret = (prices[i] - prices[i-1]) / prices[i-1]
        returns.append(ret)
    
    if not returns:
        return 0.03
    
    return np.std(returns)


def calculate_price_position(weekly_klines: List[Dict[str, Any]], index: int) -> float:
    """计算价格在历史数据中的位置（分位数）"""
    if index < 52:  # 1年数据
        return 0.5  # 默认值
    
    current_price = weekly_klines[index]['close']
    historical_prices = [k['close'] for k in weekly_klines[max(0, index-52):index]]
    
    if not historical_prices:
        return 0.5
    
    rank = sum(1 for p in historical_prices if p < current_price)
    percentile = rank / len(historical_prices)
    
    return percentile


def save_reversal_results(reversals: List[Dict[str, Any]], stock_id: str):
    """保存反转点结果"""
    if not reversals:
        logger.warning("⚠️ 没有找到重大反转点，不保存结果")
        return
    
    # 保存为JSON格式
    json_file = f"app/core/modules/analyzer/strategy/RTB/ml/precise_reversals_{stock_id}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(reversals, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 结果已保存到: {json_file}")
    
    # 保存为CSV格式
    df = pd.DataFrame(reversals)
    csv_file = f"app/core/modules/analyzer/strategy/RTB/ml/precise_reversals_{stock_id}.csv"
    df.to_csv(csv_file, index=False, encoding='utf-8')
    logger.info(f"💾 结果已保存到: {csv_file}")


def display_reversal_results(reversals: List[Dict[str, Any]]):
    """显示识别结果"""
    if not reversals:
        logger.warning("⚠️ 没有找到重大反转点")
        return
    
    logger.info("🎯 重大反转点识别结果:")
    logger.info("=" * 60)
    
    for i, reversal in enumerate(reversals, 1):
        logger.info(f"{i:2d}. {reversal['date']} | "
                   f"价格: {reversal['price']:6.2f} | "
                   f"收益: {reversal['reversal_gain']:5.1%} | "
                   f"持续: {reversal['reversal_duration']:2d}周 | "
                   f"得分: {reversal['score']:4.1f}")
    
    # 统计信息
    gains = [r['reversal_gain'] for r in reversals]
    durations = [r['reversal_duration'] for r in reversals]
    scores = [r['score'] for r in reversals]
    
    logger.info("=" * 60)
    logger.info(f"📊 统计信息:")
    logger.info(f"   反转点数量: {len(reversals)}")
    logger.info(f"   平均收益: {np.mean(gains):.1%}")
    logger.info(f"   平均持续时间: {np.mean(durations):.1f}周")
    logger.info(f"   平均得分: {np.mean(scores):.1f}")
    logger.info(f"   收益范围: {np.min(gains):.1%} - {np.max(gains):.1%}")


if __name__ == "__main__":
    # 测试函数
    reversals = identify_major_reversals()
    
    if reversals:
        save_reversal_results(reversals, "000001.SZ")
        display_reversal_results(reversals)
    else:
        logger.warning("⚠️ 未找到任何重大反转点")
