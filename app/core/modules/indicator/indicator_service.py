#!/usr/bin/env python3
"""
Indicator Service - 技术指标计算服务

职责：
- 作为 pandas-ta-classic 的 proxy
- 转换数据格式（List[Dict] <-> DataFrame）
- 提供便捷 API（常用指标）
- 支持通用调用（所有 150+ 指标）

设计：
- 静态工具类
- 不缓存（按需计算）
- 轻量级（只做数据转换和代理）
"""

from typing import List, Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


class IndicatorService:
    """
    技术指标计算服务（静态工具类）
    
    核心设计：
    1. Proxy 模式：转发调用到 pandas-ta-classic
    2. 数据转换：List[Dict] <-> DataFrame
    3. 便捷 API：暴露常用指标
    4. 通用 API：支持所有指标
    
    使用示例：
        # 方式1: 便捷API（推荐）
        ma20 = IndicatorService.ma(klines, length=20)
        rsi = IndicatorService.rsi(klines, length=14)
        
        # 方式2: 通用API（支持所有指标）
        ma20 = IndicatorService.calculate('sma', klines, length=20)
        bbands = IndicatorService.calculate('bbands', klines, length=20, std=2)
    """
    
    _ta = None  # pandas-ta-classic 模块（延迟加载）
    
    # =========================================================================
    # 核心方法
    # =========================================================================
    
    @classmethod
    def calculate(
        cls, 
        indicator_name: str, 
        klines: List[Dict[str, Any]], 
        **params
    ) -> Union[List[float], Dict[str, List[float]], None]:
        """
        通用计算接口（支持 pandas-ta-classic 的所有 150+ 指标）
        
        这是一个 proxy 方法，直接转发到 pandas-ta-classic
        
        Args:
            indicator_name: 指标名称（pandas-ta 的方法名，如 'sma', 'rsi', 'macd'）
            klines: K线数据 [{'date': '20251219', 'open': 10, 'close': 10.5, ...}, ...]
            **params: 指标参数（传递给 pandas-ta 的参数）
        
        Returns:
            - 单列指标: List[float] - 如 MA, RSI
            - 多列指标: Dict[str, List[float]] - 如 MACD, BBANDS
            - 失败: None
        
        示例：
            # 单列指标
            ma20 = IndicatorService.calculate('sma', klines, length=20)
            
            # 多列指标
            macd = IndicatorService.calculate('macd', klines, fast=12, slow=26, signal=9)
            # 返回: {'MACD_12_26_9': [...], 'MACDs_12_26_9': [...], 'MACDh_12_26_9': [...]}
            
            # 布林带
            bbands = IndicatorService.calculate('bbands', klines, length=20, std=2)
            # 返回: {'BBL_20_2.0': [...], 'BBM_20_2.0': [...], 'BBU_20_2.0': [...]}
        """
        try:
            # 1. 延迟加载 pandas-ta
            if cls._ta is None:
                cls._init_ta()
            
            # 2. 检查指标是否存在
            if not hasattr(cls._ta, indicator_name):
                logger.error(f"不支持的指标: {indicator_name}")
                return None
            
            # 3. 转换数据格式（List[Dict] -> DataFrame）
            df = cls._klines_to_dataframe(klines)
            
            if df is None or df.empty:
                logger.warning(f"K线数据为空或转换失败")
                return None
            
            # 4. 调用 pandas-ta 指标方法
            indicator_func = getattr(cls._ta, indicator_name)
            result = indicator_func(
                high=df['high'],
                low=df['low'],
                close=df['close'],
                volume=df.get('volume'),
                open_=df['open'],
                **params
            )
            
            # 5. 转换返回格式
            return cls._result_to_list(result)
        
        except Exception as e:
            logger.error(
                f"计算指标失败: indicator={indicator_name}, "
                f"params={params}, error={e}",
                exc_info=True
            )
            return None
    
    # =========================================================================
    # 便捷 API（常用指标）
    # =========================================================================
    
    @classmethod
    def ma(cls, klines: List[Dict[str, Any]], length: int = 20) -> Optional[List[float]]:
        """
        简单移动平均线（SMA）
        
        Args:
            klines: K线数据
            length: 周期（默认20）
        
        Returns:
            List[float]: MA值列表
        """
        return cls.calculate('sma', klines, length=length)
    
    @classmethod
    def ema(cls, klines: List[Dict[str, Any]], length: int = 20) -> Optional[List[float]]:
        """
        指数移动平均线（EMA）
        
        Args:
            klines: K线数据
            length: 周期（默认20）
        
        Returns:
            List[float]: EMA值列表
        """
        return cls.calculate('ema', klines, length=length)
    
    @classmethod
    def rsi(cls, klines: List[Dict[str, Any]], length: int = 14) -> Optional[List[float]]:
        """
        相对强弱指标（RSI）
        
        Args:
            klines: K线数据
            length: 周期（默认14）
        
        Returns:
            List[float]: RSI值列表（0-100）
        """
        # RSI 只依赖收盘价，为了兼容只有 close / highest / lowest 的数据，单独实现，
        # 避免 _klines_to_dataframe 对 high/low/open 的强依赖。
        try:
            cls._init_ta()
            import pandas as pd

            if not klines:
                return None

            # 提取收盘价序列
            closes = [k.get("close") for k in klines if "close" in k]
            if not closes:
                logger.error("K线数据缺少必要列: close")
                return None

            close_series = pd.Series(closes)
            result = cls._ta.rsi(close_series, length=length)
            return cls._result_to_list(result)
        except Exception as e:
            logger.error(f"RSI 计算失败: {e}")
            return None
    
    @classmethod
    def macd(
        cls, 
        klines: List[Dict[str, Any]], 
        fast: int = 12, 
        slow: int = 26, 
        signal: int = 9
    ) -> Optional[Dict[str, List[float]]]:
        """
        MACD 指标
        
        Args:
            klines: K线数据
            fast: 快线周期（默认12）
            slow: 慢线周期（默认26）
            signal: 信号线周期（默认9）
        
        Returns:
            Dict: {
                'MACD_12_26_9': [...],    # MACD线
                'MACDs_12_26_9': [...],   # 信号线
                'MACDh_12_26_9': [...]    # 柱状图
            }
        """
        return cls.calculate('macd', klines, fast=fast, slow=slow, signal=signal)
    
    @classmethod
    def bbands(
        cls, 
        klines: List[Dict[str, Any]], 
        length: int = 20, 
        std: float = 2.0
    ) -> Optional[Dict[str, List[float]]]:
        """
        布林带（Bollinger Bands）
        
        Args:
            klines: K线数据
            length: 周期（默认20）
            std: 标准差倍数（默认2.0）
        
        Returns:
            Dict: {
                'BBL_20_2.0': [...],  # 下轨
                'BBM_20_2.0': [...],  # 中轨
                'BBU_20_2.0': [...]   # 上轨
            }
        """
        return cls.calculate('bbands', klines, length=length, std=std)
    
    @classmethod
    def atr(cls, klines: List[Dict[str, Any]], length: int = 14) -> Optional[List[float]]:
        """
        真实波动幅度（ATR）
        
        Args:
            klines: K线数据
            length: 周期（默认14）
        
        Returns:
            List[float]: ATR值列表
        """
        return cls.calculate('atr', klines, length=length)
    
    @classmethod
    def stoch(
        cls, 
        klines: List[Dict[str, Any]], 
        k: int = 14, 
        d: int = 3, 
        smooth_k: int = 3
    ) -> Optional[Dict[str, List[float]]]:
        """
        随机指标（KDJ）
        
        Args:
            klines: K线数据
            k: K线周期（默认14）
            d: D线周期（默认3）
            smooth_k: K线平滑周期（默认3）
        
        Returns:
            Dict: {
                'STOCHk_14_3_3': [...],  # K线
                'STOCHd_14_3_3': [...]   # D线
            }
        """
        return cls.calculate('stoch', klines, k=k, d=d, smooth_k=smooth_k)
    
    @classmethod
    def adx(cls, klines: List[Dict[str, Any]], length: int = 14) -> Optional[List[float]]:
        """
        平均趋向指数（ADX）
        
        Args:
            klines: K线数据
            length: 周期（默认14）
        
        Returns:
            List[float]: ADX值列表
        """
        return cls.calculate('adx', klines, length=length)
    
    @classmethod
    def obv(cls, klines: List[Dict[str, Any]]) -> Optional[List[float]]:
        """
        能量潮（OBV）
        
        Args:
            klines: K线数据
        
        Returns:
            List[float]: OBV值列表
        """
        return cls.calculate('obv', klines)
    
    # =========================================================================
    # 私有方法
    # =========================================================================
    
    @classmethod
    def _init_ta(cls):
        """延迟加载 pandas-ta-classic"""
        try:
            import pandas_ta_classic as ta
            cls._ta = ta
            logger.info("✅ pandas-ta-classic 加载成功")
        except ImportError as e:
            logger.error(
                "❌ pandas-ta-classic 未安装，请运行: "
                "pip install pandas-ta-classic"
            )
            raise ImportError(
                "pandas-ta-classic 未安装，请运行: pip install pandas-ta-classic"
            ) from e
    
    @classmethod
    def _klines_to_dataframe(cls, klines: List[Dict[str, Any]]):
        """
        转换 K线数据格式：List[Dict] -> DataFrame
        
        Args:
            klines: [
                {'date': '20251219', 'open': 10, 'high': 10.5, 'low': 9.8, 'close': 10.2, 'volume': 1000},
                ...
            ]
        
        Returns:
            DataFrame with columns: ['open', 'high', 'low', 'close', 'volume']
        """
        try:
            import pandas as pd
            
            if not klines:
                return None
            
            df = pd.DataFrame(klines)

            # 兼容 legacy 字段名：highest/lowest -> high/low
            # schema 中字段为 highest/lowest，但技术指标和 pandas-ta 习惯使用 high/low
            if 'high' not in df.columns and 'highest' in df.columns:
                df['high'] = df['highest']
            if 'low' not in df.columns and 'lowest' in df.columns:
                df['low'] = df['lowest']
            
            # 确保必要的列存在
            required_columns = ['open', 'high', 'low', 'close']
            for col in required_columns:
                if col not in df.columns:
                    logger.error(f"K线数据缺少必要列: {col}")
                    return None
            
            return df
        
        except Exception as e:
            logger.error(f"K线数据转换失败: {e}")
            return None
    
    @classmethod
    def _result_to_list(cls, result) -> Union[List[float], Dict[str, List[float]], None]:
        """
        转换 pandas-ta 的返回结果
        
        Args:
            result: pandas Series 或 DataFrame
        
        Returns:
            - Series: List[float]
            - DataFrame: Dict[str, List[float]]
        """
        try:
            import pandas as pd
            
            if result is None:
                return None
            
            # 单列（Series）
            if isinstance(result, pd.Series):
                return result.tolist()
            
            # 多列（DataFrame）
            if isinstance(result, pd.DataFrame):
                return {col: result[col].tolist() for col in result.columns}
            
            return None
        
        except Exception as e:
            logger.error(f"结果转换失败: {e}")
            return None
    
    # =========================================================================
    # 工具方法
    # =========================================================================
    
    @classmethod
    def list_indicators(cls) -> List[str]:
        """
        列出所有可用的指标
        
        Returns:
            List[str]: 指标名称列表
        """
        if cls._ta is None:
            cls._init_ta()
        
        # 获取所有公开的函数（排除内部方法和类）
        indicators = [
            name for name in dir(cls._ta)
            if not name.startswith('_') and callable(getattr(cls._ta, name))
        ]
        
        return sorted(indicators)
    
    @classmethod
    def get_indicator_help(cls, indicator_name: str) -> str:
        """
        获取指标的帮助信息
        
        Args:
            indicator_name: 指标名称
        
        Returns:
            str: 帮助文档
        """
        if cls._ta is None:
            cls._init_ta()
        
        if not hasattr(cls._ta, indicator_name):
            return f"指标不存在: {indicator_name}"
        
        indicator_func = getattr(cls._ta, indicator_name)
        return indicator_func.__doc__ or "无文档"


# =========================================================================
# 使用示例
# =========================================================================

if __name__ == "__main__":
    # 示例 K线数据
    klines = [
        {'date': '20251201', 'open': 10.0, 'high': 10.5, 'low': 9.8, 'close': 10.2, 'volume': 1000},
        {'date': '20251202', 'open': 10.2, 'high': 10.8, 'low': 10.0, 'close': 10.6, 'volume': 1200},
        {'date': '20251203', 'open': 10.6, 'high': 11.0, 'low': 10.4, 'close': 10.8, 'volume': 1500},
        # ... 更多数据（需要至少 30-50 条数据）
    ]
    
    print("=" * 60)
    print("IndicatorService 使用示例")
    print("=" * 60)
    print(f"导入: from app.core.modules.indicator import IndicatorService")
    print()
    
    # 方式1: 便捷API
    print("方式1: 便捷API（推荐）")
    print("-" * 60)
    ma20 = IndicatorService.ma(klines, length=20)
    print(f"MA20: {ma20[-5:] if ma20 else 'None'}")
    
    rsi = IndicatorService.rsi(klines, length=14)
    print(f"RSI: {rsi[-5:] if rsi else 'None'}")
    
    macd = IndicatorService.macd(klines)
    print(f"MACD 字段: {list(macd.keys()) if macd else 'None'}")
    print()
    
    # 方式2: 通用API（支持所有指标）
    print("方式2: 通用API（支持所有 150+ 指标）")
    print("-" * 60)
    cci = IndicatorService.calculate('cci', klines, length=20)
    print(f"CCI: {cci[-5:] if cci else 'None'}")
    print()
    
    # 列出所有指标
    print("工具方法:")
    print("-" * 60)
    all_indicators = IndicatorService.list_indicators()
    print(f"可用指标数量: {len(all_indicators)}")
    print(f"前10个: {all_indicators[:10]}")
    print("=" * 60)
