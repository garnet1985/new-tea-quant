#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 stock_kline renewer
只测试10支股票，验证框架是否正常工作
"""
import sys
import os
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 抑制警告
from utils.warning_suppressor import setup_warning_suppression
setup_warning_suppression()

from utils.db.db_manager import DatabaseManager
from app.data_source.providers.tushare.renewers.stock_kline.config import CONFIG
from app.data_source.providers.tushare.renewers.stock_kline.renewer import StockKlineRenewer
import tushare as ts


def load_test_stock_list(db):
    """加载测试用的10支股票"""
    stock_list_table = db.get_table_instance('stock_list')
    
    # 先检查是否有数据
    count = stock_list_table.count()
    if count == 0:
        logger.warning("⚠️  stock_list表为空，使用硬编码的测试股票")
        # 返回硬编码的测试股票
        return [
            {'ts_code': '000001.SZ', 'id': '000001.SZ', 'name': '平安银行'},
            {'ts_code': '000002.SZ', 'id': '000002.SZ', 'name': '万科A'},
            {'ts_code': '000003.SZ', 'id': '000003.SZ', 'name': '深振业A'},
            {'ts_code': '600000.SH', 'id': '600000.SH', 'name': '浦发银行'},
            {'ts_code': '600004.SH', 'id': '600004.SH', 'name': '白云机场'},
            {'ts_code': '600006.SH', 'id': '600006.SH', 'name': '东风汽车'},
            {'ts_code': '600008.SH', 'id': '600008.SH', 'name': '首创环保'},
            {'ts_code': '600009.SH', 'id': '600009.SH', 'name': '上海机场'},
            {'ts_code': '600010.SH', 'id': '600010.SH', 'name': '包钢股份'},
            {'ts_code': '600011.SH', 'id': '600011.SH', 'name': '华能国际'},
        ]
    
    # 获取10支股票（排除北交所）
    all_stocks = stock_list_table.load_many(
        condition="exchangeCenter != 'BJ' AND isActive = 1",
        order_by="id",
        limit=10
    )
    
    if not all_stocks:
        logger.error("❌ 未找到股票数据，请先运行stock_list renewer")
        return []
    
    # 确保每个股票都有ts_code字段（如果只有id，复制id到ts_code）
    for stock in all_stocks:
        if 'ts_code' not in stock and 'id' in stock:
            stock['ts_code'] = stock['id']
    
    logger.info(f"📋 加载了 {len(all_stocks)} 支测试股票:")
    for stock in all_stocks:
        logger.info(f"  - {stock.get('ts_code')} {stock.get('name')}")
    
    return all_stocks


async def get_latest_market_open_day():
    """获取最新交易日"""
    # 简化：使用固定日期或从API获取
    from datetime import datetime, timedelta
    
    # 获取前几天的日期作为最新交易日
    today = datetime.now()
    latest = (today - timedelta(days=1)).strftime('%Y%m%d')
    
    logger.info(f"🗓️  最新交易日: {latest}")
    return latest


async def test_stock_kline_renewer():
    """测试stock_kline renewer"""
    
    # 1. 初始化数据库
    logger.info("=" * 60)
    logger.info("初始化数据库")
    logger.info("=" * 60)
    
    # 启用线程安全（支持多线程并发写入）
    db = DatabaseManager(is_verbose=True, enable_thread_safety=True)
    db.initialize()
    
    # 2. 初始化Tushare API
    logger.info("\n" + "=" * 60)
    logger.info("初始化Tushare API")
    logger.info("=" * 60)
    
    # 读取token
    with open('app/data_source/providers/tushare/auth/token.txt', 'r') as f:
        token = f.read().strip()
    
    api = ts.pro_api(token)
    
    # 3. 创建storage（虽然stock_kline可能不需要）
    from app.data_source.providers.tushare.main_storage import TushareStorage
    storage = TushareStorage(db)
    
    # 4. 创建renewer实例
    logger.info("\n" + "=" * 60)
    logger.info("创建Stock_Kline Renewer")
    logger.info("=" * 60)
    
    renewer = StockKlineRenewer(
        db=db,
        api=api,
        storage=storage,
        config=CONFIG,
        is_verbose=True
    )
    
    logger.info(f"✅ Renewer创建成功")
    logger.info(f"  - 表名: {CONFIG['table_name']}")
    logger.info(f"  - 模式: {CONFIG['job_mode']}")
    logger.info(f"  - 线程数: {CONFIG['multithread']['workers']}")
    logger.info(f"  - APIs: {[api['name'] for api in CONFIG['apis']]}")
    
    # 5. 加载测试股票列表
    logger.info("\n" + "=" * 60)
    logger.info("加载测试股票列表")
    logger.info("=" * 60)
    
    test_stocks = load_test_stock_list(db)
    
    if not test_stocks:
        logger.error("❌ 无法加载测试股票")
        return
    
    # 6. 获取最新交易日
    latest_market_open_day = await get_latest_market_open_day()
    
    # 7. 执行更新
    logger.info("\n" + "=" * 60)
    logger.info("开始更新Stock_Kline数据")
    logger.info("=" * 60)
    logger.info(f"📅 截止日期: {latest_market_open_day}")
    logger.info(f"📊 股票数量: {len(test_stocks)}")
    logger.info(f"📈 Term数量: 3 (daily/weekly/monthly)")
    logger.info(f"🔢 预计任务数: {len(test_stocks) * 3} (可能更少，取决于是否需要更新)")
    
    try:
        result = renewer.renew(latest_market_open_day, test_stocks)
        
        logger.info("\n" + "=" * 60)
        if result:
            logger.info("✅ 更新成功！")
        else:
            logger.info("⚠️  更新完成，但部分任务可能失败")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"\n❌ 更新失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # 8. 验证数据
    logger.info("\n" + "=" * 60)
    logger.info("验证保存的数据")
    logger.info("=" * 60)
    
    table = db.get_table_instance('stock_kline')
    
    # 检查每个term的数据量
    for term in ['daily', 'weekly', 'monthly']:
        count = table.count(f"term = '{term}'")
        logger.info(f"  - {term}: {count} 条记录")
    
    # 显示第一支股票的最新数据
    if test_stocks:
        first_stock = test_stocks[0]['ts_code']
        logger.info(f"\n📊 股票 {first_stock} 的最新数据:")
        
        for term in ['daily', 'weekly', 'monthly']:
            latest = table.load_one(
                f"id = '{first_stock}' AND term = '{term}'",
                order_by="date DESC"
            )
            if latest:
                logger.info(f"  - {term}: {latest.get('date')} close={latest.get('close')} pe={latest.get('pe')}")
            else:
                logger.info(f"  - {term}: 无数据")
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ 测试完成！")
    logger.info("=" * 60)


if __name__ == '__main__':
    import asyncio
    asyncio.run(test_stock_kline_renewer())

