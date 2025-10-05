"""
股本信息同步脚本 - 增量存储策略
从Tushare获取股本数据，只存储发生变化的数据
"""
import tushare as ts
from utils.db.db_manager import DatabaseManager
from utils.db.tables.share_info.model import ShareInfoModel
import time


class ShareInfoSyncer:
    """股本信息同步器 - 增量存储"""
    
    def __init__(self):
        self.pro = ts.pro_api()
        self.db_manager = DatabaseManager()
        self.share_model = ShareInfoModel(self.db_manager)
    
    def sync_stock_share_info(self, stock_id, start_year=2008, end_year=2024):
        """
        同步单只股票的股本信息（增量存储）
        
        Args:
            stock_id (str): 股票代码
            start_year (int): 开始年份
            end_year (int): 结束年份
        """
        print(f"开始同步 {stock_id} 的股本信息...")
        
        try:
            # 获取历史股本数据
            start_date = f"{start_year}0101"
            end_date = f"{end_year}1231"
            
            df = self.pro.balancesheet(
                ts_code=stock_id,
                start_date=start_date,
                end_date=end_date,
                fields='ts_code,end_date,total_share,float_share'
            )
            
            if df.empty:
                print(f"{stock_id}: 无股本数据")
                return
            
            # 转换为季度格式并去重
            quarterly_data = []
            quarters_seen = set()
            
            for _, row in df.iterrows():
                end_date_str = str(row['end_date'])
                quarter = self._date_to_quarter(end_date_str)
                
                # 避免重复季度数据
                if quarter not in quarters_seen:
                    quarterly_data.append({
                        'quarter': quarter,
                        'total_share': int(row['total_share']) if pd.notna(row['total_share']) else 0,
                        'float_share': int(row['float_share']) if pd.notna(row['float_share']) else 0
                    })
                    quarters_seen.add(quarter)
            
            print(f"{stock_id}: 原始数据 {len(quarterly_data)} 个季度")
            
            # 检测变化并存储
            changes_count = self.share_model.detect_and_store_changes(stock_id, quarterly_data)
            
            # 显示压缩统计
            stats = self.share_model.get_compression_stats(stock_id)
            print(f"{stock_id}: 存储了 {changes_count} 次变化，压缩率 {stats['compression_ratio']}%")
            
            time.sleep(0.2)  # 避免API限制
            
        except Exception as e:
            print(f"{stock_id}: 同步失败 - {e}")
    
    def sync_multiple_stocks(self, stock_list, start_year=2008, end_year=2024):
        """
        批量同步多只股票的股本信息
        
        Args:
            stock_list (list): 股票代码列表
            start_year (int): 开始年份
            end_year (int): 结束年份
        """
        print(f"开始批量同步 {len(stock_list)} 只股票的股本信息...")
        
        total_original = 0
        total_stored = 0
        
        for i, stock_id in enumerate(stock_list):
            print(f"进度: {i+1}/{len(stock_list)} - {stock_id}")
            
            # 获取统计信息
            stats_before = self.share_model.get_compression_stats(stock_id)
            
            # 同步数据
            self.sync_stock_share_info(stock_id, start_year, end_year)
            
            # 获取更新后的统计信息
            stats_after = self.share_model.get_compression_stats(stock_id)
            
            total_original += stats_after.get('total_quarters', 0)
            total_stored += stats_after.get('stored_changes', 0)
        
        # 总体压缩统计
        overall_compression = (1 - total_stored / total_original) * 100 if total_original > 0 else 0
        print(f"\\n=== 总体压缩统计 ===")
        print(f"理论总季度数: {total_original}")
        print(f"实际存储记录: {total_stored}")
        print(f"总体压缩率: {overall_compression:.2f}%")
    
    def test_market_cap_calculation(self, stock_id, test_dates):
        """
        测试市值计算功能
        
        Args:
            stock_id (str): 股票代码
            test_dates (list): 测试日期列表，格式 ['20240101', '20240630', ...]
        """
        print(f"\\n=== 测试 {stock_id} 市值计算 ===")
        
        for date in test_dates:
            # 模拟价格（实际应用中从K线数据获取）
            mock_price = 15.50
            
            market_cap_info = self.share_model.calculate_market_cap_by_date(stock_id, mock_price, date)
            
            if market_cap_info:
                print(f"{date}: 价格 {mock_price} -> 总市值 {market_cap_info['total_market_cap_yi']:.2f}亿元")
            else:
                print(f"{date}: 无股本数据")
    
    def _date_to_quarter(self, date_str):
        """将日期转换为季度"""
        year = int(date_str[:4])
        month = int(date_str[4:6])
        
        if month <= 3:
            return f"{year}Q1"
        elif month <= 6:
            return f"{year}Q2"
        elif month <= 9:
            return f"{year}Q3"
        else:
            return f"{year}Q4"


def main():
    """主函数 - 演示增量存储效果"""
    syncer = ShareInfoSyncer()
    
    # 测试股票列表
    test_stocks = ['000001.SZ', '000002.SZ', '600000.SH']
    
    print("=== 股本信息增量存储演示 ===")
    
    # 同步测试股票数据
    syncer.sync_multiple_stocks(test_stocks, start_year=2020, end_year=2024)
    
    # 测试市值计算
    test_dates = ['20240101', '20240630', '20240930']
    syncer.test_market_cap_calculation('000001.SZ', test_dates)
    
    # 显示压缩效果
    print("\\n=== 压缩效果对比 ===")
    for stock in test_stocks:
        stats = syncer.share_model.get_compression_stats(stock)
        if stats['total_changes'] > 0:
            print(f"{stock}: {stats['period']} 期间，从 {stats['total_quarters']} 季度压缩到 {stats['stored_changes']} 条记录，压缩率 {stats['compression_ratio']}%")


if __name__ == "__main__":
    main()
