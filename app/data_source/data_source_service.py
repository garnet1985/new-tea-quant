from datetime import date as date_type, timedelta
from typing import Any, Dict, List
from dateutil.relativedelta import relativedelta

class DataSourceService:
    @staticmethod
    def parse_ts_code(ts_code: str):
        code, market = ts_code.split('.', 1)
        return code, market

    @staticmethod
    def to_hyphen_date(date: str):
        # 20250804 -> 2025-08-04
        return f"{date[:4]}-{date[4:6]}-{date[6:]}"
    
    @staticmethod
    def to_hyphen_date_type(date: str):
        return date_type(int(date[:4]), int(date[4:6]), int(date[6:8]))

    @staticmethod
    def to_str_date(date: str):
        # 2025-08-04 -> 20250804
        return date.replace('-', '')

    @staticmethod
    def to_qfq(k_lines: list, qfq_factors: list):
        """
        计算前复权价格
        
        ⚠️  建议使用 DataLoader.load_klines() 替代
        
        新方法的优势：
            from app.data_loader import DataLoader
            
            loader = DataLoader(db)
            
            # 返回List（使用此方法，性能相同）
            records = loader.load_klines(stock_id, adjust='qfq', as_dataframe=False)
            
            # 返回DataFrame（代码更简洁，便于后续分析）
            df = loader.load_klines(stock_id, adjust='qfq', as_dataframe=True)
        
        DataLoader统一了数据加载接口，避免手动组合表操作。
        
        Args:
            k_lines: K线数据列表，包含 date, open, close, highest, lowest 等字段
            qfq_factors: 复权因子列表，包含 date, qfq 等字段
            
        Returns:
            list: 前复权后的K线数据列表
        """
        if not k_lines or not qfq_factors:
            return k_lines
            
        # 确保因子按日期升序
        sorted_factors = sorted(qfq_factors, key=lambda x: x['date'])
        
        # 获取第一个（最早的）复权因子作为默认值
        default_factor = sorted_factors[0]['qfq'] if sorted_factors else 1.0
        
        # 处理每条K线
        for k_line in k_lines:
            # 保存原始值到raw属性
            k_line['raw'] = {
                'open': k_line.get('open'),
                'close': k_line.get('close'),
                'highest': k_line.get('highest'),
                'lowest': k_line.get('lowest')
            }
            
            # 获取当前K线的日期
            current_date = k_line.get('date')
            if not current_date:
                continue
                
            # 查找对应的复权因子
            qfq_factor = DataSourceService._find_qfq_factor(current_date, sorted_factors)
            
            # 如果没有找到复权因子，使用默认因子
            if qfq_factor is None:
                qfq_factor = default_factor
            
            if qfq_factor is not None:
                # 计算前复权价格
                k_line['open'] = k_line['raw']['open'] * qfq_factor if k_line['raw']['open'] else None
                k_line['close'] = k_line['raw']['close'] * qfq_factor if k_line['raw']['close'] else None
                k_line['highest'] = k_line['raw']['highest'] * qfq_factor if k_line['raw']['highest'] else None
                k_line['lowest'] = k_line['raw']['lowest'] * qfq_factor if k_line['raw']['lowest'] else None
            else:
                # 保持原值
                pass
        
        return k_lines

    @staticmethod
    def filter_out_negative_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤掉价格为负或无效的记录
        
        ⚠️  建议使用 DataLoader.load_klines() 替代
        
        新方法的优势：
            from app.data_loader import DataLoader
            
            loader = DataLoader(db)
            
            # 自动过滤负值
            records = loader.load_klines(stock_id, filter_negative=True)
            
            # DataFrame版本（代码更简洁）
            df = loader.load_klines(stock_id, as_dataframe=True, filter_negative=True)
            # df = df[df['close'] > 0]  # 一行搞定！
        
        DataLoader统一了数据加载接口。
        """
        if not records:
            return []
        
        filtered_records = []
        for record in records:
            close_price = record.get('close', 0)
            if close_price and close_price > 0:
                filtered_records.append(record)
        
        return filtered_records
    
    @staticmethod
    def _find_qfq_factor(target_date: str, sorted_factors: list) -> float:
        """
        查找目标日期对应的复权因子
        
        算法：找到目标日期所在的时间段，返回该时间段的复权因子
        时间段定义：大于等于前一个因子日期，小于后一个因子日期
        
        Args:
            target_date: 目标日期 (YYYYMMDD格式)
            sorted_factors: 按时间升序排列的复权因子列表
            
        Returns:
            float: 复权因子，如果没找到返回None
        """
        if not sorted_factors:
            return None
            
        # 如果只有一个因子，直接返回
        if len(sorted_factors) == 1:
            return sorted_factors[0]['qfq']
        
        # 找到目标日期对应的复权因子
        # 规则：使用小于等于目标日期的最近一个复权因子
        result_factor = None
        
        for factor in sorted_factors:
            factor_date = factor['date']
            if target_date >= factor_date:
                result_factor = factor['qfq']
            else:
                # 如果目标日期小于因子日期，说明已经超过了，使用上一个因子
                break
        
        return result_factor

    # ==================== 日期和季度处理工具函数 ====================
    
    @staticmethod
    def date_to_quarter(date_str: str) -> str:
        """
        将日期转换为季度格式
        
        Args:
            date_str: 日期字符串，格式为 YYYYMMDD，如 '20240315'
            
        Returns:
            str: 季度字符串，格式为 YYYYQN，如 '2024Q1'
        """
        year = int(date_str[:4])
        month = int(date_str[4:6])
        quarter = (month - 1) // 3 + 1
        return f"{year}Q{quarter}"
    
    @staticmethod
    def quarter_to_date(quarter_str: str) -> str:
        """
        将季度转换为该季度的末尾日期
        
        Args:
            quarter_str: 季度字符串，格式为 YYYYQN，如 '2024Q1'
            
        Returns:
            str: 日期字符串，格式为 YYYYMMDD，如 '20240331' (Q1的最后一天)
        """
        year = int(quarter_str[:4])
        quarter = int(quarter_str[5])
        
        # 季度末月份和日期映射
        quarter_end_map = {
            1: (3, 31),   # Q1: 3月31日
            2: (6, 30),   # Q2: 6月30日
            3: (9, 30),   # Q3: 9月30日
            4: (12, 31),  # Q4: 12月31日
        }
        
        month, day = quarter_end_map[quarter]
        return f"{year}{month:02d}{day:02d}"
    
    @staticmethod
    def to_next_quarter(date_or_quarter_str: str) -> str:
        """
        计算下一个季度
        
        Args:
            date_or_quarter_str: 日期字符串（格式为 YYYYMMDD，如 '20240315'）
                                 或季度字符串（格式为 YYYYQN，如 '2024Q1'）
            
        Returns:
            str: 下一个季度，如 '2024Q2'
        """
        # 判断输入是日期还是季度
        if 'Q' in date_or_quarter_str:
            # 季度格式
            year = int(date_or_quarter_str[:4])
            quarter = int(date_or_quarter_str[5])
        else:
            # 日期格式，先转换为季度
            quarter_str = DataSourceService.date_to_quarter(date_or_quarter_str)
            year = int(quarter_str[:4])
            quarter = int(quarter_str[5])
        
        if quarter == 4:
            return f"{year + 1}Q1"
        else:
            return f"{year}Q{quarter + 1}"
    
    @staticmethod
    def to_next_day(date_str: str) -> str:
        """
        计算下一天
        
        Args:
            date_str: 日期字符串，格式为 YYYYMMDD，如 '20240315'
            
        Returns:
            str: 下一天的日期，如 '20240316'
        """
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        
        current_date = date_type(year, month, day)
        next_date = current_date + timedelta(days=1)
        
        return next_date.strftime('%Y%m%d')
    
    @staticmethod
    def to_next_week(date_str: str) -> str:
        """
        计算下一周（7天后）
        
        Args:
            date_str: 日期字符串，格式为 YYYYMMDD，如 '20240315'
            
        Returns:
            str: 一周后的日期，如 '20240322'
        """
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        
        current_date = date_type(year, month, day)
        next_week = current_date + timedelta(days=7)
        
        return next_week.strftime('%Y%m%d')
    
    @staticmethod
    def to_next_month(date_str: str) -> str:
        """
        计算下一个月的同一天
        
        Args:
            date_str: 日期字符串，格式为 YYYYMMDD，如 '20240315'
            
        Returns:
            str: 下个月的日期，如 '20240415'
        """
        year = int(date_str[:4])
        month = int(date_str[4:6])
        day = int(date_str[6:8])
        
        current_date = date_type(year, month, day)
        next_month = current_date + relativedelta(months=1)
        
        return next_month.strftime('%Y%m%d')
    
    @staticmethod
    def time_gap_by(unit: str, start_date: str, end_date: str) -> int:
        """
        计算两个日期之间的时间差
        
        Args:
            unit: 时间单位，'day', 'week', 'month', 'quarter' 之一
            start_date: 开始日期或季度
                - 日期格式: YYYYMMDD（用于day/week/month）
                - 季度格式: YYYYQ[1-4]（用于quarter）
            end_date: 结束日期或季度（格式同start_date）
            
        Returns:
            int: 时间差（单位由 unit 参数决定）
        """
        # 处理季度格式
        if unit == 'quarter':
            # 季度格式：2023Q1, 2023Q2, etc.
            if 'Q' in start_date and 'Q' in end_date:
                start_year = int(start_date[:4])
                start_q = int(start_date[-1])
                end_year = int(end_date[:4])
                end_q = int(end_date[-1])
                
                # 计算季度差
                return (end_year - start_year) * 4 + (end_q - start_q)
            else:
                raise ValueError(f"Quarter format requires 'YYYYQ[1-4]', got: {start_date}, {end_date}")
        
        # 处理日期格式
        year1 = int(start_date[:4])
        month1 = int(start_date[4:6])
        day1 = int(start_date[6:8])
        
        year2 = int(end_date[:4])
        month2 = int(end_date[4:6])
        day2 = int(end_date[6:8])
        
        date1 = date_type(year1, month1, day1)
        date2 = date_type(year2, month2, day2)
        
        if unit == 'day':
            return (date2 - date1).days
        elif unit == 'week':
            return (date2 - date1).days // 7
        elif unit == 'month':
            # 计算月份差
            month_diff = (year2 - year1) * 12 + (month2 - month1)
            # 如果天数不足，减一个月
            if day2 < day1:
                month_diff -= 1
            return month_diff
        else:
            raise ValueError(f"不支持的时间单位: {unit}")
    
    @staticmethod
    def get_previous_week_end(date_str: str) -> str:
        """
        获取指定日期所在周的前一周的周日
        
        逻辑：
        1. 找到date所在周的周一
        2. 前一周的周日 = 本周周一 - 1天
        
        例如：
        - 20250930 (周二) → 本周一=20250929 → 前一周日=20250928
        - 20251006 (周一) → 本周一=20251006 → 前一周日=20251005
        
        Args:
            date_str: 日期字符串，格式YYYYMMDD
            
        Returns:
            str: 前一周的周日，格式YYYYMMDD
        """
        date_obj = DataSourceService.to_hyphen_date_type(date_str)
        
        # 计算本周的周一
        days_since_monday = date_obj.weekday()  # 周一=0, 周日=6
        this_week_monday = date_obj - timedelta(days=days_since_monday)
        
        # 前一周的周日 = 本周周一 - 1天
        last_week_sunday = this_week_monday - timedelta(days=1)
        
        return last_week_sunday.strftime('%Y%m%d')
    
    @staticmethod
    def get_previous_month_end(date_str: str) -> str:
        """
        获取指定日期所在月的前一个月的最后一天
        
        逻辑：
        1. 找到date所在月
        2. 计算前一个月的最后一天
        
        例如：
        - 20250930 → 所在月=9月 → 前一月=8月 → 返回 20250831
        - 20251105 → 所在月=11月 → 前一月=10月 → 返回 20251031
        - 20250115 → 所在月=1月 → 前一月=12月 → 返回 20241231
        
        Args:
            date_str: 日期字符串，格式YYYYMMDD
            
        Returns:
            str: 前一个月的最后一天，格式YYYYMMDD
        """
        import calendar
        
        year = int(date_str[:4])
        month = int(date_str[4:6])
        
        # 前一个月的年月
        if month == 1:
            last_month_year = year - 1
            last_month = 12
        else:
            last_month_year = year
            last_month = month - 1
        
        # 获取前一个月的最后一天
        last_day = calendar.monthrange(last_month_year, last_month)[1]
        
        return f"{last_month_year:04d}{last_month:02d}{last_day:02d}"
    
    # ============ 时间格式转换工具（统一内部格式）============
    
    @staticmethod
    def to_standard_date(value: str, format_type: str) -> str:
        """
        将任意时间格式转换为标准date格式（YYYYMMDD）
        
        设计思想：
        - 内部统一使用YYYYMMDD格式
        - 边界转换：从存储格式/API格式 → YYYYMMDD
        
        Args:
            value: 时间值（如'2025Q3', '202510', '20251009'）
            format_type: 格式类型（'quarter', 'month', 'date'）
            
        Returns:
            str: 标准date格式（YYYYMMDD）
            
        示例：
            to_standard_date('2025Q3', 'quarter') → '20250930'
            to_standard_date('202510', 'month') → '20251031'
            to_standard_date('20251009', 'date') → '20251009'
        """
        if format_type == 'date':
            return value  # 已经是标准格式
        elif format_type == 'quarter':
            return DataSourceService.quarter_to_date(value)
        elif format_type == 'month':
            # month格式：YYYYMM → 该月最后一天
            import calendar
            year = int(value[:4])
            month = int(value[4:6])
            last_day = calendar.monthrange(year, month)[1]
            return f"{year:04d}{month:02d}{last_day:02d}"
        else:
            raise ValueError(f"不支持的时间格式: {format_type}")
    
    @staticmethod
    def from_standard_date(value: str, format_type: str) -> str:
        """
        将标准date格式（YYYYMMDD）转换为其他格式
        
        设计思想：
        - 内部统一使用YYYYMMDD格式
        - 边界转换：YYYYMMDD → 存储格式/API格式
        
        Args:
            value: 标准date格式（YYYYMMDD）
            format_type: 目标格式类型
            
        Returns:
            str: 转换后的格式
            
        示例：
            from_standard_date('20250930', 'quarter') → '2025Q3'
            from_standard_date('20251031', 'month') → '202510'
            from_standard_date('20251009', 'date') → '20251009'
        """
        if format_type == 'date':
            return value  # 保持原样
        elif format_type == 'quarter':
            return DataSourceService.date_to_quarter(value)
        elif format_type == 'month':
            # date → month（YYYYMMDD → YYYYMM）
            return value[:6]
        else:
            raise ValueError(f"不支持的时间格式: {format_type}")
    
    @staticmethod
    def get_previous_quarter_end(date_str: str) -> str:
        """
        获取指定日期所在季度的前一个季度的最后一天
        
        设计思想：返回标准date格式（YYYYMMDD），保持内部统一
        
        逻辑：
        1. 找到date所在季度
        2. 计算前一个季度
        3. 返回该季度的最后一天（YYYYMMDD）
        
        例如：
        - 20251009（2025Q4）→ 前一季度=2025Q3 → 返回 20250930
        - 20250315（2025Q1）→ 前一季度=2024Q4 → 返回 20241231
        - 20230630（2023Q2）→ 前一季度=2023Q1 → 返回 20230331
        
        Args:
            date_str: 日期字符串，格式YYYYMMDD
            
        Returns:
            str: 前一个季度的最后一天，格式YYYYMMDD
        """
        # 获取当前季度
        current_quarter = DataSourceService.date_to_quarter(date_str)
        
        # 解析季度
        year = int(current_quarter[:4])
        q = int(current_quarter[-1])
        
        # 前一个季度
        if q == 1:
            prev_year = year - 1
            prev_q = 4
        else:
            prev_year = year
            prev_q = q - 1
        
        prev_quarter = f"{prev_year}Q{prev_q}"
        
        # 转换为date格式（该季度的最后一天）
        return DataSourceService.quarter_to_date(prev_quarter)
    
    @staticmethod
    def to_next(interval: str, date_str: str) -> str:
        """
        根据指定的时间间隔计算下一个时间点
        
        Args:
            interval: 时间间隔类型，'day', 'week', 'month', 'quarter' 之一
            date_str: 日期字符串，格式为 YYYYMMDD（或 YYYYQN 当 interval='quarter'）
            
        Returns:
            str: 下一个时间点的日期（或季度）
        """
        if interval == 'day':
            return DataSourceService.to_next_day(date_str)
        elif interval == 'week':
            return DataSourceService.to_next_week(date_str)
        elif interval == 'month':
            return DataSourceService.to_next_month(date_str)
        elif interval == 'quarter':
            return DataSourceService.to_next_quarter(date_str)
        else:
            raise ValueError(f"不支持的时间间隔: {interval}")

    