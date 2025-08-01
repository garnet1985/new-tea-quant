import pprint
from .strategy_settings import invest_settings
from datetime import datetime


class HistoricLowService:
    def __init__(self):
        pass

    def find_lowest_records(self, records):
        """寻找最低点记录"""
        low_points = []

        if len(records) < self.get_min_required_monthly_records():
            return []

        # 为每个扫描周期寻找最低点
        for term in invest_settings['scan_terms']:
            if term <= 0:
                # 处理全历史最低点
                all_time_lowest = self.find_lowest(records)
                if all_time_lowest is not None:  # 只添加有效的全历史最低点
                    low_points.append({
                        'term': 0,  # 0表示全历史
                        'record': all_time_lowest
                    })
            else:
                # 处理指定周期的最低点
                data = records[-term:]  # 取最新的term条记录
                lowest_record = self.find_lowest(data)
                
                if lowest_record is not None:  # 只添加有效的最低点记录
                    low_points.append({
                        'term': term,
                        'record': lowest_record
                    })

        # 对 low_points 进行合并，如果有不同周期下得到的最低值是一样的，则只保留一个
        low_points = self.merge_low_points(low_points)
                
        return low_points

    def merge_low_points(self, low_points):
        """对 low_points 进行合并，如果有不同周期下得到的最低值是一样的，则只保留一个"""
        merged_low_points = []
        seen_records = set()
        
        for low_point in low_points:
            # 使用最低价格作为唯一标识
            lowest_price = float(low_point['record']['lowest'])
            
            if lowest_price not in seen_records:
                seen_records.add(lowest_price)
                merged_low_points.append(low_point)
        
        return merged_low_points

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
        
        # print(f"      📊 投资范围检查: 最低点={lowest}, 当前价格={close}, 范围=[{lower:.2f}, {upper:.2f}]")

        if close >= lower and close <= upper:
            return True
        else:
            return False

    def set_loss(self, record):
        return float(record['close']) * invest_settings['goal']['loss']
    
    def set_win(self, record):
        return float(record['close']) * invest_settings['goal']['win']

    # def get_most_recent_klines(self, kline_table, stock, term, limit=1):
    #     sql = f"""
    #             SELECT date, close, lowest, highest, open, volume, amount
    #             FROM stock_kline 
    #             WHERE code = %s AND term = %s
    #             ORDER BY date DESC 
    #             LIMIT {limit}
    #         """
    #     result = kline_table.execute_raw_query(sql, (stock['code'], term))
        
    #     # 添加调试信息
    #     print(f"    🔍 get_most_recent_klines 查询: stock={stock['code']}, term={term}, limit={limit}")
    #     print(f"    🔍 查询结果: {result}")
    #     print(f"    🔍 结果类型: {type(result)}")
        
    #     # 确保返回列表而不是None
    #     if result is None:
    #         print(f"    ❌ ERROR: get_most_recent_klines 返回 None")
    #         return []
        
    #     return result

    def get_min_required_monthly_records(self):
        minNum = float('inf')  # 使用 Python 的无穷大
        for term in invest_settings['scan_terms']:
            if term >= 0 and term < minNum:
                minNum = term
        return minNum

    def get_max_required_monthly_records(self):
        return max(invest_settings['scan_terms'])

    def get_records_before_date(self, records, date):
        """
        获取指定日期之前的所有记录（不包含本日）
        
        Args:
            records: 记录列表，按日期升序排列（最早的在前，最新的在后）
            date: 目标日期 (格式: YYYYMMDD)
            
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
                result = records[:i]
                # print(f"    🔍 返回 {len(result)} 条记录")
                return result
        
        # 如果所有记录的日期都小于目标日期，返回所有记录
        # print(f"    🔍 返回所有 {len(records)} 条记录")
        return records

    def get_investing(self, stock, investing_stocks):
        return investing_stocks.get(stock['code'])