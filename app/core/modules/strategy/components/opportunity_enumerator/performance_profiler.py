#!/usr/bin/env python3
"""
Performance Profiler for Opportunity Enumerator

性能分析工具，用于统计：
- IO 操作数量（数据库查询、文件读写）
- 时间消耗（各个阶段）
- 内存使用
"""

import time
import psutil
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标"""
    # 时间统计（秒）
    time_load_data: float = 0.0
    time_calculate_indicators: float = 0.0
    time_enumerate: float = 0.0
    time_serialize: float = 0.0
    time_save_csv: float = 0.0
    time_total: float = 0.0
    
    # IO 统计
    db_queries: int = 0  # 数据库查询次数
    db_query_time: float = 0.0  # 数据库查询总时间
    file_writes: int = 0  # 文件写入次数
    file_write_time: float = 0.0  # 文件写入总时间
    file_write_size: int = 0  # 文件写入总大小（字节）
    
    # 数据统计
    kline_count: int = 0
    opportunity_count: int = 0
    target_count: int = 0
    
    # 内存统计（MB）
    memory_peak: float = 0.0  # 峰值内存
    memory_start: float = 0.0  # 开始内存
    memory_end: float = 0.0  # 结束内存
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'time': {
                'load_data': self.time_load_data,
                'calculate_indicators': self.time_calculate_indicators,
                'enumerate': self.time_enumerate,
                'serialize': self.time_serialize,
                'save_csv': self.time_save_csv,
                'total': self.time_total,
            },
            'io': {
                'db_queries': self.db_queries,
                'db_query_time': self.db_query_time,
                'file_writes': self.file_writes,
                'file_write_time': self.file_write_time,
                'file_write_size_mb': self.file_write_size / (1024 * 1024),
            },
            'data': {
                'kline_count': self.kline_count,
                'opportunity_count': self.opportunity_count,
                'target_count': self.target_count,
            },
            'memory': {
                'peak_mb': self.memory_peak,
                'start_mb': self.memory_start,
                'end_mb': self.memory_end,
                'delta_mb': self.memory_end - self.memory_start,
            }
        }


class PerformanceProfiler:
    """性能分析器（单例，每个 Worker 一个实例）"""
    
    def __init__(self, stock_id: str):
        self.stock_id = stock_id
        self.metrics = PerformanceMetrics()
        self.process = psutil.Process(os.getpid())
        
        # 时间追踪
        self._timers: Dict[str, float] = {}
        
        # IO 追踪
        self._io_counters: Dict[str, int] = defaultdict(int)
        self._io_timers: Dict[str, float] = defaultdict(float)
        
        # 记录开始状态
        self._record_memory('start')
    
    def _record_memory(self, stage: str):
        """记录内存使用"""
        try:
            mem_info = self.process.memory_info()
            mem_mb = mem_info.rss / (1024 * 1024)  # RSS (Resident Set Size) in MB
            
            if stage == 'start':
                self.metrics.memory_start = mem_mb
            elif stage == 'end':
                self.metrics.memory_end = mem_mb
            
            # 更新峰值
            if mem_mb > self.metrics.memory_peak:
                self.metrics.memory_peak = mem_mb
        except Exception as e:
            logger.debug(f"无法记录内存: {e}")
    
    def start_timer(self, name: str):
        """开始计时"""
        self._timers[name] = time.perf_counter()
    
    def end_timer(self, name: str) -> float:
        """结束计时并返回耗时（秒）"""
        if name not in self._timers:
            logger.warning(f"Timer '{name}' not started")
            return 0.0
        
        elapsed = time.perf_counter() - self._timers[name]
        del self._timers[name]
        return elapsed
    
    def record_db_query(self, duration: float):
        """记录数据库查询"""
        self._io_counters['db_queries'] += 1
        self._io_timers['db_query_time'] += duration
    
    def record_file_write(self, size_bytes: int, duration: float):
        """记录文件写入"""
        self._io_counters['file_writes'] += 1
        self._io_timers['file_write_time'] += duration
        self._io_counters['file_write_size'] += size_bytes
    
    def finalize(self) -> PerformanceMetrics:
        """完成分析，返回最终指标"""
        # 更新 IO 统计
        self.metrics.db_queries = self._io_counters['db_queries']
        self.metrics.db_query_time = self._io_timers['db_query_time']
        self.metrics.file_writes = self._io_counters['file_writes']
        self.metrics.file_write_time = self._io_timers['file_write_time']
        self.metrics.file_write_size = self._io_counters['file_write_size']
        
        # 记录结束内存
        self._record_memory('end')
        
        return self.metrics


class AggregateProfiler:
    """聚合性能分析器（主进程使用）"""
    
    def __init__(self):
        self.stock_metrics: Dict[str, PerformanceMetrics] = {}
        self.start_time = time.perf_counter()
        self.process = psutil.Process(os.getpid())
        self.start_memory = self._get_memory_mb()
    
    def _get_memory_mb(self) -> float:
        """获取当前内存使用（MB）"""
        try:
            mem_info = self.process.memory_info()
            return mem_info.rss / (1024 * 1024)
        except Exception:
            return 0.0
    
    def add_stock_metrics(self, stock_id: str, metrics: PerformanceMetrics):
        """添加单只股票的指标"""
        self.stock_metrics[stock_id] = metrics
    
    def get_summary(self) -> Dict[str, Any]:
        """获取汇总统计"""
        if not self.stock_metrics:
            return {}
        
        total_time = time.perf_counter() - self.start_time
        end_memory = self._get_memory_mb()
        
        # 聚合所有股票的指标
        total_db_queries = sum(m.db_queries for m in self.stock_metrics.values())
        total_db_time = sum(m.db_query_time for m in self.stock_metrics.values())
        total_file_writes = sum(m.file_writes for m in self.stock_metrics.values())
        total_file_time = sum(m.file_write_time for m in self.stock_metrics.values())
        total_file_size = sum(m.file_write_size for m in self.stock_metrics.values())
        
        total_kline_count = sum(m.kline_count for m in self.stock_metrics.values())
        total_opp_count = sum(m.opportunity_count for m in self.stock_metrics.values())
        total_target_count = sum(m.target_count for m in self.stock_metrics.values())
        
        # 计算平均值
        avg_time_per_stock = total_time / len(self.stock_metrics)
        avg_db_queries_per_stock = total_db_queries / len(self.stock_metrics)
        avg_memory_per_stock = sum(m.memory_peak for m in self.stock_metrics.values()) / len(self.stock_metrics)
        
        return {
            'summary': {
                'total_stocks': len(self.stock_metrics),
                'total_time_seconds': total_time,  # 实际墙钟时间（主进程）
                'total_time_minutes': total_time / 60,
                'avg_time_per_stock_seconds': avg_time_per_stock,
            },
            'io': {
                'total_db_queries': total_db_queries,
                'avg_db_queries_per_stock': avg_db_queries_per_stock,
                # 注意：这是累加的所有进程的查询时间总和（多进程并行时，会大于实际墙钟时间）
                # 实际墙钟时间请参考 summary.total_time_seconds
                'total_db_time_seconds': total_db_time,
                'avg_db_time_per_query_ms': (total_db_time / total_db_queries * 1000) if total_db_queries > 0 else 0,
                'total_file_writes': total_file_writes,
                'total_file_size_mb': total_file_size / (1024 * 1024),
                # 注意：这是累加的所有进程的文件写入时间总和
                'total_file_time_seconds': total_file_time,
            },
            'data': {
                'total_kline_count': total_kline_count,
                'total_opportunity_count': total_opp_count,
                'total_target_count': total_target_count,
                'avg_opportunities_per_stock': total_opp_count / len(self.stock_metrics) if self.stock_metrics else 0,
            },
            'memory': {
                'start_mb': self.start_memory,
                'end_mb': end_memory,
                'delta_mb': end_memory - self.start_memory,
                'avg_peak_per_stock_mb': avg_memory_per_stock,
            },
            'time_breakdown': {
                'avg_load_data_ms': sum(m.time_load_data for m in self.stock_metrics.values()) / len(self.stock_metrics) * 1000,
                'avg_enumerate_ms': sum(m.time_enumerate for m in self.stock_metrics.values()) / len(self.stock_metrics) * 1000,
                'avg_serialize_ms': sum(m.time_serialize for m in self.stock_metrics.values()) / len(self.stock_metrics) * 1000,
            }
        }
    
    def print_report(self):
        """打印性能报告"""
        summary = self.get_summary()
        if not summary:
            logger.info("没有性能数据")
            return
        
        logger.info("\n" + "="*80)
        logger.info("📊 枚举器性能分析报告")
        logger.info("="*80)
        
        # 总体统计
        logger.info(f"\n【总体统计】")
        logger.info(f"  股票数量: {summary['summary']['total_stocks']}")
        logger.info(f"  总耗时: {summary['summary']['total_time_minutes']:.2f} 分钟 ({summary['summary']['total_time_seconds']:.2f} 秒)")
        logger.info(f"  平均每只股票: {summary['summary']['avg_time_per_stock_seconds']:.2f} 秒")
        
        # IO 统计
        logger.info(f"\n【IO 统计】")
        logger.info(f"  数据库查询总数: {summary['io']['total_db_queries']}")
        logger.info(f"  平均每只股票查询: {summary['io']['avg_db_queries_per_stock']:.1f} 次")
        logger.info(f"  数据库查询累计时间: {summary['io']['total_db_time_seconds']:.2f} 秒 (所有进程累加，非实际墙钟时间)")
        logger.info(f"  平均每次查询: {summary['io']['avg_db_time_per_query_ms']:.2f} ms")
        logger.info(f"  文件写入总数: {summary['io']['total_file_writes']}")
        logger.info(f"  文件写入总大小: {summary['io']['total_file_size_mb']:.2f} MB")
        logger.info(f"  文件写入累计时间: {summary['io']['total_file_time_seconds']:.2f} 秒 (所有进程累加，非实际墙钟时间)")
        
        # 数据统计
        logger.info(f"\n【数据统计】")
        logger.info(f"  总 K 线数: {summary['data']['total_kline_count']:,}")
        logger.info(f"  总机会数: {summary['data']['total_opportunity_count']:,}")
        logger.info(f"  总目标数: {summary['data']['total_target_count']:,}")
        logger.info(f"  平均每只股票机会数: {summary['data']['avg_opportunities_per_stock']:.1f}")
        
        # 内存统计
        logger.info(f"\n【内存统计】")
        logger.info(f"  开始内存: {summary['memory']['start_mb']:.2f} MB")
        logger.info(f"  结束内存: {summary['memory']['end_mb']:.2f} MB")
        logger.info(f"  内存增长: {summary['memory']['delta_mb']:.2f} MB")
        logger.info(f"  平均每只股票峰值: {summary['memory']['avg_peak_per_stock_mb']:.2f} MB")
        
        # 时间分解
        logger.info(f"\n【时间分解（平均每只股票）】")
        logger.info(f"  数据加载: {summary['time_breakdown']['avg_load_data_ms']:.1f} ms")
        logger.info(f"  枚举计算: {summary['time_breakdown']['avg_enumerate_ms']:.1f} ms")
        logger.info(f"  序列化: {summary['time_breakdown']['avg_serialize_ms']:.1f} ms")
        
        logger.info("="*80 + "\n")
