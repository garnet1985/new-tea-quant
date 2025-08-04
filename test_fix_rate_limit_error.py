#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from loguru import logger
import asyncio

# 在导入其他模块之前设置警告抑制
from utils.warning_suppressor import setup_warning_suppression
setup_warning_suppression()

from utils.db.db_manager import get_sync_db_manager
from app.data_source.data_source_manager import DataSourceManager

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_fix_rate_limit_error():
    """测试修复_rate_limit错误"""
    print("=== 测试修复_rate_limit错误 ===")
    
    try:
        # 初始化数据源管理器
        db = get_sync_db_manager()
        dsm = DataSourceManager(db, is_verbose=True)
        
        # 测试renew_data方法，这会调用Tushare的fetch_kline_data
        print("测试renew_data方法...")
        await dsm.renew_data()
        
        print("✅ 修复测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fix_rate_limit_error()) 