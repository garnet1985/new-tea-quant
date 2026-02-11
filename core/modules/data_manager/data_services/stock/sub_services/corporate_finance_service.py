"""
企业财务数据服务

提供财务指标的加载和查询功能，支持：
- 按股票代码和季度查询
- 按指标类别查询（盈利、成长、偿债、现金流等）
- 多季度趋势查询
"""

from typing import List, Dict, Any, Optional
import logging

from core.utils.date.date_utils import DateUtils
from ... import BaseDataService


logger = logging.getLogger(__name__)


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
        """获取财务数据 Model（延迟初始化）"""
        if not self._finance_model:
            self._finance_model = self.data_manager.get_table("sys_corporate_finance")
        return self._finance_model
    
    def _filter_fields(self, data: Dict[str, Any], indicators: Optional[List[str]]) -> Dict[str, Any]:
        """
        过滤数据字段（通用方法）
        
        Args:
            data: 原始数据字典
            indicators: 需要保留的字段列表，如果为None返回所有字段
            
        Returns:
            过滤后的数据字典
        """
        if not indicators:
            return data
        return {k: data.get(k) for k in indicators if k in data}
    
    def _filter_fields_list(self, data_list: List[Dict[str, Any]], indicators: Optional[List[str]]) -> List[Dict[str, Any]]:
        """
        过滤数据列表的字段（通用方法）
        
        Args:
            data_list: 原始数据列表
            indicators: 需要保留的字段列表，如果为None返回所有字段
            
        Returns:
            过滤后的数据列表
        """
        if not indicators:
            return data_list
        return [self._filter_fields(data, indicators) for data in data_list]
    
    def _validate_financial_data(self, data: Dict[str, Any]) -> bool:
        """
        验证财务数据是否包含必要字段
        
        Args:
            data: 财务数据字典
            
        Returns:
            是否验证通过
        """
        if 'id' not in data or 'quarter' not in data:
            logger.error(f"财务数据缺少必要字段 'id' 或 'quarter': {data}")
            return False
        return True
    
    def load(
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
        return self._filter_fields(data, indicators)
    
    def load_by_category(
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
        return self.load(ts_code, quarter, indicators)
    
    def load_trend(
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
        return self._filter_fields_list(results, indicators)
    
    def load_latest(
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
        return self._filter_fields(data, indicators)
    
    def save(self, data: Dict[str, Any]) -> bool:
        """
        保存财务数据
        
        Args:
            data: 财务数据字典，必须包含 'id' 和 'quarter'
        
        Returns:
            是否保存成功
        """
        if not self._validate_financial_data(data):
            return False
        
        model = self._get_model()
        unique_keys = ['id', 'quarter']
        affected = model.upsert_one(data, unique_keys)
        return affected >= 0
    
    def save_batch(self, data_list: List[Dict[str, Any]]) -> int:
        """
        批量保存财务数据
        
        Args:
            data_list: 财务数据列表
        
        Returns:
            是否保存成功
        """
        if not data_list:
            return 0
        
        # 验证所有数据
        for data in data_list:
            if not self._validate_financial_data(data):
                return 0
        
        model = self._get_model()
        unique_keys = ['id', 'quarter']
        affected = model.upsert_many(data_list, unique_keys)
        # 返回受影响的记录数（与 tag_service.save_batch 的语义保持一致）
        return affected
    
    def get_stocks_latest_update_quarter(self) -> Dict[str, str]:
        """
        获取所有股票的最新财务数据更新季度
        
        查询逻辑：找出所有股票中，最新财务数据季度
        
        Returns:
            Dict[str, str]: 股票ID到最新季度的映射
                {
                    '000001.SZ': '2024Q3',
                    '000002.SZ': '2024Q2',
                    ...
                }
        """
        model = self._get_model()
        
        # 查询每个股票的最新季度
        # SQL: SELECT id, MAX(quarter) as last_updated_quarter FROM corporate_finance GROUP BY id
        query = f"""
            SELECT id, MAX(quarter) as last_updated_quarter
            FROM {model.table_name}
            GROUP BY id
        """
        
        try:
            results = model.db.execute_sync_query(query)
            if not results:
                return {}
            
            # 使用字典推导式简化
            return {
                row['id']: row['last_updated_quarter']
                for row in results
                if row.get('id')
            }
            
        except Exception as e:
            logger.error(f"查询企业财务数据股票列表失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
    
    def load_by_categories(
        self,
        stock_id: str,
        categories: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        按类别加载企业财务数据（兼容接口）
        
        Args:
            stock_id: 股票代码
            categories: 指标类别列表（可选，如 ['profitability', 'growth']）
            start_date: 开始日期（YYYYMMDD 格式，可选）
            end_date: 结束日期（YYYYMMDD 格式，可选）
        
        Returns:
            Dict: 财务数据字典，按类别组织
        """
        # 转换日期为季度范围
        start_quarter = self._convert_date_to_quarter(start_date) if start_date else None
        end_quarter = self._convert_date_to_quarter(end_date) if end_date else None
        has_date_range = start_quarter and end_quarter
        
        # 如果没有日期范围，直接返回最新数据
        if not has_date_range:
            if categories:
                # 按类别加载最新数据
                result = {}
                for category in categories:
                    if category in self.INDICATOR_CATEGORIES:
                        indicators = self.INDICATOR_CATEGORIES[category]
                        latest = self.load_latest(stock_id, indicators)
                        if latest:
                            result[category] = latest
                return result
            else:
                # 加载所有最新数据
                return self.load_latest(stock_id) or {}
        
        # 有日期范围，加载趋势数据
        if categories:
            # 按类别加载趋势数据
            result = {}
            for category in categories:
                if category in self.INDICATOR_CATEGORIES:
                    indicators = self.INDICATOR_CATEGORIES[category]
                    trend_data = self.load_trend(
                        stock_id, start_quarter, end_quarter, indicators
                    )
                    if trend_data:
                        result[category] = trend_data
            return result
        else:
            # 加载所有趋势数据
            trend_data = self.load_trend(
                stock_id, start_quarter, end_quarter
            )
            return trend_data[0] if trend_data else {}
    
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
            # 如果包含 '-'，先转换为 YYYYMMDD 格式
            if '-' in date_str:
                date_str = DateUtils.yyyy_mm_dd_to_yyyymmdd(date_str)
            
            # 使用 DateUtils 的 date_to_quarter 方法
            return DateUtils.date_to_quarter(date_str)
        except Exception as e:
            logger.warning(f"日期转季度失败: {date_str}, error={e}")
            return None


__all__ = ['CorporateFinanceService']

