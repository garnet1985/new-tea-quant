#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import threading
from collections import defaultdict, deque
from loguru import logger


class PerformanceMonitor:
    """
    性能监控器
    用于监控系统各个组件的性能指标
    """
    
    def __init__(self, max_history=1000):
        """
        初始化性能监控器
        
        Args:
            max_history: 最大历史记录数
        """
        self.max_history = max_history
        self.metrics = defaultdict(lambda: deque(maxlen=max_history))
        self.lock = threading.Lock()
        
        # 性能指标分类
        self.categories = {
            'database': ['query_time', 'write_time', 'connection_time'],
            'api': ['request_time', 'response_time', 'error_rate'],
            'processing': ['job_time', 'batch_time', 'throughput'],
            'memory': ['memory_usage', 'gc_time'],
            'system': ['cpu_usage', 'disk_io']
        }
        
        logger.info("性能监控器已启动")
    
    def record_metric(self, category, metric_name, value, metadata=None):
        """
        记录性能指标
        
        Args:
            category: 指标分类
            metric_name: 指标名称
            value: 指标值
            metadata: 额外元数据
        """
        timestamp = time.time()
        record = {
            'timestamp': timestamp,
            'value': value,
            'metadata': metadata or {}
        }
        
        with self.lock:
            key = f"{category}.{metric_name}"
            self.metrics[key].append(record)
    
    def get_metric_stats(self, category, metric_name, window_seconds=None):
        """
        获取指标统计信息
        
        Args:
            category: 指标分类
            metric_name: 指标名称
            window_seconds: 时间窗口（秒），None表示全部历史
            
        Returns:
            dict: 统计信息
        """
        key = f"{category}.{metric_name}"
        
        with self.lock:
            if key not in self.metrics:
                return None
            
            records = list(self.metrics[key])
            
            # 应用时间窗口过滤
            if window_seconds:
                cutoff_time = time.time() - window_seconds
                records = [r for r in records if r['timestamp'] >= cutoff_time]
            
            if not records:
                return None
            
            values = [r['value'] for r in records]
            
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'latest': values[-1],
                'window_seconds': window_seconds
            }
    
    def get_performance_report(self, window_seconds=300):
        """
        生成性能报告
        
        Args:
            window_seconds: 报告时间窗口（秒）
            
        Returns:
            dict: 性能报告
        """
        report = {
            'timestamp': time.time(),
            'window_seconds': window_seconds,
            'categories': {}
        }
        
        for category, metrics in self.categories.items():
            category_stats = {}
            for metric in metrics:
                stats = self.get_metric_stats(category, metric, window_seconds)
                if stats:
                    category_stats[metric] = stats
            
            if category_stats:
                report['categories'][category] = category_stats
        
        return report
    
    def print_performance_summary(self, window_seconds=300):
        """
        打印性能摘要
        
        Args:
            window_seconds: 时间窗口（秒）
        """
        report = self.get_performance_report(window_seconds)
        
        logger.info(f"📊 性能监控报告 (最近 {window_seconds} 秒):")
        
        for category, metrics in report['categories'].items():
            logger.info(f"\n  📈 {category.upper()}:")
            for metric_name, stats in metrics.items():
                logger.info(f"    {metric_name}:")
                logger.info(f"      平均值: {stats['avg']:.3f}")
                logger.info(f"      最小值: {stats['min']:.3f}")
                logger.info(f"      最大值: {stats['max']:.3f}")
                logger.info(f"      最新值: {stats['latest']:.3f}")
                logger.info(f"      样本数: {stats['count']}")
    
    def timer(self, category, metric_name, metadata=None):
        """
        创建性能计时器
        
        Args:
            category: 指标分类
            metric_name: 指标名称
            metadata: 额外元数据
            
        Returns:
            PerformanceTimer: 计时器实例
        """
        return PerformanceTimer(self, category, metric_name, metadata)
    
    def clear_old_metrics(self, cutoff_time=None):
        """
        清理旧指标数据
        
        Args:
            cutoff_time: 截止时间戳，None表示清理所有数据
        """
        if cutoff_time is None:
            cutoff_time = time.time() - 3600  # 默认清理1小时前的数据
        
        with self.lock:
            for key in list(self.metrics.keys()):
                records = list(self.metrics[key])
                filtered_records = [r for r in records if r['timestamp'] >= cutoff_time]
                self.metrics[key] = deque(filtered_records, maxlen=self.max_history)
        
        logger.info(f"已清理 {cutoff_time} 之前的性能指标数据")


class PerformanceTimer:
    """
    性能计时器
    用于测量代码块的执行时间
    """
    
    def __init__(self, monitor, category, metric_name, metadata=None):
        """
        初始化计时器
        
        Args:
            monitor: PerformanceMonitor实例
            category: 指标分类
            metric_name: 指标名称
            metadata: 额外元数据
        """
        self.monitor = monitor
        self.category = category
        self.metric_name = metric_name
        self.metadata = metadata
        self.start_time = None
    
    def __enter__(self):
        """进入上下文"""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        if self.start_time:
            duration = time.time() - self.start_time
            self.monitor.record_metric(
                self.category, 
                self.metric_name, 
                duration, 
                self.metadata
            )
    
    def record(self, value, metadata=None):
        """
        手动记录指标
        
        Args:
            value: 指标值
            metadata: 额外元数据
        """
        self.monitor.record_metric(
            self.category,
            self.metric_name,
            value,
            metadata or self.metadata
        )


# 全局性能监控器实例
_global_monitor = None
_monitor_lock = threading.Lock()


def get_performance_monitor():
    """获取全局性能监控器实例"""
    global _global_monitor
    if _global_monitor is None:
        with _monitor_lock:
            if _global_monitor is None:
                _global_monitor = PerformanceMonitor()
    return _global_monitor


def timer(category, metric_name, metadata=None):
    """
    性能计时器装饰器
    
    Args:
        category: 指标分类
        metric_name: 指标名称
        metadata: 额外元数据
    
    Returns:
        decorator: 装饰器函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_performance_monitor()
            with PerformanceTimer(monitor, category, metric_name, metadata):
                return func(*args, **kwargs)
        return wrapper
    return decorator 