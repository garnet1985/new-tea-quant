#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
进度跟踪器
"""

import threading
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ProgressTracker:
    """通用的进度跟踪器"""
    
    def __init__(self, total_jobs: int, job_name: str, show_details: bool = True):
        """
        初始化进度跟踪器
        
        Args:
            total_jobs: 总任务数
            job_name: 任务名称
            show_details: 是否显示详细信息
        """
        self.total_jobs = total_jobs
        self.job_name = job_name
        self.show_details = show_details
        
        # 计数器
        self.completed_jobs = 0
        self.failed_jobs = 0
        self.start_time = datetime.now()
        
        # 线程锁
        self.lock = threading.Lock()
    
    def update(self, job_id: str, status: str, details: Optional[str] = None) -> None:
        """
        更新进度
        
        Args:
            job_id: 任务ID
            status: 任务状态 ('success', 'failed', 'no_data', 'error')
            details: 详细信息
        """
        with self.lock:
            self.completed_jobs += 1
            
            if status in ['failed', 'error']:
                self.failed_jobs += 1
            
            # 计算进度
            progress = (self.completed_jobs / self.total_jobs * 100) if self.total_jobs > 0 else 100
            
            # 构建日志消息
            if self.show_details and details:
                message = f"📊 {self.job_name}更新进度: {self.completed_jobs}/{self.total_jobs} ({progress:.1f}%) - {job_id} {status}: {details}"
            else:
                message = f"📊 {self.job_name}更新进度: {self.completed_jobs}/{self.total_jobs} ({progress:.1f}%)"
            
            logger.info(message)
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取当前状态
        
        Returns:
            包含当前状态的字典
        """
        with self.lock:
            current_time = datetime.now()
            elapsed_time = (current_time - self.start_time).total_seconds()
            
            progress = (self.completed_jobs / self.total_jobs * 100) if self.total_jobs > 0 else 100
            success_rate = ((self.completed_jobs - self.failed_jobs) / self.completed_jobs * 100) if self.completed_jobs > 0 else 0
            
            # 估算剩余时间
            if self.completed_jobs > 0 and self.completed_jobs < self.total_jobs:
                avg_time_per_job = elapsed_time / self.completed_jobs
                remaining_jobs = self.total_jobs - self.completed_jobs
                estimated_remaining_time = avg_time_per_job * remaining_jobs
            else:
                estimated_remaining_time = 0
            
            return {
                'job_name': self.job_name,
                'total_jobs': self.total_jobs,
                'completed_jobs': self.completed_jobs,
                'failed_jobs': self.failed_jobs,
                'progress_percentage': progress,
                'success_rate': success_rate,
                'elapsed_time': elapsed_time,
                'estimated_remaining_time': estimated_remaining_time,
                'start_time': self.start_time,
                'current_time': current_time
            }
    
    def print_summary(self) -> None:
        """打印进度摘要"""
        status = self.get_status()
        
        logger.info(f"✅ {self.job_name}任务完成摘要:")
        logger.info(f"   📊 总进度: {status['completed_jobs']}/{status['total_jobs']} ({status['progress_percentage']:.1f}%)")
        logger.info(f"   ✅ 成功: {status['completed_jobs'] - status['failed_jobs']}")
        logger.info(f"   ❌ 失败: {status['failed_jobs']}")
        logger.info(f"   📈 成功率: {status['success_rate']:.1f}%")
        logger.info(f"   ⏱️ 总耗时: {status['elapsed_time']:.1f}秒")
        
        if status['estimated_remaining_time'] > 0:
            logger.info(f"   ⏳ 预计剩余: {status['estimated_remaining_time']:.1f}秒")


class ProgressTrackerManager:
    """进度跟踪器管理器"""
    
    def __init__(self):
        """初始化进度跟踪器管理器"""
        self.trackers: Dict[str, ProgressTracker] = {}
        self._lock = threading.Lock()
    
    def create_tracker(self, tracker_id: str, total_jobs: int, job_name: str, show_details: bool = True) -> ProgressTracker:
        """
        创建新的进度跟踪器
        
        Args:
            tracker_id: 跟踪器ID
            total_jobs: 总任务数
            job_name: 任务名称
            show_details: 是否显示详细信息
            
        Returns:
            ProgressTracker实例
        """
        with self._lock:
            tracker = ProgressTracker(total_jobs, job_name, show_details)
            self.trackers[tracker_id] = tracker
            return tracker
    
    def get_tracker(self, tracker_id: str) -> Optional[ProgressTracker]:
        """
        获取进度跟踪器
        
        Args:
            tracker_id: 跟踪器ID
            
        Returns:
            ProgressTracker实例，如果不存在返回None
        """
        with self._lock:
            return self.trackers.get(tracker_id)
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有跟踪器的状态
        
        Returns:
            所有跟踪器状态的字典
        """
        return {tracker_id: tracker.get_status() for tracker_id, tracker in self.trackers.items()}
