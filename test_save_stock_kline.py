#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from loguru import logger
from utils.db.db_manager import get_sync_db_manager
from app.data_source.providers.tushare.storage import TushareStorage

def test_save_stock_kline():
    """测试 save_stock_kline 函数"""
    logger.info("开始测试 save_stock_kline 函数")
    
    try:
        # 初始化数据库连接
        db = get_sync_db_manager()
        db.initialize()
        
        # 初始化存储类
        storage = TushareStorage(db)
        
        # 创建模拟的K线数据
        mock_data = pd.DataFrame([
            {
                'ts_code': '000001.SZ',
                'trade_date': '20250725',
                'open': 12.50,
                'close': 12.80,
                'high': 12.95,
                'low': 12.45,
                'change': 0.30,
                'pct_chg': 2.40,
                'pre_close': 12.50,
                'vol': 1500000,
                'amount': 19000000.00
            },
            {
                'ts_code': '000001.SZ',
                'trade_date': '20250726',
                'open': 12.80,
                'close': 13.10,
                'high': 13.25,
                'low': 12.75,
                'change': 0.30,
                'pct_chg': 2.34,
                'pre_close': 12.80,
                'vol': 1600000,
                'amount': 20800000.00
            }
        ])
        
        # 创建模拟的job信息
        mock_job = {
            'code': '000001',
            'market': 'SZ',
            'term': 'daily',
            'start_date': '20250725',
            'end_date': '20250726'
        }
        
        logger.info("模拟数据:")
        logger.info(f"数据形状: {mock_data.shape}")
        logger.info(f"Job信息: {mock_job}")
        
        # 调用保存函数
        storage.save_stock_kline(mock_data, mock_job)
        
        # 验证数据是否保存成功
        stock_kline_table = db.get_table_instance('stock_kline', 'base')
        saved_data = stock_kline_table.find_many(
            "code = %s AND market = %s AND term = %s", 
            ('000001', 'SZ', 'daily')
        )
        
        logger.info(f"保存的数据条数: {len(saved_data)}")
        if saved_data:
            logger.info("保存的数据示例:")
            for i, record in enumerate(saved_data[:2]):
                logger.info(f"  记录 {i+1}: {record}")
        
        logger.info("✅ save_stock_kline 测试完成")
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        raise

if __name__ == "__main__":
    test_save_stock_kline() 