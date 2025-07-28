from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger
from app.data_source.providers.conf.conf import kline_terms, data_default_start_date

class TushareService:
    def __init__(self):
        self.latest_market_open_day_backward_checking_days = 15

    def get_latest_market_open_day(self, api):

        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=self.latest_market_open_day_backward_checking_days)).strftime('%Y%m%d')

        dates = api.trade_cal(exchange='', start_date=start_date, end_date=end_date)
        # 检查返回的字段名
        if 'is_open' in dates.columns:
            last_market_open_day = dates[dates['is_open'] == 1]['cal_date'].max()
        elif 'is_open' in dates.columns:
            last_market_open_day = dates[dates['is_open'] == 1]['cal_date'].max()
        else:
            # 如果字段名不匹配，使用当前日期作为默认值
            logger.warning("无法获取交易日历，使用当前日期作为默认值")
            last_market_open_day = datetime.now().strftime('%Y%m%d')
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
            return self.to_default_stock_daily_kline_renew_job(stock_idx_info['code'], stock_idx_info['market'], latest_market_open_day)
            
        
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

    def to_default_stock_daily_kline_renew_job(self, code: str, market: str, last_market_open_day: str):
        return {
            'code': code,
            'market': market,
            'ts_code': self.to_ts_code(code, market),
            'term': 'daily',
            'start_date': data_default_start_date,
            'end_date': last_market_open_day
        }

    def to_single_stock_daily_kline_renew_job(self, code: str, market: str, latest_market_open_day: str, formatted_latest_record_date: datetime, formatted_latest_market_open_date: datetime):
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
        latest_week_start = formatted_latest_record_date - timedelta(days=formatted_latest_record_date.weekday())
        last_market_week_start = formatted_latest_market_open_date - timedelta(days=formatted_latest_market_open_date.weekday())
        
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
        latest_month_start = formatted_latest_record_date.replace(day=1)
        last_market_month_start = formatted_latest_market_open_date.replace(day=1)
        
        if latest_month_start < last_market_month_start:
            # 需要更新：从最新月的下一个月开始
            if latest_month_start.month == 12:
                next_month_start = latest_month_start.replace(year=latest_month_start.year + 1, month=1)
            else:
                next_month_start = latest_month_start.replace(month=latest_month_start.month + 1)
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