"""
股票K线数据更新器
"""

from typing import Dict, List, Any
from loguru import logger
from ...base_renewer import BaseRenewer


class StockKLinesRenewer(BaseRenewer):
    """股票K线数据更新器"""
    
    def build_jobs(self, start_date: str, end_date: str) -> List[Dict]:
        """构建股票K线更新任务"""
        jobs = []
        
        try:
            # 获取股票列表（从依赖数据中获取）
            stock_index = self._get_stock_index()
            
            if not stock_index:
                logger.warning("⚠️ 没有股票列表，无法构建K线更新任务")
                return []
            
            # 获取每只股票的最新数据日期
            stocks_needing_update = self._get_stocks_needing_update(stock_index, end_date)
            
            # 只为需要更新的股票构建任务
            for stock_code in stocks_needing_update:
                # 获取股票名称
                stock_name = self._get_stock_name(stock_code, stock_index)
                
                jobs.append({
                    'ts_code': stock_code,
                    'stock_name': stock_name,
                    'start_date': start_date,
                    'end_date': end_date,
                    'api_method': 'daily',
                    'api_params': {
                        'ts_code': stock_code,
                        'start_date': start_date,
                        'end_date': end_date,
                        'fields': 'ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
                    }
                })
            
            logger.info(f"📈 构建了 {len(jobs)} 个股票K线更新任务（共 {len(stock_index)} 只股票，{len(jobs)} 只需要更新）")
            return jobs
            
        except Exception as e:
            logger.error(f"❌ 构建股票K线任务失败: {e}")
            return []
    
    def _get_stock_index(self) -> List[Dict]:
        """获取股票指数列表"""
        try:
            # 从数据库中获取股票列表
            table_instance = self.db.get_table_instance('stock_index')
            if table_instance:
                # 获取所有活跃的股票
                # 使用 storage 中的方法获取股票列表
                stock_list = self.storage.load_stock_index()
                if stock_list:
                    return stock_list
            
            # 返回一些默认的主要股票代码
            return []
            
        except Exception as e:
            logger.error(f"❌ 获取股票列表失败: {e}")
            return []
    
    def _get_stocks_needing_update(self, stock_index: List[Dict], end_date: str) -> List[str]:
        """获取需要更新的股票列表"""
        stocks_needing_update = []
        
        try:
            # 获取 stock_klines 表实例
            table_instance = self.db.get_table_instance('stock_klines')
            if not table_instance:
                logger.warning("⚠️ 无法获取 stock_klines 表实例")
                return []
            
            # 批量查询所有股票的最新日期
            # stock_index 已经是正确的字典列表，直接提取 id 字段
            stock_codes = [stock['id'] for stock in stock_index if stock.get('id')]
            
            if not stock_codes:
                return []
            
            # 使用 model 中的方法获取每只股票的最新日期
            latest_dates = table_instance.get_every_stock_latest_update_by_term(stock_codes, 'daily')
            
            
            # 检查每只股票是否需要更新
            for stock_code in stock_codes:
                latest_date = latest_dates.get(stock_code)
                
                # 如果没有数据，则需要更新
                if latest_date is None:
                    stocks_needing_update.append(stock_code)
                # 如果有数据但最新日期早于结束日期，则需要更新
                elif latest_date < end_date:
                    stocks_needing_update.append(stock_code)
                # 如果最新日期已经等于或晚于结束日期，则不需要更新
            
            logger.info(f"📊 检查了 {len(stock_codes)} 只股票，其中 {len(stocks_needing_update)} 只需要更新")
            return stocks_needing_update
            
        except Exception as e:
            logger.error(f"❌ 获取需要更新的股票列表失败: {e}")
            return []
    
    def _get_stock_name(self, stock_code: str, stock_index: List[Dict]) -> str:
        """获取股票名称"""
        try:
            for stock in stock_index:
                if stock.get('id') == stock_code:
                    return stock.get('name', stock_code)
            return stock_code  # 如果找不到名称，返回股票代码
        except Exception as e:
            logger.warning(f"❌ 获取股票名称失败: {e}")
            return stock_code
    
    def should_renew(self, start_date: str, end_date: str) -> bool:
        """判断是否需要更新"""
        # K线数据总是需要更新（可以根据具体需求调整逻辑）
        return True
    
    def should_execute_api(self, api_config: Dict, previous_results: Dict) -> bool:
        """判断是否执行特定 API"""
        # K线数据只需要 daily API
        return api_config['name'] == 'daily'
