"""
示例 Tag Calculator

继承 BaseTagCalculator，实现 calculate_tag 方法
支持一个 Calculator 打多个 Tag
"""
from typing import Dict, Any, Optional
from app.tag.base_tag_calculator import BaseTagCalculator


class ExampleCalculator(BaseTagCalculator):
    """示例 Tag Calculator - 市值分类"""
    
    def calculate_tag(
        self, 
        entity_id: str,
        entity_type: str,
        as_of_date: str, 
        historical_data: Dict[str, Any],
        tag_config: Dict[str, Any]
    ) -> Optional[Any]:
        """
        计算 tag
        
        Args:
            entity_id: 实体ID（如股票代码 "000001.SZ"）
            entity_type: 实体类型（如 "stock", "kline_daily" 等）
            as_of_date: 当前时间点（YYYYMMDD 格式，如 "20250101"）
            historical_data: 完整历史数据
                - klines: Dict[str, List[Dict]] - K线数据，key 是 term
                - finance: List[Dict] - 财务数据（如果有）
            tag_config: 当前 tag 的配置（已合并 calculator 和 tag 配置）
                - core: 合并后的 core 参数
                - tag_meta: tag 元信息（name, display_name, version 等）
        
        Returns:
            TagEntity 或 None（不创建 tag）
        """
        # 获取 tag 元信息
        tag_meta = tag_config.get("tag_meta", {})
        tag_name = tag_meta.get("name", "")
        tag_label = tag_config.get("core", {}).get("label", "")
        
        # 获取 calculator 级别的参数
        mkv_threshold = tag_config.get("core", {}).get("mkv_threshold", 0)
        
        # 示例：根据市值阈值判断
        # 注意：这里只是示例，实际需要从 historical_data 中获取市值数据
        # market_value = historical_data.get("market_value", {}).get("current", 0)
        
        # 示例逻辑：根据 tag label 判断
        if tag_label == "large":
            # 大市值逻辑
            # if market_value > mkv_threshold:
            #     return {"value": "1", "as_of_date": as_of_date}
            pass
        elif tag_label == "small":
            # 小市值逻辑
            # if market_value <= mkv_threshold:
            #     return {"value": "1", "as_of_date": as_of_date}
            pass
        
        # 示例：简单的动量计算（用于演示）
        daily_klines = historical_data.get("klines", {}).get("daily", [])
        if len(daily_klines) < 20:
            return None
        
        recent_close = daily_klines[-1].get("close", 0)
        past_close = daily_klines[-20].get("close", 0)
        
        if past_close == 0:
            return None
        
        momentum = (recent_close - past_close) / past_close
        
        # 创建 tag（这里返回一个简单的字典，实际应该返回 TagEntity）
        # TODO: 需要定义 TagEntity 类
        return {
            "value": str(momentum),
            "as_of_date": as_of_date,
        }
    
    def on_init(self):
        """初始化钩子"""
        # 可以在这里进行一些初始化操作
        # 例如：预加载数据、初始化缓存等
        pass
    
    def on_tag_created(self, tag_entity: Any, entity_id: str, as_of_date: str):
        """Tag 创建后钩子"""
        # 可以在这里记录日志、更新缓存等
        pass
