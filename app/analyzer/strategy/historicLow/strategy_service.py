import pprint
from .strategy_settings import invest_settings
from datetime import datetime


class HistoricLowService:
    def __init__(self):
        pass

    def find_lowest_records(self, records):
        """寻找最低点记录 - 参照Node.js版本实现"""
        low_points = []

        if not self.is_reached_min_required_monthly_records(records):
            return []

        # 遍历所有扫描周期
        for term in invest_settings['terms']:
            lowest_record = self.find_lowest_record(records, term)
            if lowest_record:
                low_points.append({
                    'term': term,
                    'record': lowest_record
                })

        # 添加全局最低点（term=0表示所有历史数据）
        lowest_record = self.find_lowest_record(records)
        if lowest_record:
            low_points.append({
                'term': 0,
                'record': lowest_record
            })

        return low_points

    def find_lowest_record(self, records, amount=None):
        """寻找指定周期内的最低点记录 - 参照Node.js版本实现"""
        if not records or len(records) == 0:
            return None
            
        # 调试信息
        # print(f"    🔍 find_lowest_record: records类型={type(records)}, 长度={len(records) if hasattr(records, '__len__') else 'N/A'}")
        # if records and len(records) > 0:
        #     print(f"    🔍 第一条记录: {records[0]}")
        #     print(f"    🔍 最后一条记录: {records[-1]}")
            
        lowest_record = None
        
        # 从最新到最旧查找（与JavaScript版本一致）
        for i in range(len(records) - 1, -1, -1):
            record = records[i]
            
            # 检查记录是否有效
            if record is None or 'lowest' not in record:
                continue
                
            if lowest_record is None or float(record['lowest']) < float(lowest_record['lowest']):
                lowest_record = record
                
            # 如果指定了amount，检查是否达到指定数量
            if amount and (len(records) - i) == amount:
                break
                
        return lowest_record
        
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



    def is_reached_min_required_monthly_records(self, records):
        return len(records) >= invest_settings['min_required_monthly_records']

    def get_max_required_monthly_records(self):
        return max(invest_settings['terms'])

    def get_records_before_date(self, records, date):
        """
        获取指定日期之前的所有记录（不包含本日）
        
        Args:
            records: 记录列表，按日期升序排列（最早的在前，最新的在后）
            date: 目标日期 (格式: YYYYMMDD)
            
        Returns:
            list: 目标日期之前的所有记录
        """
        if not records or len(records) == 0:
            return []
            
        target_date = datetime.strptime(date, '%Y%m%d')
        
        # 由于记录是按日期升序排列的，我们需要找到第一个日期大于等于目标日期的记录
        # 然后返回从开始到该记录之前的所有记录
        for i, record in enumerate(records):
            if not isinstance(record, dict) or 'date' not in record:
                continue
                
            record_date = datetime.strptime(record['date'], '%Y%m%d')
            
            # 如果记录日期大于等于目标日期，返回从开始到该记录之前的所有记录
            if record_date >= target_date:
                result = records[:i]
                return result
        
        # 如果所有记录的日期都小于目标日期，返回所有记录
        return records

    def get_investing(self, stock, investing_stocks):
        return investing_stocks.get(stock['code'])

    def is_trend_suitable_for_investment(self, monthly_records, daily_records):
        """
        检查股票趋势是否适合投资
        只在股票处于横盘或上升趋势时投资
        
        Args:
            monthly_records: 月度K线数据
            daily_records: 日线K线数据
            
        Returns:
            bool: True表示趋势适合投资，False表示不适合
        """
        if not monthly_records or len(monthly_records) < 12:
            return False
        if not daily_records or len(daily_records) < 60:
            return False
            
        monthly_trend = self._analyze_monthly_trend(monthly_records)
        daily_trend = self._analyze_daily_trend(daily_records)
        
        if monthly_trend == 'up':
            return True
        elif monthly_trend == 'sideways':
            return daily_trend != 'down'
        else:
            return False

    def _analyze_monthly_trend(self, monthly_records):
        """分析月度趋势"""
        if len(monthly_records) < 6:
            return 'sideways'
            
        recent_6_months = monthly_records[-6:]
        prices = [float(record['close']) for record in recent_6_months]
        
        slope = self._calculate_trend_slope(prices)
        price_change_pct = (prices[-1] - prices[0]) / prices[0] * 100
        
        if slope > 0.01 and price_change_pct > 5:
            return 'up'
        elif slope < -0.01 and price_change_pct < -5:
            return 'down'
        else:
            return 'sideways'

    def _analyze_daily_trend(self, daily_records):
        """分析日线趋势"""
        if len(daily_records) < 30:
            return 'sideways'
            
        recent_30_days = daily_records[-30:]
        prices = [float(record['close']) for record in recent_30_days]
        
        slope = self._calculate_trend_slope(prices)
        price_change_pct = (prices[-1] - prices[0]) / prices[0] * 100
        
        if slope > 0.005 and price_change_pct > 3:
            return 'up'
        elif slope < -0.005 and price_change_pct < -3:
            return 'down'
        else:
            return 'sideways'

    def _calculate_trend_slope(self, prices):
        """计算线性回归斜率"""
        n = len(prices)
        if n < 2:
            return 0
            
        x_sum = sum(range(n))
        y_sum = sum(prices)
        xy_sum = sum(i * price for i, price in enumerate(prices))
        x2_sum = sum(i * i for i in range(n))
        
        numerator = n * xy_sum - x_sum * y_sum
        denominator = n * x2_sum - x_sum * x_sum
        
        if denominator == 0:
            return 0
            
        return numerator / denominator

    def find_dividers(self, monthly_K_lines):
        """
        找到K线数据中的三个最深的波谷作为divider
        
        Args:
            monthly_K_lines: 月度K线数据列表，按时间升序排列
            
        Returns:
            list: 三个最深的波谷位置（0-1之间的比例）
        """
        if len(monthly_K_lines) < 10:
            # 数据太少，返回默认divider
            # print("    📊 数据不足，使用默认divider: [0.3, 0.5, 0.7]")
            return [0.3, 0.5, 0.7]
        
        # 1. 找到所有的波谷（局部最低点）
        valleys = self.find_valleys(monthly_K_lines)
        # print(f"    🔍 找到 {len(valleys)} 个波谷候选")
        
        if len(valleys) < 3:
            # 波谷太少，返回默认divider
            # print("    📊 波谷数量不足，使用默认divider: [0.3, 0.5, 0.7]")
            return [0.3, 0.5, 0.7]
        
        # 2. 计算每个波谷的深度
        valley_depths = self.calculate_valley_depths(monthly_K_lines, valleys)
        
        # 3. 智能选择历史低点
        selected_valleys = self.select_smart_historic_lows(valley_depths, monthly_K_lines)
        
        # 如果没有足够的智能选择结果，使用传统方法作为备选
        if len(selected_valleys) < 3:
            # print("    ⚠️  智能选择结果不足，使用传统方法补充")
            top_3_valleys = self.select_deepest_valleys(valley_depths, 3)
            selected_valleys = top_3_valleys
        
        # 4. 转换为divider格式（0-1之间的比例）
        dividers = []
        for valley in selected_valleys:
            divider = valley['position'] / len(monthly_K_lines)
            divider = round(divider, 2)
            dividers.append(divider)
        
        # 确保divider按升序排列
        dividers.sort()
        
        # print(f"    📊 最终选择的divider: {dividers}")
        return dividers
    
    # def find_valleys(self, k_lines):
    #     """
    #     找到K线数据中的所有波谷（局部最低点）
        
    #     Args:
    #         k_lines: K线数据列表
            
    #     Returns:
    #         list: 波谷位置列表
    #     """
    #     valleys = []
        
    #     # 使用滑动窗口找到局部最低点
    #     window_size = 5  # 5个周期的窗口
        
    #     for i in range(window_size, len(k_lines) - window_size):
    #         current_low = float(k_lines[i]['lowest'])
            
    #         # 检查是否是局部最低点
    #         is_valley = True
    #         for j in range(i - window_size, i + window_size + 1):
    #             if j != i and float(k_lines[j]['lowest']) < current_low:
    #                 is_valley = False
    #                 break
            
    #         if is_valley:
    #             valleys.append(i)
        
    #     return valleys
    
    # def calculate_valley_depths(self, k_lines, valleys):
    #     """
    #     计算每个波谷的深度
        
    #     Args:
    #         k_lines: K线数据列表
    #         valleys: 波谷位置列表
            
    #     Returns:
    #         list: 包含深度信息的波谷列表
    #     """
    #     valley_depths = []
        
    #     for valley_pos in valleys:
    #         valley_low = float(k_lines[valley_pos]['lowest'])
            
    #         # 向前查找最近的高点
    #         left_peak = self.find_nearest_peak(k_lines, valley_pos, direction='left')
            
    #         # 向后查找最近的高点
    #         right_peak = self.find_nearest_peak(k_lines, valley_pos, direction='right')
            
    #         # 计算深度（相对于两个高点的平均高度）
    #         if left_peak is not None and right_peak is not None:
    #             avg_peak = (left_peak + right_peak) / 2
    #             relative_depth = (avg_peak - valley_low) / avg_peak  # 相对深度
    #             absolute_drop = avg_peak - valley_low  # 绝对跌幅
    #         elif left_peak is not None:
    #             relative_depth = (left_peak - valley_low) / left_peak
    #             absolute_drop = left_peak - valley_low
    #         elif right_peak is not None:
    #             relative_depth = (right_peak - valley_low) / right_peak
    #             absolute_drop = right_peak - valley_low
    #         else:
    #             relative_depth = 0
    #             absolute_drop = 0
            
    #         # 计算综合评分（结合相对跌幅和绝对跌幅）
    #         # 相对跌幅权重0.6，绝对跌幅权重0.4
    #         # 绝对跌幅需要标准化，假设最大跌幅为10元
    #         normalized_absolute_drop = min(absolute_drop / 10.0, 1.0)  # 标准化到0-1
    #         composite_score = relative_depth * 0.6 + normalized_absolute_drop * 0.4
            
    #         valley_depths.append({
    #             'position': valley_pos,
    #             'date': k_lines[valley_pos]['date'],  # 添加日期信息
    #             'lowest': valley_low,
    #             'depth': relative_depth,  # 保持原有字段名兼容性
    #             'absolute_drop': absolute_drop,
    #             'composite_score': composite_score,
    #             'left_peak': left_peak,
    #             'right_peak': right_peak
    #         })
        
    #     return valley_depths
    