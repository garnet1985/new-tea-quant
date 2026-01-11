"""
DataService - 跨service协调器

职责：
1. 管理各个子 Service（stock, macro, calendar）
2. 提供跨service方法（如 prepare_data）
3. 统一访问入口
"""
from typing import Dict, List, Any, Optional
from loguru import logger

from . import BaseDataService


class DataService:
    """
    DataService 主类，管理所有子 Service
    
    使用方式：
        data_service = DataService(data_manager)
        klines = data_service.stock.load_klines('000001.SZ')
        gdp = data_service.macro.load_gdp('2020Q1', '2024Q4')
        latest_date = data_service.calendar.get_latest_trading_date()
    """
    
    def __init__(self, data_manager):
        """
        初始化 DataService
        
        Args:
            data_manager: DataManager 实例
        """
        self.data_manager = data_manager
        
        # 初始化各个子 Service
        from .stock.stock_service import StockService
        from .macro.macro_service import MacroService
        from .calendar.calendar_service import CalendarService
        
        self.stock = StockService(data_manager)
        self.macro = MacroService(data_manager)
        self.calendar = CalendarService(data_manager)
    
    def prepare_data(self, stock: Dict[str, Any], settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        配置驱动的数据准备（跨service协调）
        
        根据 settings 配置，协调多个 Service 加载所需数据
        
        Args:
            stock: 股票信息
            settings: 数据设置（包含klines、macro、corporate_finance等配置）
            
        Returns:
            Dict: {
                'klines': {...},
                'macro': {...},
                'corporate_finance': {...},
                'labels': {...},
                ...
            }
        """
        data = {}
        stock_id = stock.get('id')
        
        # 1. 加载K线数据
        klines_settings = settings.get("klines")
        if klines_settings:
            # 将 simulation 中的 start_date 和 end_date 传递给 klines_settings
            klines_settings_with_dates = klines_settings.copy()
            simulation_settings = settings.get("simulation", {})
            if simulation_settings.get('start_date') and 'start_date' not in klines_settings_with_dates:
                klines_settings_with_dates['start_date'] = simulation_settings['start_date']
            if simulation_settings.get('end_date') and 'end_date' not in klines_settings_with_dates:
                klines_settings_with_dates['end_date'] = simulation_settings['end_date']
            
            # 使用 stock.kline 加载多周期K线
            data["klines"] = self.stock.kline.load_multiple_terms(stock_id, klines_settings_with_dates)
            
            # 确保返回dict类型
            if not isinstance(data.get("klines"), dict):
                data["klines"] = {}
            
            # 应用技术指标（如果配置）
            if data["klines"] and klines_settings.get('indicators'):
                from app.core.modules.indicator import IndicatorService
                data["klines"] = IndicatorService.add_indicators(data["klines"], klines_settings['indicators'])
        
        # 2. 加载宏观数据
        macro_settings = settings.get("macro")
        if macro_settings:
            data["macro"] = self._load_macro_data(macro_settings)
        
        # 3. 加载企业财务数据
        corporate_finance_settings = settings.get("corporate_finance")
        if corporate_finance_settings:
            categories = corporate_finance_settings.get('categories')
            start_date = corporate_finance_settings.get('start_date')
            end_date = corporate_finance_settings.get('end_date')
            data["corporate_finance"] = self.stock.corporate_finance.load(
                stock_id, categories, start_date, end_date
            )
        
        # 4. 加载指数指标数据（暂未实现）
        index_indicators_settings = settings.get("index_indicators")
        if index_indicators_settings:
            logger.warning("index_indicators 暂未实现")
            data["index_indicators"] = {}
        
        return data
    
    def _load_macro_data(self, macro_settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        加载宏观数据（委托给 MacroService）
        
        Args:
            macro_settings: 宏观数据配置
            
        Returns:
            Dict: 包含各类宏观数据的字典
        """
        result = {}
        
        # 提取通用的日期参数
        start_date = macro_settings.get('start_date', '')
        end_date = macro_settings.get('end_date', '')
        start_date = None if not start_date else start_date
        end_date = None if not end_date else end_date
        
        # GDP
        if macro_settings.get('GDP', False):
            start_quarter = None
            end_quarter = None
            if start_date:
                start_quarter = self._convert_date_to_quarter(start_date)
            if end_date:
                end_quarter = self._convert_date_to_quarter(end_date)
            result['GDP'] = self.macro.load_gdp(start_quarter, end_quarter)
        
        # LPR
        if macro_settings.get('LPR', False):
            result['LPR'] = self.macro.load_lpr(start_date, end_date)
        
        # Shibor
        if macro_settings.get('Shibor', False):
            result['Shibor'] = self.macro.load_shibor(start_date, end_date)
        
        # 价格指数
        price_indexes = macro_settings.get('price_indexes', [])
        if price_indexes:
            result['price_indexes'] = {}
            for index_name in price_indexes:
                if index_name == 'CPI':
                    result['price_indexes']['CPI'] = self.macro.load_cpi(start_date, end_date)
                elif index_name == 'PPI':
                    result['price_indexes']['PPI'] = self.macro.load_ppi(start_date, end_date)
                elif index_name == 'PMI':
                    result['price_indexes']['PMI'] = self.macro.load_pmi(start_date, end_date)
                elif index_name == 'MoneySupply':
                    result['price_indexes']['MoneySupply'] = self.macro.load_money_supply(start_date, end_date)
        
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
            # 统一格式处理
            if '-' in date_str:
                date_str = date_str.replace('-', '')
            
            if len(date_str) != 8:
                return None
            
            year = int(date_str[:4])
            month = int(date_str[4:6])
            
            # 计算季度
            quarter = (month - 1) // 3 + 1
            return f"{year}Q{quarter}"
        except Exception as e:
            logger.warning(f"日期转季度失败: {date_str}, error={e}")
            return None
