"""
企业财务数据加载器
"""
from typing import List, Dict, Any, Optional
from loguru import logger


class CorporateFinanceLoader:
    """
    企业财务数据加载器
    
    职责：
    - 企业财务数据的读写操作
    - 企业财务数据的查询
    """
    
    def __init__(self, db=None):
        """
        初始化企业财务数据加载器
        
        Args:
            db: DatabaseManager实例，如果为None则自行创建
        """
        if db is not None:
            self.db = db
        else:
            from utils.db.db_manager import DatabaseManager
            self.db = DatabaseManager()
            self.db.initialize()
        
        self.corporate_finance_model = self.db.get_table_instance('corporate_finance')
    
    def load_all(self, stock_id: str, start_date: Optional[str] = None, 
                 end_date: Optional[str] = None) -> List[Dict]:
        """
        加载企业财务数据（所有字段）
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            end_date: 结束日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            
        Returns:
            List[Dict]: 企业财务数据列表，包含所有字段
        """
        return self.corporate_finance_model.load_all(stock_id, start_date, end_date)
    
    def load_growth_indicators(self, stock_id: str, start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> List[Dict]:
        """
        加载成长能力指标
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            end_date: 结束日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            
        Returns:
            List[Dict]: 成长能力指标数据，包含or_yoy, netprofit_yoy, basic_eps_yoy等字段
        """
        return self.corporate_finance_model.load_growth_indicators(stock_id, start_date, end_date)
    
    def load_profit_indicators(self, stock_id: str, start_date: Optional[str] = None,
                               end_date: Optional[str] = None) -> List[Dict]:
        """
        加载盈利能力指标
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            end_date: 结束日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            
        Returns:
            List[Dict]: 盈利能力指标数据，包含eps, roe, roa等字段
        """
        return self.corporate_finance_model.load_profit_indicators(stock_id, start_date, end_date)
    
    def load_cashflow_indicators(self, stock_id: str, start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> List[Dict]:
        """
        加载现金流状况指标
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            end_date: 结束日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            
        Returns:
            List[Dict]: 现金流状况指标数据，包含ocfps, fcff, fcfe等字段
        """
        return self.corporate_finance_model.load_cashflow_indicators(stock_id, start_date, end_date)
    
    def load_solvency_indicators(self, stock_id: str, start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> List[Dict]:
        """
        加载偿债能力指标
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            end_date: 结束日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            
        Returns:
            List[Dict]: 偿债能力指标数据，包含netdebt, debt_to_eqt, debt_to_assets等字段
        """
        return self.corporate_finance_model.load_solvency_indicators(stock_id, start_date, end_date)
    
    def load_operation_indicators(self, stock_id: str, start_date: Optional[str] = None,
                                  end_date: Optional[str] = None) -> List[Dict]:
        """
        加载运营能力指标
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            end_date: 结束日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            
        Returns:
            List[Dict]: 运营能力指标数据，包含ar_turn等字段
        """
        return self.corporate_finance_model.load_operation_indicators(stock_id, start_date, end_date)
    
    def load_asset_indicators(self, stock_id: str, start_date: Optional[str] = None,
                              end_date: Optional[str] = None) -> List[Dict]:
        """
        加载资产状况指标
        
        Args:
            stock_id: 股票代码
            start_date: 开始日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            end_date: 结束日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            
        Returns:
            List[Dict]: 资产状况指标数据，包含bps等字段
        """
        return self.corporate_finance_model.load_asset_indicators(stock_id, start_date, end_date)
    
    def load(self, stock_id: str, categories: List[str] = None, 
            start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        统一接口：根据类别加载企业财务数据
        
        Args:
            stock_id: 股票代码
            categories: 数据类别列表，支持：
                - 'growth': 成长能力指标
                - 'profit': 盈利能力指标
                - 'cashflow': 现金流状况指标
                - 'solvency': 偿债能力指标
                - 'operation': 运营能力指标
                - 'asset': 资产状况指标
                如果为None或空列表，则加载所有数据
            start_date: 开始日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            end_date: 结束日期（YYYYMMDD格式）或季度（YYYYQ[1-4]格式）
            
        Returns:
            Dict[str, List[Dict]]: 按类别组织的企业财务数据字典
            
        Raises:
            ValueError: 如果category不支持
        """
        result = {}
        
        # 如果没有指定类别或为空，加载所有数据
        if not categories:
            result['all'] = self.load_all(stock_id, start_date, end_date)
            return result
        
        # 类别映射
        category_map = {
            'growth': self.load_growth_indicators,
            'profit': self.load_profit_indicators,
            'cashflow': self.load_cashflow_indicators,
            'solvency': self.load_solvency_indicators,
            'operation': self.load_operation_indicators,
            'asset': self.load_asset_indicators,
        }
        
        # 加载指定类别的数据
        for category in categories:
            if category not in category_map:
                logger.warning(f"不支持的企业财务数据类别: {category}. 支持的类别: {list(category_map.keys())}")
                continue
            
            try:
                result[category] = category_map[category](stock_id, start_date, end_date)
            except Exception as e:
                logger.error(f"加载{category}数据失败 {stock_id}: {e}")
                result[category] = []
        
        return result

