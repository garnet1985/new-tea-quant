"""
企业财务数据服务

提供财务指标的加载和查询功能，支持：
- 按股票代码和季度查询
- 按指标类别查询（盈利、成长、偿债、现金流等）
- 多季度趋势查询
"""

from typing import List, Dict, Any, Optional
from loguru import logger


from .. import BaseDataService


class CorporateFinanceService(BaseDataService):
    """
    企业财务数据服务
    
    财务指标分类：
    - 盈利能力：EPS、ROE、ROA、净利率、毛利率等
    - 成长能力：营收增长率、净利润增长率、EPS增长率等
    - 偿债能力：资产负债率、流动比率、速动比率等
    - 现金流：FCFF、FCFE、经营现金流等
    - 运营能力：应收账款周转率等
    - 资产状况：每股净资产等
    """
    
    # 指标分类映射
    INDICATOR_CATEGORIES = {
        'profitability': [  # 盈利能力
            'eps', 'dt_eps', 'roe_dt', 'roe', 'roa', 
            'netprofit_margin', 'gross_profit_margin', 'op_income',
            'roic', 'ebit', 'ebitda', 'dtprofit_to_profit', 'profit_dedt'
        ],
        'growth': [  # 成长能力
            'or_yoy', 'netprofit_yoy', 'basic_eps_yoy', 'dt_eps_yoy', 'tr_yoy'
        ],
        'solvency': [  # 偿债能力
            'netdebt', 'debt_to_eqt', 'debt_to_assets', 'interestdebt',
            'assets_to_eqt', 'quick_ratio', 'current_ratio'
        ],
        'cashflow': [  # 现金流
            'ocfps', 'fcff', 'fcfe'
        ],
        'operation': [  # 运营能力
            'ar_turn'
        ],
        'assets': [  # 资产状况
            'bps'
        ]
    }
    
    def __init__(self, data_manager):
        """
        初始化服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
        self._finance_model = None
    
    def _get_model(self):
        """获取财务数据 Model（延迟初始化）- 私有方法，内部使用"""
        if not self._finance_model:
            self._finance_model = self.data_manager.get_model('corporate_finance')
        return self._finance_model
    
    def load_financials(
        self, 
        ts_code: str, 
        quarter: str,
        indicators: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        加载指定股票和季度的财务数据
        
        Args:
            ts_code: 股票代码
            quarter: 季度，格式 YYYYQ[1-4]，例如 '2024Q1'
            indicators: 指定指标列表，默认返回所有指标
        
        Returns:
            财务数据字典，未找到返回 None
        """
        model = self._get_model()
        
        condition = "id = %s AND quarter = %s"
        params = (ts_code, quarter)
        results = model.load(condition, params, limit=1)
        
        if not results:
            return None
        
        data = results[0]
        
        # 如果指定了指标，只返回指定的字段
        if indicators:
            return {k: data.get(k) for k in indicators if k in data}
        
        return data
    
    def load_financials_by_category(
        self,
        ts_code: str,
        quarter: str,
        category: str
    ) -> Optional[Dict[str, Any]]:
        """
        按指标类别加载财务数据
        
        Args:
            ts_code: 股票代码
            quarter: 季度
            category: 指标类别
                - 'profitability': 盈利能力
                - 'growth': 成长能力
                - 'solvency': 偿债能力
                - 'cashflow': 现金流
                - 'operation': 运营能力
                - 'assets': 资产状况
        
        Returns:
            指定类别的财务指标字典
        """
        if category not in self.INDICATOR_CATEGORIES:
            logger.warning(f"未知的指标类别: {category}，可用: {list(self.INDICATOR_CATEGORIES.keys())}")
            return None
        
        indicators = self.INDICATOR_CATEGORIES[category]
        return self.load_financials(ts_code, quarter, indicators)
    
    def load_financials_trend(
        self,
        ts_code: str,
        start_quarter: str,
        end_quarter: str,
        indicators: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        加载多个季度的财务数据（用于趋势分析）
        
        Args:
            ts_code: 股票代码
            start_quarter: 起始季度，格式 YYYYQ[1-4]
            end_quarter: 结束季度，格式 YYYYQ[1-4]
            indicators: 指定指标列表，默认返回所有指标
        
        Returns:
            财务数据列表，按季度排序
        """
        model = self._get_model()
        
        condition = "id = %s AND quarter >= %s AND quarter <= %s"
        params = (ts_code, start_quarter, end_quarter)
        order_by = "quarter ASC"
        
        results = model.load(condition, params, order_by=order_by)
        
        # 如果指定了指标，只返回指定的字段
        if indicators and results:
            return [{k: data.get(k) for k in indicators if k in data} for data in results]
        
        return results
    
    def load_latest_financials(
        self,
        ts_code: str,
        indicators: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        加载最新的财务数据
        
        Args:
            ts_code: 股票代码
            indicators: 指定指标列表
        
        Returns:
            最新的财务数据
        """
        model = self._get_model()
        
        condition = "id = %s"
        params = (ts_code,)
        order_by = "quarter DESC"
        
        results = model.load(condition, params, order_by=order_by, limit=1)
        
        if not results:
            return None
        
        data = results[0]
        
        if indicators:
            return {k: data.get(k) for k in indicators if k in data}
        
        return data
    
    def save_financials(self, data: Dict[str, Any]) -> bool:
        """
        保存财务数据
        
        Args:
            data: 财务数据字典，必须包含 'id' 和 'quarter'
        
        Returns:
            是否保存成功
        """
        if 'id' not in data or 'quarter' not in data:
            logger.error("财务数据必须包含 'id' 和 'quarter' 字段")
            return False
        
        model = self._get_model()
        unique_keys = ['id', 'quarter']
        affected = model.replace([data], unique_keys)
        return affected >= 0
    
    def save_financials_batch(self, data_list: List[Dict[str, Any]]) -> bool:
        """
        批量保存财务数据
        
        Args:
            data_list: 财务数据列表
        
        Returns:
            是否保存成功
        """
        if not data_list:
            return True
        
        for data in data_list:
            if 'id' not in data or 'quarter' not in data:
                logger.error(f"财务数据缺少必要字段: {data}")
                return False
        
        model = self._get_model()
        unique_keys = ['id', 'quarter']
        affected = model.replace(data_list, unique_keys)
        return affected >= 0
    
    def load(
        self,
        stock_id: str,
        categories: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        加载企业财务数据（兼容接口）
        
        Args:
            stock_id: 股票代码
            categories: 指标类别列表（可选，如 ['profitability', 'growth']）
            start_date: 开始日期（YYYYMMDD 格式，可选）
            end_date: 结束日期（YYYYMMDD 格式，可选）
        
        Returns:
            Dict: 财务数据字典，按类别组织
        """
        model = self._get_model()
        result = {}
        
        # 如果提供了日期范围，需要转换为季度范围
        start_quarter = None
        end_quarter = None
        if start_date or end_date:
            # 将日期转换为季度
            if start_date:
                start_quarter = self._convert_date_to_quarter(start_date)
            if end_date:
                end_quarter = self._convert_date_to_quarter(end_date)
        else:
            # 如果没有提供日期，加载最新季度
            latest = self.load_latest_financials(stock_id)
            if latest:
                return latest
            return {}
        
        # 如果指定了类别，按类别加载
        if categories:
            for category in categories:
                if category in self.INDICATOR_CATEGORIES:
                    indicators = self.INDICATOR_CATEGORIES[category]
                    # 加载该类别的时间范围数据
                    if start_quarter and end_quarter:
                        trend_data = self.load_financials_trend(
                            stock_id, start_quarter, end_quarter, indicators
                        )
                        result[category] = trend_data
                    else:
                        # 只加载最新季度
                        latest = self.load_latest_financials(stock_id, indicators)
                        if latest:
                            result[category] = latest
        else:
            # 如果没有指定类别，加载所有数据
            if start_quarter and end_quarter:
                trend_data = self.load_financials_trend(
                    stock_id, start_quarter, end_quarter
                )
                result = trend_data[0] if trend_data else {}
            else:
                latest = self.load_latest_financials(stock_id)
                result = latest if latest else {}
        
        return result
    
    @staticmethod
    def _convert_date_to_quarter(date_str: str) -> Optional[str]:
        """
        将日期字符串转换为季度字符串
        
        Args:
            date_str: 日期字符串（YYYYMMDD 或 YYYY-MM-DD）
        
        Returns:
            季度字符串（YYYYQ[1-4]），如果转换失败返回 None
        """
        try:
            if '-' in date_str:
                date_str = date_str.replace('-', '')
            
            if len(date_str) != 8:
                return None
            
            year = int(date_str[:4])
            month = int(date_str[4:6])
            
            quarter = (month - 1) // 3 + 1
            return f"{year}Q{quarter}"
        except Exception as e:
            logger.warning(f"日期转季度失败: {date_str}, error={e}")
            return None


__all__ = ['CorporateFinanceDataService']

