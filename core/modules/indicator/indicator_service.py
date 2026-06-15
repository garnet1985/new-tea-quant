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

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import logging

logger = logging.getLogger(__name__)

# 仅依赖 close 序列的 pandas-ta 指标（走 _ta_on_close，避免宽表 DataFrame）
_CLOSE_SERIES_INDICATORS = frozenset(
    {"sma", "ema", "wma", "rma", "roc", "mom", "hma", "zlma"}
)

# 需要 OHLC(V) 的高频指标：无单独便捷方法时走 _ta_on_ohlcv 裁剪通道
_OHLCV_DIRECT_INDICATORS = frozenset(
    {
        "cci",
        "willr",
        "mfi",
        "supertrend",
        "vwma",
        "cmf",
        "ad",
        "adosc",
        "ppo",
        "kc",
        "donchian",
        "natr",
        "psar",
        "stochrsi",
        "uo",
        "cmo",
        "aroon",
        "vortex",
        "true_range",
        "trix",
        "kst",
        "efi",
        "pvt",
        "eom",
    }
)

# compute_batch 单项: (指标名, 参数, 结果)
BatchIndicatorResult = Tuple[str, Dict[str, Any], Union[List[float], Dict[str, List[float]]]]


@dataclass
class _BatchContext:
    """单套 K 线批量算指标：close Series 与 OCHL(V) DataFrame 各只构建一次。"""

    close_series: Any
    ohlcv_df: Any


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
        
        最后一层 fallback：使用完整 K 线宽表转 DataFrame（不裁剪）。
        策略配置请优先走 ``compute()``；仅未知/冷门指标才应落到这里。

        示例：
            ma20 = IndicatorService.calculate('sma', klines, length=20)
        """
        try:
            indicator_name = str(indicator_name).lower().strip()
            cfg = dict(params or {})
            cls._init_ta()
            if not hasattr(cls._ta, indicator_name):
                logger.error(f"不支持的指标: {indicator_name}")
                return None

            df = cls._klines_to_dataframe(klines)
            if df is None or df.empty:
                logger.warning("K线数据为空或转换失败")
                return None

            result = getattr(cls._ta, indicator_name)(
                high=df["high"],
                low=df["low"],
                close=df["close"],
                volume=df.get("volume"),
                open_=df["open"],
                **cfg,
            )
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
        return cls._ta_on_close("sma", klines, length=length)
    
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
        return cls._ta_on_close("ema", klines, length=length)
    
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
        return cls._ta_on_close("rsi", klines, length=length)
    
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
        return cls._ta_on_ohlcv(
            "macd", klines, fast=fast, slow=slow, signal=signal
        )
    
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
        return cls._ta_on_ohlcv("bbands", klines, length=length, std=std)
    
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
        return cls._ta_on_ohlcv("atr", klines, length=length)
    
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
        return cls._ta_on_ohlcv("stoch", klines, k=k, d=d, smooth_k=smooth_k)
    
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
        return cls._ta_on_ohlcv("adx", klines, length=length)
    
    @classmethod
    def obv(cls, klines: List[Dict[str, Any]]) -> Optional[List[float]]:
        """
        能量潮（OBV）
        
        Args:
            klines: K线数据
        
        Returns:
            List[float]: OBV值列表
        """
        return cls._ta_on_ohlcv("obv", klines)
    
    # =========================================================================
    # 私有方法
    # =========================================================================
    
    @classmethod
    def warmup(cls) -> None:
        """预加载 pandas-ta-classic（每个进程调用一次即可，重复调用无副作用）。"""
        cls._init_ta()

    @classmethod
    def compute(
        cls,
        indicator_name: str,
        klines: List[Dict[str, Any]],
        **params: Any,
    ) -> Union[List[float], Dict[str, List[float]], None]:
        """
        策略 indicators 单指标入口（三层，见 ``_compute_single``）。
        多套 K 线、多指标请用 ``compute_batch``。
        """
        return cls._compute_single(
            str(indicator_name).lower().strip(),
            klines,
            dict(params or {}),
            batch_ctx=None,
        )

    @classmethod
    def compute_batch(
        cls,
        klines: List[Dict[str, Any]],
        indicators_cfg: Dict[str, Any],
    ) -> List[BatchIndicatorResult]:
        """
        单套 K 线批量计算 indicators 配置中的全部指标。

        close Series 与 OCHL(V) DataFrame 各只构建一次，再逐项调用 ta。
        """
        if not klines or not indicators_cfg:
            return []

        ctx = cls._build_batch_context(klines)
        if ctx is None:
            return []

        results: List[BatchIndicatorResult] = []
        for name, configs in indicators_cfg.items():
            if not configs:
                continue
            if not isinstance(configs, list):
                configs = [configs]
            for cfg in configs:
                if not isinstance(cfg, dict):
                    continue
                item_cfg = dict(cfg)
                try:
                    result = cls._compute_single(
                        str(name).lower().strip(),
                        klines,
                        item_cfg,
                        batch_ctx=ctx,
                    )
                    if result:
                        results.append((str(name).lower().strip(), item_cfg, result))
                except Exception as exc:
                    logger.error(
                        "批量指标失败: indicator=%s, params=%s, error=%s",
                        name,
                        item_cfg,
                        exc,
                        exc_info=True,
                    )
        return results

    @classmethod
    def _build_batch_context(cls, klines: List[Dict[str, Any]]) -> Optional[_BatchContext]:
        import pandas as pd

        if not klines:
            return None
        cls._init_ta()

        closes = [k.get("close") for k in klines if k.get("close") is not None]
        close_series = pd.Series(closes) if closes else None

        trimmed = cls._trim_klines_for_ohlcv(klines)
        ohlcv_df = cls._klines_to_dataframe(trimmed)
        if close_series is None and (ohlcv_df is None or ohlcv_df.empty):
            return None
        return _BatchContext(close_series=close_series, ohlcv_df=ohlcv_df)

    @classmethod
    def _compute_single(
        cls,
        name: str,
        klines: List[Dict[str, Any]],
        cfg: Dict[str, Any],
        *,
        batch_ctx: Optional[_BatchContext],
    ) -> Union[List[float], Dict[str, List[float]], None]:
        """
        单指标计算（三层）：

        1. 专通：close 序列或带默认参数的 OHLCV
        2. 裁剪普通：OCHL(V) 窄表
        3. ``calculate``：完整宽表 fallback
        """
        if name == "ma":
            name = "sma"

        def close_call(method: str, **kwargs: Any) -> Optional[List[float]]:
            if batch_ctx is not None and batch_ctx.close_series is not None:
                return cls._ta_on_close_series(method, batch_ctx.close_series, **kwargs)
            return cls._ta_on_close(method, klines, **kwargs)

        def ohlcv_call(method: str, **kwargs: Any) -> Union[List[float], Dict[str, List[float]], None]:
            if batch_ctx is not None and batch_ctx.ohlcv_df is not None and not batch_ctx.ohlcv_df.empty:
                return cls._ta_on_ohlcv_df(method, batch_ctx.ohlcv_df, **kwargs)
            return cls._ta_on_ohlcv(method, klines, **kwargs)

        # --- 1. 专通（close）---
        if name == "rsi":
            return close_call("rsi", length=int(cfg.get("length", 14)))
        if name in _CLOSE_SERIES_INDICATORS:
            return close_call(name, **cfg)

        # --- 1b. 专通（OHLCV，带默认参数）---
        if name == "macd":
            return ohlcv_call(
                "macd",
                fast=int(cfg.get("fast", 12)),
                slow=int(cfg.get("slow", 26)),
                signal=int(cfg.get("signal", 9)),
            )
        if name == "bbands":
            return ohlcv_call(
                "bbands",
                length=int(cfg.get("length", 20)),
                std=float(cfg.get("std", 2.0)),
            )
        if name == "atr":
            return ohlcv_call("atr", length=int(cfg.get("length", 14)))
        if name == "stoch":
            return ohlcv_call(
                "stoch",
                k=int(cfg.get("k", 14)),
                d=int(cfg.get("d", 3)),
                smooth_k=int(cfg.get("smooth_k", 3)),
            )
        if name == "adx":
            return ohlcv_call("adx", length=int(cfg.get("length", 14)))
        if name == "obv":
            return ohlcv_call("obv")

        # --- 2. 裁剪后普通 ---
        if name in _OHLCV_DIRECT_INDICATORS:
            return ohlcv_call(name, **cfg)

        cls._init_ta()
        if hasattr(cls._ta, name):
            return ohlcv_call(name, **cfg)

        # --- 3. 宽表 fallback（batch 不用宽表，避免重复建表）---
        return cls.calculate(name, klines, **cfg)

    @classmethod
    def _ta_on_close_series(
        cls,
        method_name: str,
        close_series: Any,
        **params: Any,
    ) -> Optional[List[float]]:
        try:
            cls._init_ta()
            if close_series is None or len(close_series) == 0:
                logger.error("K线数据缺少必要列: close")
                return None
            if not hasattr(cls._ta, method_name):
                logger.error(f"不支持的指标: {method_name}")
                return None

            result = getattr(cls._ta, method_name)(close_series, **params)
            out = cls._result_to_list(result)
            return out if isinstance(out, list) else None
        except Exception as e:
            logger.error(
                "close 序列指标失败: indicator=%s, params=%s, error=%s",
                method_name,
                params,
                e,
            )
            return None

    @classmethod
    def _ta_on_close(
        cls,
        method_name: str,
        klines: List[Dict[str, Any]],
        **params: Any,
    ) -> Optional[List[float]]:
        """仅 close 序列的指标（SMA/EMA/RSI 等）。"""
        if not klines:
            return None
        import pandas as pd

        closes = [k.get("close") for k in klines if k.get("close") is not None]
        if not closes:
            logger.error("K线数据缺少必要列: close")
            return None
        return cls._ta_on_close_series(method_name, pd.Series(closes), **params)

    @classmethod
    def _ta_on_ohlcv_df(
        cls,
        method_name: str,
        df: Any,
        **params: Any,
    ) -> Union[List[float], Dict[str, List[float]], None]:
        cls._init_ta()
        if not hasattr(cls._ta, method_name):
            logger.error(f"不支持的指标: {method_name}")
            return None
        if df is None or df.empty:
            logger.warning("K线数据为空或转换失败")
            return None

        result = getattr(cls._ta, method_name)(
            high=df["high"],
            low=df["low"],
            close=df["close"],
            volume=df.get("volume"),
            open_=df["open"],
            **params,
        )
        return cls._result_to_list(result)

    @classmethod
    def _ta_on_ohlcv(
        cls,
        method_name: str,
        klines: List[Dict[str, Any]],
        **params: Any,
    ) -> Union[List[float], Dict[str, List[float]], None]:
        """OHLC(V) 指标：裁剪宽表后调 pandas-ta。"""
        if not klines:
            return None
        return cls._ta_on_ohlcv_df(
            method_name,
            cls._klines_to_dataframe(cls._trim_klines_for_ohlcv(klines)),
            **params,
        )

    @classmethod
    def _trim_klines_for_ohlcv(cls, klines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """OHLC(V) 通道：仅保留算指标所需列，避免 storage 宽行拖慢 DataFrame 构造。"""
        trimmed: List[Dict[str, Any]] = []
        for row in klines:
            slim: Dict[str, Any] = {
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
            }
            volume = row.get("volume")
            if volume is not None:
                slim["volume"] = volume
            trimmed.append(slim)
        return trimmed

    @classmethod
    def _patch_pandas_ta_verify_series(cls) -> None:
        """将 pandas-ta 数据不足告警改为中文 DEBUG，避免刷屏。"""
        from typing import Optional, Union

        from pandas import Series

        import pandas_ta_classic.utils._core as pta_core

        if getattr(pta_core.verify_series, "_tea_patched", False):
            return

        def verify_series(
            series: Series,
            min_length: Optional[Union[int, float]] = None,
        ) -> Optional[Series]:
            has_length = min_length is not None and isinstance(min_length, int)
            if series is not None and isinstance(series, Series):
                if has_length and series.size < min_length:
                    logger.debug(
                        "序列仅 %s 行，指标至少需要 %s 行，跳过计算",
                        series.size,
                        min_length,
                    )
                    return None
                return series
            return None

        verify_series._tea_patched = True  # type: ignore[attr-defined]
        pta_core.verify_series = verify_series

    @classmethod
    def _init_ta(cls):
        """延迟加载 pandas-ta-classic"""
        try:
            import pandas_ta_classic as ta

            cls._patch_pandas_ta_verify_series()
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
    print(f"导入: from core.modules.indicator import IndicatorService")
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
