"""
Entity List Loader - 实体列表加载器

职责：
1. 解析需要打 tag 的实体列表
2. 支持多种实体类型（stock, macro, corporate_finance 等）
3. 提供统一的实体列表获取接口

当前仅支持 stock 实体，未来将扩展支持 macro、corporate_finance 等
"""
from typing import Dict, Any, List
import logging
from app.data_manager import DataManager

logger = logging.getLogger(__name__)


class EntityListLoader:
    """
    Entity List Loader - 实体列表加载器
    
    职责：
    1. 解析需要打 tag 的实体列表
    2. 支持多种实体类型（stock, macro, corporate_finance 等）
    3. 提供统一的实体列表获取接口
    
    实例类，可以缓存 DataManager 和相关的 data service 以便复用
    """
    
    def __init__(self):
        """
        初始化 EntityListLoader
        
        缓存 DataManager 以便复用
        """
        self.data_mgr = DataManager(is_verbose=False)
    
    def resolve_tagging_target_entity_list(self, scenario_setting: Dict[str, Any]) -> List[str]:
        """
        解析需要打 tag 的实体列表
        
        职责：
        1. 从 settings 中检查是否有配置实体列表（预留扩展）
        2. 如果没有配置，使用 DataManager 获取默认的股票列表
        3. 返回实体ID列表
        
        Args:
            scenario_setting: scenario_setting 字典，包含：
                - "scenario_name": str
                - "settings": Dict[str, Any]
        
        Returns:
            List[str]: 实体ID列表（如股票代码列表）
        """
        settings = scenario_setting.get("settings", {})
        calculator = settings.get("calculator", {})
        
        # TODO：current tagging only support stock entity，will support macro，corporate finance in the future
        
        # 预留：检查 settings 中是否有配置实体列表
        # 例如：calculator.get("entity_list") 或 calculator.get("entity_filter")
        # 目前暂不支持，直接使用默认逻辑
        
        # 使用 DataManager 获取股票列表
        if not self.data_mgr:
            raise ValueError("DataManager 未初始化，无法获取实体列表")
        
        try:
            # 使用 DataManager 的 load_stock_list 方法（使用过滤规则，排除ST、科创板等）
            stock_list = self.data_mgr.load_stock_list(filtered=True)
            
            if not stock_list:
                logger.warning("DataManager 返回的股票列表为空")
                return []
            
            # 提取股票ID列表
            entity_list = [stock.get('id') for stock in stock_list if stock.get('id')]
            
            logger.info(
                f"解析实体列表完成: scenario={scenario_setting['scenario_name']}, "
                f"entities={len(entity_list)}"
            )
            
            return entity_list
            
        except Exception as e:
            logger.error(f"获取实体列表失败: {e}", exc_info=True)
            # 备用方案：尝试使用 StockModel
            try:
                stock_model = self.data_mgr.get_model("stock_list")
                if stock_model:
                    stocks = stock_model.load_active_stocks()
                    entity_list = [stock.get('id') for stock in stocks if stock.get('id')]
                    logger.info(f"使用备用方案获取实体列表: {len(entity_list)} 个实体")
                    return entity_list
            except Exception as e2:
                logger.error(f"备用方案也失败: {e2}", exc_info=True)
            
            return []
