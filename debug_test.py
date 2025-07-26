#!/usr/bin/env python3
"""
Debug测试文件 - 验证代码是否生效
"""
import sys
import os
from loguru import logger
from app.data_source.providers.tushare.query import TushareQuery

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_tushare_renew():
    """测试Tushare股票数据更新功能"""
    try:
        logger.info("🚀 开始测试股票数据更新功能...")
        
        # 创建TushareQuery实例
        query = TushareQuery()
        logger.info(f"📅 最后市场开放日: {query.last_market_open_day}")
        
        # 测试股票数据更新
        if query.renew_stock_index():
            logger.success("🎉 股票数据更新测试成功！")
        else:
            logger.error("❌ 股票数据更新测试失败！")
            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tushare_renew()



# def test_token_reading():
#     """测试token读取机制"""
#     try:
#         from crawler.providers.tushare.query import TushareQuery
        
#         query = TushareQuery()
#         token = query.token
        
#         logger.success(f"✅ Token读取成功: {token[:10]}...")
#         logger.info(f"Token长度: {len(token)} 字符")
#         return True
#     except FileNotFoundError as e:
#         logger.error(f"❌ Token文件未找到: {e}")
#         return False
#     except Exception as e:
#         logger.error(f"❌ Token读取失败: {e}")
#         return False

# def test_tushare_settings():
#     """测试Tushare设置导入"""
#     try:
#         from crawler.providers.tushare.settings import (
#             auth_token, start_date, end_date, STOCK_BASIC_FIELDS
#         )
        
#         logger.success(f"✅ Tushare设置导入成功")
#         logger.info(f"Token文件路径: {auth_token}")
#         logger.info(f"日期范围: {start_date} - {end_date}")
#         logger.info(f"股票基础字段: {STOCK_BASIC_FIELDS}")
#         return True
#     except Exception as e:
#         logger.error(f"❌ Tushare设置导入失败: {e}")
#         return False

# def test_file_structure():
#     """测试文件结构"""
#     try:
#         token_file = 'crawler/providers/tushare/auth/token.txt'
#         example_file = 'crawler/providers/tushare/auth/token.example.txt'
#         readme_file = 'crawler/providers/tushare/auth/README.md'
        
#         files_exist = []
#         for file_path in [token_file, example_file, readme_file]:
#             if os.path.exists(file_path):
#                 files_exist.append(f"✅ {file_path}")
#             else:
#                 files_exist.append(f"❌ {file_path}")
        
#         logger.success("✅ 文件结构检查完成")
#         for status in files_exist:
#             logger.info(status)
#         return True
#     except Exception as e:
#         logger.error(f"❌ 文件结构检查失败: {e}")
#         return False

