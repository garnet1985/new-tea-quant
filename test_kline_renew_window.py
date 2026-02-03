"""
测试脚本：分析特定股票的 renew 时间窗口

用于诊断为什么某些股票的3个API都返回空数据
"""
from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
from core.modules.data_source.service.renew.renew_common_helper import RenewCommonHelper
from core.modules.data_source.data_class.config import DataSourceConfig
from core.modules.data_manager.data_manager import DataManager
from core.utils.date.date_utils import DateUtils
from loguru import logger
import sys

# 要测试的股票列表（从日志中看到的返回空数据的股票）
TEST_STOCKS = ["000001.SZ", "000002.SZ", "000004.SZ", "000006.SZ", "000007.SZ", "000008.SZ", "000009.SZ", "000010.SZ", "000012.SZ"]

def test_stock_renew_window(stock_id: str, config: DataSourceConfig, data_manager: DataManager):
    """测试单个股票的 renew 时间窗口"""
    logger.info(f"\n{'='*80}")
    logger.info(f"测试股票: {stock_id}")
    logger.info(f"{'='*80}")
    
    # 1. 查询该股票的 last_update（每个 term）
    from core.modules.data_source.service.renew.renew_common_helper import RenewCommonHelper
    
    # 构建查询条件
    context = {
        "config": config,
        "data_manager": data_manager,
    }
    
    # 查询 latest_trading_date
    latest_trading_date = data_manager.service.calendar.get_latest_completed_trading_date()
    logger.info(f"最新交易日: {latest_trading_date}")
    
    # 查询该股票的 last_update（每个 term）
    terms = ["daily", "weekly", "monthly"]
    last_update_map = {}
    
    for term in terms:
        composite_key = f"{stock_id}::{term}"
        # 查询该 term 的最新日期
        from core.modules.data_source.service.handler_helper import DataSourceHandlerHelper
        
        # 使用 load_latests 查询
        schema = data_manager.get_schema("sys_stock_klines")
        if not schema:
            logger.error(f"无法获取 schema: sys_stock_klines")
            return
        
        # 构建查询条件
        conditions = {
            "id": stock_id,
            "term": term
        }
        
        # 查询最新记录
        records = data_manager.load_latests(
            schema=schema,
            conditions=conditions,
            group_by=["id", "term"],
            order_by={"date": "desc"},
            limit=1
        )
        
        if records and len(records) > 0:
            last_update = records[0].get("date")
            last_update_map[composite_key] = last_update
            logger.info(f"  {term}: last_update = {last_update}")
        else:
            logger.info(f"  {term}: 没有找到记录（新股票）")
            last_update_map[composite_key] = None
    
    # 2. 计算 renew 时间窗口
    logger.info(f"\n计算 renew 时间窗口:")
    
    # 获取 end_date（最新交易日）
    end_date = latest_trading_date
    
    # 获取 start_date（根据 renew_mode）
    renew_mode = config.get_renew_mode()
    logger.info(f"renew_mode: {renew_mode}")
    
    # 计算每个 term 的日期范围
    for term in terms:
        composite_key = f"{stock_id}::{term}"
        last_update = last_update_map.get(composite_key)
        
        logger.info(f"\n  {term} ({composite_key}):")
        logger.info(f"    last_update: {last_update}")
        
        if not last_update:
            # 新股票，使用默认 start_date
            default_start_date = config.get_default_start_date()
            logger.info(f"    新股票，使用 default_start_date: {default_start_date}")
            start_date = default_start_date
        else:
            # 根据 renew_mode 计算 start_date
            if renew_mode == "incremental":
                # 增量模式：从 last_update 的下一个交易日开始
                start_date = DateUtils.get_next_trading_date(last_update)
            else:
                # 全量模式：使用 default_start_date
                start_date = config.get_default_start_date()
            
            logger.info(f"    计算得到 start_date: {start_date}")
        
        # 计算 term_end_date（对于 weekly/monthly）
        term_end_date = end_date
        
        if term in ["weekly", "monthly"]:
            # 检查完整周期是否已过
            if last_update:
                period_end = DateUtils.get_period_end(last_update, term)
                if period_end:
                    logger.info(f"    last_update 所在周期的结束日期: {period_end}")
                    
                    if DateUtils.is_before(latest_trading_date, period_end):
                        logger.info(f"    ⚠️ 周期未完整结束，跳过更新")
                        term_end_date = None
                    else:
                        # 计算上一周期的结束日期
                        prev_period_end = DateUtils.get_previous_period_end(latest_trading_date, term)
                        if prev_period_end:
                            logger.info(f"    上一周期的结束日期: {prev_period_end}")
                            # 找到这个日期之前的最后一个交易日
                            term_end_date = DataSourceHandlerHelper._get_last_trading_date_before(
                                data_manager, prev_period_end, latest_trading_date
                            )
                            logger.info(f"    上一周期结束日期之前的最后一个交易日: {term_end_date}")
        
        # 检查日期范围是否有效
        if term_end_date:
            if DateUtils.is_after(start_date, term_end_date) or DateUtils.is_same(start_date, term_end_date):
                logger.info(f"    ⚠️ 日期范围无效: start_date ({start_date}) >= end_date ({term_end_date})")
                logger.info(f"    结果: 跳过该 term")
            else:
                logger.info(f"    ✅ 日期范围有效: {start_date} ~ {term_end_date}")
                logger.info(f"    结果: 会创建 job，日期范围: {start_date} ~ {term_end_date}")
        else:
            logger.info(f"    ⚠️ term_end_date 为 None，跳过该 term")


def main():
    """主函数"""
    # 初始化 DataManager
    data_manager = DataManager()
    
    # 加载 kline 配置
    from userspace.data_source.handlers.stock_klines.kline import config as kline_config
    config = DataSourceConfig(kline_config.CONFIG, data_source_key="kline")
    
    logger.info("开始测试股票的 renew 时间窗口...")
    logger.info(f"测试股票列表: {TEST_STOCKS}")
    
    for stock_id in TEST_STOCKS:
        try:
            test_stock_renew_window(stock_id, config, data_manager)
        except Exception as e:
            logger.error(f"测试股票 {stock_id} 时出错: {e}", exc_info=True)
    
    logger.info("\n测试完成！")


if __name__ == "__main__":
    main()
