"""
Test Database Models
"""
import os
import sys
from loguru import logger

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from crawler.db import (
    stock_index_model,
    stock_kline_model,
    stock_detail_model,
    industry_index_model,
    industry_kline_model,
    industry_stock_map_model,
    macro_economics_model,
    real_estate_model,
    hl_opportunity_history_model,
    hl_stock_summary_model,
    hl_meta_model
)


def test_stock_models():
    """测试股票相关模型"""
    logger.info("Testing stock models...")
    
    try:
        # 测试股票指数模型
        stocks = stock_index_model.get_all_stocks()
        logger.info(f"Found {len(stocks)} stocks")
        
        if stocks:
            # 测试获取单个股票
            first_stock = stocks[0]
            stock = stock_index_model.get_stock_by_code(first_stock['code'])
            logger.info(f"Stock info: {stock['name']} ({stock['code']})")
            
            # 测试K线数据
            klines = stock_kline_model.get_stock_kline_data(
                first_stock['code'], 
                term='daily', 
                limit=5
            )
            logger.info(f"Found {len(klines)} kline records")
            
            # 测试股票详情
            detail = stock_detail_model.get_stock_detail(first_stock['code'])
            if detail:
                logger.info(f"Stock detail: PE={detail.get('dynamicPE', 'N/A')}")
        
        logger.success("Stock models test completed")
        return True
        
    except Exception as e:
        logger.error(f"Stock models test failed: {e}")
        return False


def test_industry_models():
    """测试行业相关模型"""
    logger.info("Testing industry models...")
    
    try:
        # 测试行业指数模型
        industries = industry_index_model.get_all_industries()
        logger.info(f"Found {len(industries)} industries")
        
        if industries:
            # 测试行业K线数据
            first_industry = industries[0]
            klines = industry_kline_model.get_industry_kline_data(
                first_industry['code'], 
                term='daily', 
                limit=5
            )
            logger.info(f"Found {len(klines)} industry kline records")
            
            # 测试行业股票映射
            stocks = industry_stock_map_model.get_stocks_by_industry(first_industry['code'])
            logger.info(f"Found {len(stocks)} stocks in industry {first_industry['name']}")
        
        logger.success("Industry models test completed")
        return True
        
    except Exception as e:
        logger.error(f"Industry models test failed: {e}")
        return False


def test_macro_models():
    """测试宏观经济模型"""
    logger.info("Testing macro economics models...")
    
    try:
        # 测试宏观经济数据
        macro_data = macro_economics_model.find_many(limit=5)
        logger.info(f"Found {len(macro_data)} macro economics records")
        
        # 测试房地产数据
        real_estate_data = real_estate_model.find_many(limit=5)
        logger.info(f"Found {len(real_estate_data)} real estate records")
        
        logger.success("Macro models test completed")
        return True
        
    except Exception as e:
        logger.error(f"Macro models test failed: {e}")
        return False


def test_strategy_models():
    """测试策略模型"""
    logger.info("Testing strategy models...")
    
    try:
        # 测试历史低点策略机会
        opportunities = hl_opportunity_history_model.find_many(limit=5)
        logger.info(f"Found {len(opportunities)} HL opportunities")
        
        # 测试股票汇总
        summaries = hl_stock_summary_model.find_many(limit=5)
        logger.info(f"Found {len(summaries)} HL stock summaries")
        
        # 测试元数据
        meta_data = hl_meta_model.find_many(limit=5)
        logger.info(f"Found {len(meta_data)} HL meta records")
        
        logger.success("Strategy models test completed")
        return True
        
    except Exception as e:
        logger.error(f"Strategy models test failed: {e}")
        return False


def test_data_operations():
    """测试数据操作"""
    logger.info("Testing data operations...")
    
    try:
        # 测试查询操作
        stocks = stock_index_model.find_many("market = 1", limit=10)
        logger.info(f"Found {len(stocks)} stocks in market 1")
        
        # 测试统计操作
        total_stocks = stock_index_model.count()
        logger.info(f"Total stocks: {total_stocks}")
        
        # 测试条件查询
        if stocks:
            first_stock = stocks[0]
            klines_count = stock_kline_model.count("code = %s AND term = 'daily'", (first_stock['code'],))
            logger.info(f"Kline records for {first_stock['code']}: {klines_count}")
        
        logger.success("Data operations test completed")
        return True
        
    except Exception as e:
        logger.error(f"Data operations test failed: {e}")
        return False


if __name__ == "__main__":
    logger.info("Starting model tests...")
    
    tests = [
        test_stock_models,
        test_industry_models,
        test_macro_models,
        test_strategy_models,
        test_data_operations
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    logger.info(f"Tests completed: {passed}/{total} passed")
    
    if passed == total:
        logger.success("All tests passed!")
        sys.exit(0)
    else:
        logger.error("Some tests failed!")
        sys.exit(1) 