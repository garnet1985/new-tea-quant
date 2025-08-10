from datetime import date as date_type

class DataSourceService:
    @staticmethod
    def to_ts_code(code: str, market: str):
        return f"{code}.{market}"
    
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
        print(qfq_factors)
        pass

    