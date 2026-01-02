#!/usr/bin/env python3
"""
Indicators - 常用技术指标

当前实现：
- 简单移动平均 (SMA)：在传入的K线列表上添加 `ma{period}` 字段。
- MACD：添加 `macd_dif`, `macd_dea`, `macd_hist` 字段。
- RSI：添加 `rsi{period}` 字段。
- 布林带 (Bollinger Bands)：添加 `bb_mid{period}`、`bb_upper{period}`、`bb_lower{period}` 字段。
"""
from typing import List, Dict, Any, Optional
from collections import deque


class Indicators:

    @staticmethod
    def add_indicators(kline_data: Dict[str, List[Dict[str, Any]]], indicators_config: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        为K线数据添加技术指标
        
        Args:
            kline_data: 包含不同周期K线数据的字典，格式为 {term: List[Dict]}
            indicators_config: 指标配置字典
            
        Returns:
            Dict[str, List[Dict]]: 添加了指标后的K线数据
        """
        result = {}
        
        for term, k_lines in kline_data.items():
            # 为每个周期的K线数据添加指标
            result[term] = k_lines.copy()  # 浅拷贝，避免修改原数据
            
            for indicator_name, indicator_config in indicators_config.items():
                if indicator_name == 'moving_average':
                    # 移动平均线
                    for period in indicator_config.get('periods', []):
                        result[term] = Indicators.moving_average(result[term], period)
                        
                elif indicator_name == 'macd':
                    # MACD指标
                    result[term] = Indicators.macd(result[term])
                    
                elif indicator_name == 'rsi':
                    # RSI指标
                    period = indicator_config.get('period', 14)
                    result[term] = Indicators.rsi(result[term], period)
                    
                elif indicator_name == 'bollinger':
                    # 布林带指标
                    period = indicator_config.get('period', 20)
                    std_multiplier = indicator_config.get('std_multiplier', 2.0)
                    result[term] = Indicators.bollinger(result[term], period, std_multiplier=std_multiplier)
        
        return result

    @staticmethod
    def moving_average(k_lines: List[Dict[str, Any]], period: int, *, price_field: str = 'close', output_field: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        计算简单移动平均（SMA），返回在原记录基础上新增 `ma{period}` 字段的K线列表。

        Args:
            k_lines: 已按时间顺序排列的K线记录列表
            period: 计算窗口期数（>0）
            price_field: 价格字段名（默认 'close'）
            output_field: 输出字段名；默认使用 `ma{period}`

        Returns:
            List[Dict]: 带有MA字段的K线记录（浅拷贝后的新列表）
        """
        if not isinstance(period, int) or period <= 0:
            raise ValueError("period 必须是正整数")

        out_field = output_field or f"ma{period}"

        # 使用滑动窗口提高性能
        window: deque = deque(maxlen=period)
        window_sum: float = 0.0

        result: List[Dict[str, Any]] = []
        for rec in k_lines or []:
            value = rec.get(price_field)
            # 构造新记录，避免修改入参
            new_rec = dict(rec)

            # 输入健壮性：非数字直接视为缺失
            try:
                num = float(value) if value is not None else None
            except (TypeError, ValueError):
                num = None

            if num is None:
                # 缺失数据时，重置窗口
                window.clear()
                window_sum = 0.0
                new_rec[out_field] = None
                result.append(new_rec)
                continue

            # 推入窗口
            if len(window) == period:
                # 先弹出旧值
                oldest = window[0]
                window_sum -= oldest
            window.append(num)
            window_sum += num

            if len(window) == period:
                new_rec[out_field] = window_sum / period
            else:
                new_rec[out_field] = None

            result.append(new_rec)

        return result

    @staticmethod
    def add_indicators(kline_data: Dict[str, List[Dict[str, Any]]], indicators_config: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        为K线数据添加技术指标
        
        Args:
            kline_data: 包含不同周期K线数据的字典，格式为 {term: List[Dict]}
            indicators_config: 指标配置字典
            
        Returns:
            Dict[str, List[Dict]]: 添加了指标后的K线数据
        """
        result = {}
        
        for term, k_lines in kline_data.items():
            # 为每个周期的K线数据添加指标
            result[term] = k_lines.copy()  # 浅拷贝，避免修改原数据
            
            for indicator_name, indicator_config in indicators_config.items():
                if indicator_name == 'moving_average':
                    # 移动平均线
                    for period in indicator_config.get('periods', []):
                        result[term] = Indicators.moving_average(result[term], period)
                        
                elif indicator_name == 'macd':
                    # MACD指标
                    result[term] = Indicators.macd(result[term])
                    
                elif indicator_name == 'rsi':
                    # RSI指标
                    period = indicator_config.get('period', 14)
                    result[term] = Indicators.rsi(result[term], period)
                    
                elif indicator_name == 'bollinger':
                    # 布林带指标
                    period = indicator_config.get('period', 20)
                    std_multiplier = indicator_config.get('std_multiplier', 2.0)
                    result[term] = Indicators.bollinger(result[term], period, std_multiplier=std_multiplier)
        
        return result

    # -----------------------------
    # MACD
    # -----------------------------
    @staticmethod
    def macd(
        k_lines: List[Dict[str, Any]],
        *,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        price_field: str = 'close'
    ) -> List[Dict[str, Any]]:
        """
        计算 MACD 指标，并在每条记录上添加：
          - macd_dif: EMA(fast) - EMA(slow)
          - macd_dea: DIF 的 EMA(signal)
          - macd_hist: DIF - DEA  （若需乘2，可在下游展示时处理）
        """
        if not (isinstance(fast, int) and isinstance(slow, int) and isinstance(signal, int)):
            raise ValueError("fast/slow/signal 必须是整数")
        if fast <= 0 or slow <= 0 or signal <= 0:
            raise ValueError("fast/slow/signal 必须为正数")

        prices: List[Optional[float]] = []
        for rec in k_lines or []:
            v = rec.get(price_field)
            try:
                prices.append(float(v) if v is not None else None)
            except (TypeError, ValueError):
                prices.append(None)

        ema_fast = Indicators._ema_series(prices, fast)
        ema_slow = Indicators._ema_series(prices, slow)

        dif: List[Optional[float]] = []
        for a, b in zip(ema_fast, ema_slow):
            if a is None or b is None:
                dif.append(None)
            else:
                dif.append(a - b)

        dea = Indicators._ema_series(dif, signal)

        result: List[Dict[str, Any]] = []
        for rec, d, e in zip(k_lines or [], dif, dea):
            new_rec = dict(rec)
            new_rec['macd_dif'] = d
            new_rec['macd_dea'] = e
            new_rec['macd_hist'] = (d - e) if (d is not None and e is not None) else None
            result.append(new_rec)
        return result

    @staticmethod
    def _ema_series(values: List[Optional[float]], period: int) -> List[Optional[float]]:
        """
        计算 EMA 序列。对于 None 值，输出 None 并不参与累计；
        种子使用遇到的首个非 None 值。
        """
        if period <= 0:
            raise ValueError("period 必须为正数")
        k = 2.0 / (period + 1)
        ema_list: List[Optional[float]] = []
        ema_prev: Optional[float] = None
        for v in values:
            if v is None:
                ema_list.append(None)
                continue
            if ema_prev is None:
                ema_prev = v
            else:
                ema_prev = v * k + ema_prev * (1 - k)
            ema_list.append(ema_prev)
        return ema_list

    # -----------------------------
    # RSI (Wilder)
    # -----------------------------
    @staticmethod
    def rsi(
        k_lines: List[Dict[str, Any]],
        period: int = 14,
        *,
        price_field: str = 'close',
        output_field: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        计算 RSI（Wilder 平滑），并在每条记录上添加 `rsi` 字段。
        对于不可用价格或不足周期的前几条，输出为 None。
        """
        if not isinstance(period, int) or period <= 0:
            raise ValueError("period 必须是正整数")
        # 统一使用"rsi"作为字段名，不管什么周期
        out_field = output_field or "rsi"

        # 提取价格序列
        closes: List[Optional[float]] = []
        for rec in k_lines or []:
            v = rec.get(price_field)
            try:
                closes.append(float(v) if v is not None else None)
            except (TypeError, ValueError):
                closes.append(None)

        # 计算单步涨跌
        deltas: List[Optional[float]] = [None]
        for i in range(1, len(closes)):
            a, b = closes[i - 1], closes[i]
            if a is None or b is None:
                deltas.append(None)
            else:
                deltas.append(b - a)

        avg_gain: Optional[float] = None
        avg_loss: Optional[float] = None
        result: List[Dict[str, Any]] = []

        # 初始化窗口（前 period 个 delta，不含第一条 None）
        for idx, rec in enumerate(k_lines or []):
            new_rec = dict(rec)
            if idx < period:
                new_rec[out_field] = None
                result.append(new_rec)
                continue

            if idx == period:
                # 用前 period 个有效 delta 初始化平均涨跌
                gains: List[float] = []
                losses: List[float] = []
                for d in deltas[1:period + 1]:
                    if d is None:
                        gains.append(0.0)
                        losses.append(0.0)
                    elif d >= 0:
                        gains.append(d)
                        losses.append(0.0)
                    else:
                        gains.append(0.0)
                        losses.append(-d)
                avg_gain = sum(gains) / period
                avg_loss = sum(losses) / period
            else:
                d = deltas[idx]
                if d is None:
                    g = 0.0
                    l = 0.0
                elif d >= 0:
                    g = d
                    l = 0.0
                else:
                    g = 0.0
                    l = -d
                # Wilder 平滑
                assert avg_gain is not None and avg_loss is not None
                avg_gain = (avg_gain * (period - 1) + g) / period
                avg_loss = (avg_loss * (period - 1) + l) / period

            # 计算 RSI
            if avg_loss is None or (avg_gain is None):
                rsi_val: Optional[float] = None
            elif avg_loss == 0:
                rsi_val = 100.0
            else:
                rs = avg_gain / avg_loss
                rsi_val = 100.0 - (100.0 / (1.0 + rs))

            new_rec[out_field] = rsi_val
            result.append(new_rec)

        return result

    @staticmethod
    def add_indicators(kline_data: Dict[str, List[Dict[str, Any]]], indicators_config: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        为K线数据添加技术指标
        
        Args:
            kline_data: 包含不同周期K线数据的字典，格式为 {term: List[Dict]}
            indicators_config: 指标配置字典
            
        Returns:
            Dict[str, List[Dict]]: 添加了指标后的K线数据
        """
        result = {}
        
        for term, k_lines in kline_data.items():
            # 为每个周期的K线数据添加指标
            result[term] = k_lines.copy()  # 浅拷贝，避免修改原数据
            
            for indicator_name, indicator_config in indicators_config.items():
                if indicator_name == 'moving_average':
                    # 移动平均线
                    for period in indicator_config.get('periods', []):
                        result[term] = Indicators.moving_average(result[term], period)
                        
                elif indicator_name == 'macd':
                    # MACD指标
                    result[term] = Indicators.macd(result[term])
                    
                elif indicator_name == 'rsi':
                    # RSI指标
                    period = indicator_config.get('period', 14)
                    result[term] = Indicators.rsi(result[term], period)
                    
                elif indicator_name == 'bollinger':
                    # 布林带指标
                    period = indicator_config.get('period', 20)
                    std_multiplier = indicator_config.get('std_multiplier', 2.0)
                    result[term] = Indicators.bollinger(result[term], period, std_multiplier=std_multiplier)
        
        return result

    # -----------------------------
    # Bollinger Bands (SMA ± k*STD)
    # -----------------------------
    @staticmethod
    def bollinger(
        k_lines: List[Dict[str, Any]],
        period: int = 20,
        *,
        std_multiplier: float = 2.0,
        price_field: str = 'close',
        output_mid_field: Optional[str] = None,
        output_upper_field: Optional[str] = None,
        output_lower_field: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        计算布林带：
          - 中轨 = SMA(period)
          - 上轨 = 中轨 + k * STD(period)
          - 下轨 = 中轨 - k * STD(period)

        返回在原记录基础上新增 `bb_mid{period}`、`bb_upper{period}`、`bb_lower{period}` 字段的列表。
        """
        if not isinstance(period, int) or period <= 0:
            raise ValueError("period 必须是正整数")
        try:
            k = float(std_multiplier)
        except Exception:
            raise ValueError("std_multiplier 必须是数值")

        mid_field = output_mid_field or f"bb_mid{period}"
        upper_field = output_upper_field or f"bb_upper{period}"
        lower_field = output_lower_field or f"bb_lower{period}"

        # 滑动窗口维护 sum 与 sumsq，用于快速均值与标准差
        window: deque = deque(maxlen=period)
        sum_x: float = 0.0
        sum_x2: float = 0.0

        result: List[Dict[str, Any]] = []
        for rec in k_lines or []:
            v = rec.get(price_field)
            try:
                x = float(v) if v is not None else None
            except (TypeError, ValueError):
                x = None

            new_rec = dict(rec)

            if x is None:
                # 缺失值重置窗口
                window.clear()
                sum_x = 0.0
                sum_x2 = 0.0
                new_rec[mid_field] = None
                new_rec[upper_field] = None
                new_rec[lower_field] = None
                result.append(new_rec)
                continue

            # 若窗口已满，先移除最旧值
            if len(window) == period:
                oldest = window[0]
                sum_x -= oldest
                sum_x2 -= oldest * oldest

            window.append(x)
            sum_x += x
            sum_x2 += x * x

            if len(window) == period:
                mean = sum_x / period
                # population std（总体标准差），与常见指标实现一致
                var = max(sum_x2 / period - mean * mean, 0.0)
                std = var ** 0.5
                new_rec[mid_field] = mean
                new_rec[upper_field] = mean + k * std
                new_rec[lower_field] = mean - k * std
            else:
                new_rec[mid_field] = None
                new_rec[upper_field] = None
                new_rec[lower_field] = None

            result.append(new_rec)

        return result

    @staticmethod
    def add_indicators(kline_data: Dict[str, List[Dict[str, Any]]], indicators_config: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        为K线数据添加技术指标
        
        Args:
            kline_data: 包含不同周期K线数据的字典，格式为 {term: List[Dict]}
            indicators_config: 指标配置字典
            
        Returns:
            Dict[str, List[Dict]]: 添加了指标后的K线数据
        """
        result = {}
        
        for term, k_lines in kline_data.items():
            # 为每个周期的K线数据添加指标
            result[term] = k_lines.copy()  # 浅拷贝，避免修改原数据
            
            for indicator_name, indicator_config in indicators_config.items():
                if indicator_name == 'moving_average':
                    # 移动平均线
                    for period in indicator_config.get('periods', []):
                        result[term] = Indicators.moving_average(result[term], period)
                        
                elif indicator_name == 'macd':
                    # MACD指标
                    result[term] = Indicators.macd(result[term])
                    
                elif indicator_name == 'rsi':
                    # RSI指标
                    period = indicator_config.get('period', 14)
                    result[term] = Indicators.rsi(result[term], period)
                    
                elif indicator_name == 'bollinger':
                    # 布林带指标
                    period = indicator_config.get('period', 20)
                    std_multiplier = indicator_config.get('std_multiplier', 2.0)
                    result[term] = Indicators.bollinger(result[term], period, std_multiplier=std_multiplier)
        
        return result


