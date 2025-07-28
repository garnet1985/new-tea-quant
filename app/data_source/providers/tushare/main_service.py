from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger
from app.data_source.providers.conf.conf import kline_terms, data_default_start_date

class TushareService:
    def __init__(self):
        self.latest_market_open_day_backward_checking_days = 15

    def normalize_stock_index_data(self, stock_index_data: list) -> list:
        """
        统一股票指数数据格式
        将API数据(包含ts_code)和数据库数据(包含code和market)统一为标准格式
        
        Args:
            stock_index_data: 股票指数数据列表
            
        Returns:
            list: 统一格式的股票指数数据，每个元素包含 code, market, ts_code
        """
        normalized_data = []
        
        for row in stock_index_data:
            if 'ts_code' in row:
                # API数据格式：包含ts_code字段
                ts_code = row['ts_code']
                code, market = ts_code.split('.', 1)
                normalized_row = {
                    'code': code,
                    'market': market,
                    'ts_code': ts_code,
                    'name': row.get('name', ''),
                    'industry': row.get('industry', ''),
                    'area': row.get('area', ''),
                    'exchange': row.get('exchange', ''),
                    'list_date': row.get('list_date', '')
                }
            else:
                # 数据库数据格式：包含code和market字段
                code = row['code']
                market = row['market']
                ts_code = f"{code}.{market}"
                normalized_row = {
                    'code': code,
                    'market': market,
                    'ts_code': ts_code,
                    'name': row.get('name', ''),
                    'industry': row.get('industry', ''),
                    'area': row.get('area', ''),
                    'exchange': row.get('exchangeCenter', ''),  # 数据库字段名不同
                    'list_date': row.get('list_date', '')
                }
            
            normalized_data.append(normalized_row)
        return normalized_data

    def get_latest_market_open_day(self, api):
        # 如果今天还没过去，那么最后一次交易日应该是昨天
        # 使用昨天作为结束日期来查询交易日历
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        end_date = yesterday.strftime('%Y%m%d')
        start_date = (yesterday - timedelta(days=self.latest_market_open_day_backward_checking_days)).strftime('%Y%m%d')

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

    def generate_kline_renew_jobs(self, stock_idx_info: list, last_market_open_day: str, storage) -> dict:
        
        stock_groups = defaultdict(list)
        most_recent_records = storage.get_most_recent_stock_kline_record_dates()
        
        for code, market in stock_idx_info:
            stock_key = f"{code}.{market}"
            stock_jobs = self.to_single_stock_kline_renew_job({
                'ts_code': self.to_ts_code(code, market),
                'code': code,
                'market': market
            }, most_recent_records, last_market_open_day)
            
            if stock_jobs:  # 只有当有任务时才添加到分组中
                stock_groups[stock_key] = stock_jobs
        
        return dict(stock_groups)


    def to_single_stock_kline_renew_job(self, stock_idx_info: dict, most_recent_records: dict, last_market_open_day: str) -> dict:
        jobs = []
        for term in kline_terms:
            job = self.to_single_stock_kline_renew_job_by_term(term, stock_idx_info, most_recent_records, last_market_open_day)
            if job:
                jobs.append(job)
        return jobs


    def to_single_stock_kline_renew_job_by_term(self, term: str, stock_idx_info: dict, most_recent_records: dict, latest_market_open_day: str) -> dict:
        # 获取该股票该周期的最新数据日期
        latest_date = most_recent_records.get(stock_idx_info['ts_code'], {}).get(term)

        if not latest_date:
            # 没有数据，使用默认开始日期
            return self.to_default_stock_kline_renew_job(stock_idx_info['code'], stock_idx_info['market'], term, latest_market_open_day)
            
        
        formatted_latest_record_date = datetime.strptime(latest_date, '%Y%m%d')
        formatted_latest_market_open_date = datetime.strptime(latest_market_open_day, '%Y%m%d')

        if term == 'daily':
            return self.to_single_stock_daily_kline_renew_job(stock_idx_info['code'], stock_idx_info['market'], latest_market_open_day, formatted_latest_record_date, formatted_latest_market_open_date)

        
        elif term == 'weekly':
            return self.to_single_stock_weekly_kline_renew_job(stock_idx_info['code'], stock_idx_info['market'], latest_market_open_day, formatted_latest_record_date, formatted_latest_market_open_date)

                
        elif term == 'monthly':
            return self.to_single_stock_monthly_kline_renew_job(stock_idx_info['code'], stock_idx_info['market'], latest_market_open_day, formatted_latest_record_date, formatted_latest_market_open_date)
        
        # 不需要更新
        return None

    def to_default_stock_kline_renew_job(self, code: str, market: str, term: str, last_market_open_day: str):
        return {
            'code': code,
            'market': market,
            'ts_code': self.to_ts_code(code, market),
            'term': term,
            'start_date': data_default_start_date,
            'end_date': last_market_open_day
        }

    def to_single_stock_daily_kline_renew_job(self, code: str, market: str, latest_market_open_day: str, formatted_latest_record_date: datetime, formatted_latest_market_open_date: datetime):
        # 只有当最新记录日期小于最后一次市场开放日期时才需要更新
        if formatted_latest_record_date < formatted_latest_market_open_date:
            start_date = (formatted_latest_record_date + timedelta(days=1)).strftime('%Y%m%d')
            return {
                'code': code,
                'market': market,
                'ts_code': self.to_ts_code(code, market),
                'term': 'daily',
                'start_date': start_date,
                'end_date': latest_market_open_day
            }
        else:
            return None

    def to_single_stock_weekly_kline_renew_job(self, code: str, market: str, latest_market_open_day: str, formatted_latest_record_date: datetime, formatted_latest_market_open_date: datetime):
        # 计算最新记录日期所在周的开始日期（周一）
        latest_week_start = formatted_latest_record_date - timedelta(days=formatted_latest_record_date.weekday())
        # 计算最后一次市场开放日期所在周的开始日期（周一）
        last_market_week_start = formatted_latest_market_open_date - timedelta(days=formatted_latest_market_open_date.weekday())
        
        # 只有当最新记录的周开始日期小于最后一次市场开放日期的周开始日期时才需要更新
        if latest_week_start < last_market_week_start:
            # 需要更新：从最新周的下一个周开始
            next_week_start = latest_week_start + timedelta(days=7)
            start_date = next_week_start.strftime('%Y%m%d')
            return {
                'code': code,
                'market': market,
                'ts_code': self.to_ts_code(code, market),
                'term': 'weekly',
                'start_date': start_date,
                'end_date': latest_market_open_day
            }
        else:
            return None

    def to_single_stock_monthly_kline_renew_job(self, code: str, market: str, latest_market_open_day: str, formatted_latest_record_date: datetime, formatted_latest_market_open_date: datetime):
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
                'code': code,
                'market': market,
                'ts_code': self.to_ts_code(code, market),
                'term': 'monthly',
                'start_date': start_date,
                'end_date': latest_market_open_day
            }
        else:
            return None

    def to_ts_code(self, code: str, market: str):
        return code + '.' + market

    def parse_ts_code(self, ts_code: str):
        return {
            'code': ts_code.split('.')[0],
            'market': ts_code.split('.')[1]
        }