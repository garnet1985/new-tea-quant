from .strategy_settings import invest_settings
from datetime import datetime


class HistoricLowService:
    def __init__(self):
        pass

    def find_lowest_records(self, records):
        """寻找最低点记录"""
        low_points = []
        
        # 检查输入数据是否有效
        if not records or len(records) == 0:
            print("    ⚠️ 没有月度数据，无法寻找最低点")
            return low_points
        
        # 为每个扫描周期寻找最低点
        for term in invest_settings['scan_terms']:
            if term > len(records):
                data = records
            else:
                data = records[:term]
            lowest_record = self.find_lowest(data)
            if lowest_record is not None:  # 只添加有效的最低点记录
                low_points.append({
                    'term': term,
                    'record': lowest_record
                })
            else:
                print(f"    ⚠️ 扫描周期 {term}: 未找到有效的最低点记录")
        
        # 添加全历史最低点（JavaScript版本有这个逻辑）
        if records:
            all_time_lowest = self.find_lowest(records)
            if all_time_lowest is not None:  # 只添加有效的全历史最低点
                low_points.append({
                    'term': 0,  # 0表示全历史
                    'record': all_time_lowest
                })
            else:
                print(f"    ⚠️ 全历史: 未找到有效的最低点记录")
        
        return low_points

    def find_lowest(self, records):
        """寻找最低点记录（从最新到最旧查找，与JavaScript版本一致）"""
        # 检查输入数据是否有效
        if not records or len(records) == 0:
            return None
            
        lowest_record = None
        # 从最新到最旧查找（与JavaScript版本一致）
        for i in range(len(records) - 1, -1, -1):
            record = records[i]
            # 检查记录是否有效
            if record is None or 'lowest' not in record:
                continue
            if lowest_record is None or record['lowest'] < lowest_record['lowest']:
                lowest_record = record
        return lowest_record

    def is_in_invest_range(self, record, low_point):
        """检查是否在投资范围内"""
        # 检查low_point是否有效
        if low_point is None or low_point['record'] is None:
            return False
            
        # 将Decimal转换为float进行计算
        lowest = float(low_point['record']['lowest'])
        close = float(record['close'])
        
        upper = lowest * (1 + invest_settings['goal']['opportunityRange'])
        lower = lowest * (1 - invest_settings['goal']['opportunityRange'])
        
        print(f"      📊 投资范围检查: 最低点={lowest}, 当前价格={close}, 范围=[{lower:.2f}, {upper:.2f}]")

        if close >= lower and close <= upper:
            return True
        else:
            return False

    def set_loss(self, record):
        return float(record['close']) * invest_settings['goal']['loss']
    
    def set_win(self, record):
        return float(record['close']) * invest_settings['goal']['win']

    def get_most_recent_klines(self, kline_table, stock, term, limit=1):
        sql = f"""
                SELECT date, close, lowest, highest, open, volume, amount
                FROM stock_kline 
                WHERE code = %s AND term = %s
                ORDER BY date DESC 
                LIMIT {limit}
            """
        return kline_table.execute_raw_query(sql, (stock['code'], term))

    def get_min_required_monthly_records(self):
        return min(invest_settings['scan_terms'])

    def get_max_required_monthly_records(self):
        return max(invest_settings['scan_terms'])

    def get_records_before_date(self, records, date):
        """
        获取指定日期之前的所有记录（不包含本日）
        
        Args:
            records: 记录列表，按日期升序排列（最早的在前，最新的在后）
            date: 目标日期（格式：YYYYMMDD）
            
        Returns:
            list: 目标日期之前的所有记录
        """
        target_date = datetime.strptime(date, '%Y%m%d')
        
        # 由于记录是按日期升序排列的，我们需要找到第一个日期大于等于目标日期的记录
        # 然后返回从开始到该记录之前的所有记录
        for i, record in enumerate(records):
            record_date = datetime.strptime(record['date'], '%Y%m%d')
            
            # 如果记录日期大于等于目标日期，返回从开始到该记录之前的所有记录
            if record_date >= target_date:
                return records[:i]
        
        # 如果所有记录的日期都小于目标日期，返回所有记录
        return records

    def get_investing(self, stock, investing_stocks):
        return investing_stocks.get(stock['code'])