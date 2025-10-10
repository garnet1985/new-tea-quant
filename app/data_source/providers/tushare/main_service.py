from datetime import datetime, timedelta
from collections import defaultdict
import math
from loguru import logger
from app.conf.conf import kline_terms, data_default_start_date
from .config import TushareConfig

class TushareService:
    @staticmethod
    def to_unified_stock_index_format(stock_index_data: list) -> list:
        """
        统一股票指数数据格式
        将API数据和数据库数据统一为标准格式
        
        Args:
            stock_index_data: 股票指数数据列表
            
        Returns:
            list: 统一格式的股票指数数据，每个元素包含 id, name, industry 等字段
        """
        normalized_data = []
        
        for row in stock_index_data:
            try:
                if 'ts_code' in row and row['ts_code']:
                    # API数据格式：包含ts_code字段
                    ts_code = row['ts_code']
                    
                    normalized_row = {
                        'id': ts_code,  # 使用 ts_code 作为 id
                        'ts_code': ts_code,
                        'name': row.get('name', ''),
                        'industry': row.get('industry', ''),
                        'area': row.get('area', ''),
                        'exchange': row.get('exchange', ''),
                        'list_date': row.get('list_date', '')
                    }
                elif 'id' in row and row['id']:
                    # 数据库数据格式：包含id字段
                    stock_id = row['id']
                    normalized_row = {
                        'id': stock_id,
                        'ts_code': stock_id,
                        'name': row.get('name', ''),
                        'industry': row.get('industry', ''),
                        'area': row.get('area', ''),
                        'exchange': row.get('exchange_center', ''),  # 数据库字段名不同
                        'list_date': row.get('list_date', '')
                    }
                else:
                    # 数据不完整，跳过这条记录
                    continue
                
                normalized_data.append(normalized_row)
                
            except Exception as e:
                # 记录错误但继续处理其他记录
                logger.warning(f"处理股票指数数据时出错: {e}, 数据: {row}")
                continue
                
        return normalized_data

    @staticmethod
    def get_latest_market_open_day(api):
        # 如果今天还没过去，那么最后一次交易日应该是昨天
        # 使用昨天作为结束日期来查询交易日历
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        end_date = yesterday.strftime('%Y%m%d')
        start_date = (yesterday - timedelta(days=TushareConfig.latest_market_open_day_backward_checking_days)).strftime('%Y%m%d')

        dates = api.trade_cal(exchange='', start_date=start_date, end_date=end_date)
        # 检查返回的字段名
        if 'is_open' in dates.columns:
            last_market_open_day = dates[dates['is_open'] == 1]['cal_date'].max()
        elif 'is_open' in dates.columns:
            last_market_open_day = dates[dates['is_open'] == 1]['cal_date'].max()
        else:
            # 如果字段名不匹配，使用昨天作为默认值
            logger.warning("无法获取交易日历，使用昨天作为默认值")
            last_market_open_day = yesterday.strftime('%Y%m%d')
        return last_market_open_day

    @staticmethod
    def generate_kline_renew_jobs(stock_idx_info: list, last_market_open_day: str, storage) -> dict:
        
        stock_groups = defaultdict(list)
        most_recent_records = storage.get_most_recent_stock_kline_record_dates()
        
        for ts_code in stock_idx_info:
            stock_jobs = TushareService.to_single_stock_kline_renew_job({
                'ts_code': ts_code
            }, most_recent_records, last_market_open_day)
            
            if stock_jobs:  # 只有当有任务时才添加到分组中
                stock_groups[ts_code] = stock_jobs
        
        return dict(stock_groups)


    @staticmethod
    def to_single_stock_kline_renew_job(stock_idx_info: dict, most_recent_records: dict, last_market_open_day: str) -> dict:
        jobs = []
        for term in kline_terms:
            job = TushareService.to_single_stock_kline_renew_job_by_term(term, stock_idx_info, most_recent_records, last_market_open_day)
            if job:
                jobs.append(job)
        return jobs


    @staticmethod
    def to_single_stock_kline_renew_job_by_term(term: str, stock_idx_info: dict, most_recent_records: dict, latest_market_open_day: str) -> dict:
        # 获取该股票该周期的最新数据日期
        latest_date = most_recent_records.get(stock_idx_info['ts_code'], {}).get(term)

        if not latest_date:
            # 没有数据，使用默认开始日期
            return TushareService.to_default_stock_kline_renew_job(stock_idx_info['ts_code'], term, latest_market_open_day)
            
        
        formatted_latest_record_date = datetime.strptime(latest_date, '%Y%m%d')
        formatted_latest_market_open_date = datetime.strptime(latest_market_open_day, '%Y%m%d')

        if term == 'daily':
            return TushareService.to_single_stock_daily_kline_renew_job(stock_idx_info['ts_code'], latest_market_open_day, formatted_latest_record_date, formatted_latest_market_open_date)

        
        elif term == 'weekly':
            return TushareService.to_single_stock_weekly_kline_renew_job(stock_idx_info['ts_code'], latest_market_open_day, formatted_latest_record_date, formatted_latest_market_open_date)

                
        elif term == 'monthly':
            return TushareService.to_single_stock_monthly_kline_renew_job(stock_idx_info['ts_code'], latest_market_open_day, formatted_latest_record_date, formatted_latest_market_open_date)
        
        # 不需要更新
        return None

    @staticmethod
    def to_default_stock_kline_renew_job(ts_code: str, term: str, last_market_open_day: str):
        return {
            'ts_code': ts_code,
            'term': term,
            'start_date': data_default_start_date,
            'end_date': last_market_open_day
        }

    @staticmethod
    def to_single_stock_daily_kline_renew_job(ts_code: str, latest_market_open_day: str, formatted_latest_record_date: datetime, formatted_latest_market_open_date: datetime):
        # 只有当最新记录日期小于最后一次市场开放日期时才需要更新

        if formatted_latest_record_date < formatted_latest_market_open_date:
            start_date = (formatted_latest_record_date + timedelta(days=1)).strftime('%Y%m%d')
            return {
                'ts_code': ts_code,
                'term': 'daily',
                'start_date': start_date,
                'end_date': latest_market_open_day
            }
        else:
            return None

    @staticmethod
    def to_single_stock_weekly_kline_renew_job(ts_code: str, latest_market_open_day: str, formatted_latest_record_date: datetime, formatted_latest_market_open_date: datetime):
        # 周线数据通常在每周结束后更新（周五）
        # 只有当最新记录日期加两周后的周一已经到来时，才需要更新
        # 例如：如果最新记录是7月25日（周五），那么至少要到8月8日（周一）才考虑更新
        
        # 计算最新记录日期加两周后的周一
        two_weeks_later_monday = formatted_latest_record_date + timedelta(days=14 - formatted_latest_record_date.weekday())
        
        # 只有当最新市场开放日期大于等于两周后的周一时，才需要更新
        if formatted_latest_market_open_date >= two_weeks_later_monday:
            # 需要更新：从最新周的下一个周开始
            next_week_start = formatted_latest_record_date + timedelta(days=7 - formatted_latest_record_date.weekday())
            start_date = next_week_start.strftime('%Y%m%d')
            return {
                'ts_code': ts_code,
                'term': 'weekly',
                'start_date': start_date,
                'end_date': latest_market_open_day
            }
        
        return None

    @staticmethod
    def to_single_stock_monthly_kline_renew_job(ts_code: str, latest_market_open_day: str, formatted_latest_record_date: datetime, formatted_latest_market_open_date: datetime):
        # 月线数据通常在月底生成，包含整个月的数据
        # 如果最新记录是某月30日，那么至少要到该月加两个月后的第一天才考虑更新
        # 例如：如果最新记录是6月30日，那么至少要到8月1日才考虑更新7月的月线数据
        
        # 计算最新记录日期加两个月后的第一天
        if formatted_latest_record_date.month >= 11:  # 11月或12月
            next_month_year = formatted_latest_record_date.year + 1
            next_month_month = formatted_latest_record_date.month - 10  # 11->1, 12->2
        else:
            next_month_year = formatted_latest_record_date.year
            next_month_month = formatted_latest_record_date.month + 2
        
        # 计算两个月后的第一天
        two_months_later_start = datetime(next_month_year, next_month_month, 1)
        
        # 只有当最后一次市场开放日期大于等于两个月后的第一天时，才需要更新
        if formatted_latest_market_open_date >= two_months_later_start:
            # 需要更新：从最新月的下一个月开始
            if formatted_latest_record_date.month == 12:
                next_month_start = formatted_latest_record_date.replace(year=formatted_latest_record_date.year + 1, month=1, day=1)
            else:
                next_month_start = formatted_latest_record_date.replace(month=formatted_latest_record_date.month + 1, day=1)
            start_date = next_month_start.strftime('%Y%m%d')
            return {
                'ts_code': ts_code,
                'term': 'monthly',
                'start_date': start_date,
                'end_date': latest_market_open_day
            }
        else:
            return None


    @staticmethod
    def to_yyyymm(d: str) -> str:
        d = (d or '').strip()
        if not d:
            return ''
        for fmt in ('%Y%m%d', '%Y-%m-%d', '%Y/%m/%d', '%Y%m'):
            try:
                return datetime.strptime(d, fmt).strftime('%Y%m')
            except ValueError:
                continue
        return ''

    @staticmethod
    def to_date(d: str) -> datetime:
        if d is None:
            return None
        if isinstance(d, datetime):
            return d
        s = str(d).strip()
        if not s:
            return None
        return datetime.strptime(s, '%Y%m%d')

    @staticmethod
    def safe_to_float(x, default=0.0):
        try:
            if x is None or (isinstance(x, float) and math.isnan(x)):
                return default
            return float(x)
        except Exception:
            return default

    @staticmethod
    def to_quarter(d: str) -> str:
        """
        将日期转换为季度标识。输入支持：YYYYMMDD 或 YYYY-MM-DD 或 YYYY/MM/DD 或 YYYYMM
        输出：YYYYQ{N}，N∈{1,2,3,4}
        """
        from datetime import datetime
        s = (d or '').strip()
        if not s:
            return ''
        # 规范化为 datetime
        dt = None
        for fmt in ('%Y%m%d', '%Y-%m-%d', '%Y/%m/%d', '%Y%m'):
            try:
                dt = datetime.strptime(s, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            return ''
        month = dt.month
        q = (month - 1) // 3 + 1
        return f"{dt.year}Q{q}"
    
    @staticmethod
    def generate_quarter_range(start_quarter: str, end_quarter: str) -> list:
        """
        生成季度范围列表
        
        Args:
            start_quarter: 开始季度，格式 YYYYQ{N}
            end_quarter: 结束季度，格式 YYYYQ{N}
            
        Returns:
            list: 季度列表
        """
        quarters = []
        current = start_quarter
        
        while current <= end_quarter:
            quarters.append(current)
            current = TushareService.get_next_quarter(current)
            if not current:
                break
        
        return quarters

    @staticmethod
    def get_next_quarter(quarter: str) -> str:
        """
        获取下一个季度
        
        Args:
            quarter: 季度，格式 YYYYQ{N}
            
        Returns:
            str: 下一个季度，格式 YYYYQ{N}
        """
        if not quarter or len(quarter) != 6:
            return None
        
        try:
            year = int(quarter[:4])
            q_num = int(quarter[5])
            
            # 如果是第四季度，则返回下一年的第一季度
            if q_num == 4:
                next_year = year + 1
                return f"{next_year}Q1"
            else:
                next_q = q_num + 1
                return f"{year}Q{next_q}"
                
        except (ValueError, IndexError):
            return None

    @staticmethod
    def get_previous_quarter(quarter: str) -> str:
        """
        获取上一个季度
        
        Args:
            quarter: 季度，格式 YYYYQ{N}
            
        Returns:
            str: 上一个季度，格式 YYYYQ{N}
        """
        if not quarter or len(quarter) != 6:
            return None
        
        try:
            year = int(quarter[:4])
            q_num = int(quarter[5])
            
            # 如果是第一季度，则返回上一年的第四季度
            if q_num == 1:
                prev_year = year - 1
                return f"{prev_year}Q4"
            else:
                prev_q = q_num - 1
                return f"{year}Q{prev_q}"
                
        except (ValueError, IndexError):
            return None

    @staticmethod
    def quarter_to_date_range(quarter: str):
        """
        将季度转换为日期范围
        
        Args:
            quarter: 季度，格式 YYYYQ{N}
            
        Returns:
            tuple: (start_date, end_date) 格式为 YYYYMMDD
        """
        if not quarter or len(quarter) != 6:
            return None, None
        
        try:
            year = int(quarter[:4])
            q_num = int(quarter[5])
            
            # 计算季度的开始和结束月份
            if q_num == 1:
                start_month = 1
                end_month = 3
            elif q_num == 2:
                start_month = 4
                end_month = 6
            elif q_num == 3:
                start_month = 7
                end_month = 9
            elif q_num == 4:
                start_month = 10
                end_month = 12
            else:
                return None, None
            
            # 计算日期
            start_date = f"{year}{start_month:02d}01"
            
            # 计算结束月份的最后一天
            if end_month in [1, 3, 5, 7, 8, 10, 12]:
                last_day = 31
            elif end_month in [4, 6, 9, 11]:
                last_day = 30
            else:  # 2月
                # 简单处理，不考虑闰年
                last_day = 28
            
            end_date = f"{year}{end_month:02d}{last_day:02d}"
            
            return start_date, end_date
            
        except (ValueError, IndexError):
            return None, None