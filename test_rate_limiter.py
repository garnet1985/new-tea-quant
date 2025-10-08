"""
测试限流功能

测试场景：
1. 直接测试RateLimiter
2. 多线程模式限流
"""

import sys
import time
from loguru import logger

from utils.db.db_manager import DatabaseManager

# 配置logger
logger.remove()
logger.add(sys.stderr, level="INFO")

from app.data_source.providers.tushare.rate_limiter import APIRateLimiter


def test_rate_limiter_direct():
    """直接测试APIRateLimiter"""
    logger.info("=" * 60)
    logger.info("测试1: 直接测试APIRateLimiter")
    logger.info("=" * 60)
    logger.info("配置: 20次/分钟，buffer=0.9")
    
    # 创建限流器：20次/分钟，buffer=2（实际限流18次/分钟）
    rate_limiter = APIRateLimiter(max_per_minute=20, api_name='test_api', buffer=2)
    
    logger.info(f"  - 限流配置: {rate_limiter.max_per_minute}次/分钟")
    logger.info(f"  - Buffer: {rate_limiter.buffer}次")
    logger.info(f"  - 实际限流: {rate_limiter.actual_limit}次/分钟")
    
    # 记录开始时间
    start_time = time.time()
    
    # 连续调用25次（超过限流20次）
    logger.info(f"\n🔄 开始连续调用25次...")
    
    for i in range(25):
        call_start = time.time()
        
        # 获取令牌
        rate_limiter.acquire()
        
        call_end = time.time()
        call_duration = call_end - call_start
        elapsed = call_end - start_time
        
        if call_duration > 0.1:
            logger.warning(f"  调用 {i+1:2d}: 等待 {call_duration:.2f}秒 (总耗时 {elapsed:.2f}秒) ⏳ 被限流")
        else:
            logger.info(f"  调用 {i+1:2d}: 立即执行 (总耗时 {elapsed:.2f}秒)")
    
    total_time = time.time() - start_time
    
    actual_limit = rate_limiter.actual_limit  # 18次/分钟
    
    logger.info(f"\n📊 统计结果:")
    logger.info(f"  - 总调用次数: 25次")
    logger.info(f"  - 总耗时: {total_time:.2f}秒")
    logger.info(f"  - 平均每次: {total_time / 25:.3f}秒")
    logger.info(f"  - 限流配置: {rate_limiter.max_per_minute}次/分钟")
    logger.info(f"  - 实际限流: {actual_limit}次/分钟")
    logger.info(f"  - Buffer: {rate_limiter.buffer}次")
    
    # 验证限流：前18次应该快速通过，后7次需要等待
    # 预期：前18次立即执行，19-25需要在第二分钟执行
    expected_min_time = 60  # 至少需要60秒（跨越两个分钟）
    if total_time < expected_min_time * 0.9:
        logger.error(f"❌ 限流可能未生效！总耗时 {total_time:.2f}秒 < 预期 {expected_min_time:.2f}秒")
    else:
        logger.success(f"✅ 限流正常！符合预期（超出{actual_limit}次后等待下一分钟）")


def test_multithread_mode_rate_limit():
    """测试多线程模式限流"""
    logger.info("\n" + "=" * 60)
    logger.info("测试2: 多线程模式限流")
    logger.info("=" * 60)
    logger.info("配置: 20次/分钟，6个worker，buffer=0.7（自动调整）")
    
    # 初始化数据库
    db = DatabaseManager(is_verbose=False, enable_thread_safety=True)
    db.initialize()
    
    # 读取token
    with open('app/data_source/providers/tushare/auth/token.txt', 'r') as f:
        token = f.read().strip()
    
    # 读取测试股票列表
    stock_list_table = db.get_table_instance('stock_list')
    stock_list = stock_list_table.read(
        filters={'exchangeCenter': 'SSE'},
        limit=10  # 只测试10只股票
    )
    
    logger.info(f"📋 加载了 {len(stock_list)} 只测试股票")
    
    # 创建stock_kline renewer（多线程模式）
    from app.data_source.providers.tushare.renewers.stock_kline.config import CONFIG as KLINE_CONFIG
    from app.data_source.providers.tushare.renewers.stock_kline.renewer import StockKlineRenewer
    
    # 修改配置：限流20次/分钟
    test_config = KLINE_CONFIG.copy()
    test_config['rate_limit'] = {
        'max_per_minute': 20
    }
    # 修改日志避免刷屏
    test_config['multithread']['log'] = {}  # 不输出日志
    
    renewer = StockKlineRenewer(db, token, test_config)
    
    logger.info(f"\n🔄 开始多线程更新（6个worker）...")
    logger.info(f"  - 预计任务数: ~30个 (10只股票 × 3个term)")
    logger.info(f"  - 每个任务需要2次API调用")
    logger.info(f"  - 总API调用: ~60次")
    logger.info(f"  - 限流: 20次/分钟")
    logger.info(f"  - 预期耗时: ~120秒（60次调用需要3分钟）")
    
    # 记录开始时间
    start_time = time.time()
    
    # 执行更新
    renewer.renew(latest_market_open_day='20251007', stock_list=stock_list)
    
    total_time = time.time() - start_time
    
    logger.info(f"\n📊 统计结果:")
    logger.info(f"  - 总耗时: {total_time:.2f}秒")
    logger.info(f"  - 限流配置: 20次/分钟，buffer=0.7")
    logger.info(f"  - 实际限流: {20 * 0.7:.1f}次/分钟")
    
    if total_time < 60:
        logger.warning(f"⚠️  耗时较短，可能任务量不足或有缓存")
    else:
        logger.success(f"✅ 多线程限流正常工作！")


if __name__ == "__main__":
    try:
        # 测试1：直接测试RateLimiter
        test_rate_limiter_direct()
        
        # 等待一会儿，让限流器恢复
        logger.info("\n⏳ 等待30秒，让限流器恢复...")
        time.sleep(30)
        
        # 测试2：多线程模式限流
        test_multithread_mode_rate_limit()
        
        logger.info("\n" + "=" * 60)
        logger.success("✅ 所有限流测试完成！")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
