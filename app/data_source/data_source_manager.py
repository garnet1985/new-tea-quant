from app.data_source.providers.tushare.main import Tushare
from app.data_source.providers.akshare.main import AKShare
from app.data_source.providers.akshare.main_storage import AKShareStorage
from typing import List, Dict, Optional, Union
import pandas as pd

class DataSourceManager:
    def __init__(self, connected_db, is_verbose: bool = False):
        self.db = connected_db
        self.is_verbose = is_verbose

        self.sources = {
            'tushare': Tushare(connected_db, is_verbose),
            'akshare': AKShare(connected_db, is_verbose),
        }

        # 初始化复权服务
        self.adj_factor_storage = AKShareStorage(connected_db)

        # global data memory cache
        self.latest_market_open_day = None
        self.latest_stock_index = None

    def get_source(self, source_name: str):
        return self.sources[source_name]()

    async def renew_data(self):
        tu = self.sources['tushare']
        ak = self.sources['akshare']

        # 先获取最新交易日
        self.latest_market_open_day = await tu.get_latest_market_open_day()

        # 然后更新股票指数
        self.latest_stock_index = tu.renew_stock_index(self.latest_market_open_day)

        # 限制测试数量，避免长时间运行
        # self.latest_stock_index = self.latest_stock_index[:3]
        
        await tu.renew_stock_K_lines(self.latest_market_open_day, self.latest_stock_index)
        
        ak.inject_dependency(tu).renew_stock_K_line_factors(self.latest_market_open_day, self.latest_stock_index)

        # below are not implemented yet
        # tu.renew_global_economic_data()
        # tu.renew_corporate_finance_data()

    # ==================== 复权服务 ====================
    
    def get_adj_factor(self, ts_code: str, date: str) -> Optional[float]:
        """
        获取指定股票在指定日期的前复权因子
        
        Args:
            ts_code: 股票代码 (如: '000001.SZ')
            date: 日期 (格式: 'YYYYMMDD')
            
        Returns:
            前复权因子，如果未找到返回None
        """
        factor_data = self.adj_factor_storage.get_adj_factor_for_date(ts_code, date)
        if factor_data:
            return factor_data['qfq_factor']
        return None
    
    def adjust_price(self, ts_code: str, raw_price: float, date: str) -> Optional[float]:
        """
        将裸价格转换为前复权价格
        
        Args:
            ts_code: 股票代码
            raw_price: 裸价格
            date: 日期 (格式: 'YYYYMMDD')
            
        Returns:
            前复权价格，如果未找到因子返回None
        """
        factor = self.get_adj_factor(ts_code, date)
        if factor:
            return raw_price * factor
        return None
    
    def adjust_price_list(self, ts_code: str, raw_prices: List[float], dates: List[str]) -> List[Optional[float]]:
        """
        批量转换裸价格列表为前复权价格列表
        
        Args:
            ts_code: 股票代码
            raw_prices: 裸价格列表
            dates: 日期列表 (格式: 'YYYYMMDD')
            
        Returns:
            前复权价格列表，未找到因子的位置返回None
        """
        if len(raw_prices) != len(dates):
            raise ValueError("价格列表和日期列表长度必须相同")
        
        adjusted_prices = []
        for raw_price, date in zip(raw_prices, dates):
            adjusted_price = self.adjust_price(ts_code, raw_price, date)
            adjusted_prices.append(adjusted_price)
        
        return adjusted_prices
    
    def adjust_dataframe(self, ts_code: str, df: pd.DataFrame, 
                        price_column: str = 'close', date_column: str = 'date') -> pd.DataFrame:
        """
        将DataFrame中的价格列转换为前复权价格
        
        Args:
            ts_code: 股票代码
            df: 包含价格和日期的DataFrame
            price_column: 价格列名
            date_column: 日期列名
            
        Returns:
            添加了前复权价格列的DataFrame
        """
        if price_column not in df.columns or date_column not in df.columns:
            raise ValueError(f"DataFrame必须包含列: {price_column}, {date_column}")
        
        # 复制DataFrame避免修改原数据
        result_df = df.copy()
        
        # 添加前复权价格列
        result_df['qfq_price'] = None
        
        for idx, row in result_df.iterrows():
            raw_price = row[price_column]
            date = str(row[date_column]).replace('-', '')  # 确保日期格式为YYYYMMDD
            
            adjusted_price = self.adjust_price(ts_code, raw_price, date)
            result_df.at[idx, 'qfq_price'] = adjusted_price
        
        return result_df
    
    def get_adj_factor_info(self, ts_code: str, date: str) -> Optional[Dict]:
        """
        获取复权因子的详细信息
        
        Args:
            ts_code: 股票代码
            date: 日期
            
        Returns:
            包含因子信息的字典，如果未找到返回None
        """
        return self.adj_factor_storage.get_adj_factor_for_date(ts_code, date)