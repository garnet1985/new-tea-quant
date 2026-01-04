#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
进度跟踪器
"""

import threading
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from app.core.utils.progress.progress_bar import ProgressBarManager


class ProgressTracker:
    """通用的进度跟踪器"""
    
    def __init__(self, total_jobs: int, job_name: str, show_details: bool = True, use_progress_bar: bool = False, fixed_position: bool = True):
        """
        初始化进度跟踪器
        
        Args:
            total_jobs: 总任务数
            job_name: 任务名称
            show_details: 是否显示详细信息
            use_progress_bar: 是否使用进度条模式
            fixed_position: 进度条是否固定在窗口底部
        """
        self.total_jobs = total_jobs
        self.job_name = job_name
        self.show_details = show_details
        self.use_progress_bar = use_progress_bar
        self.fixed_position = fixed_position
        
        # 计数器
        self.completed_jobs = 0
        self.failed_jobs = 0
        self.start_time = datetime.now()
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 进度条管理器
        if self.use_progress_bar:
            self.bar_manager = ProgressBarManager()
            self.progress_bar = self.bar_manager.create_bar(
                f"{job_name}_bar",
                total_jobs,
                width=50,
                show_details=show_details,
                fixed_position=fixed_position
            )
    
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
            
            # 构建日志消息（简化版本，避免与进度条冲突）
            if self.show_details and details:
                message = f"{job_id} {status}: {details}"
            else:
                message = f"{job_id} {status}"
            
            # 输出详细日志（保持原有输出）
            logger.info(message)
            
            # 更新进度条（每当小格子增加时更新）
            if self.use_progress_bar:
                # 计算当前进度条应该有多少个格子
                current_filled_length = int(self.progress_bar.width * self.completed_jobs // self.total_jobs)
                previous_filled_length = int(self.progress_bar.width * (self.completed_jobs - 1) // self.total_jobs)
                
                # 如果格子数量增加了，就更新进度条
                should_update_bar = (
                    current_filled_length > previous_filled_length or  # 格子增加时更新
                    status in ['failed', 'error'] or  # 失败时立即更新
                    self.completed_jobs >= self.total_jobs  # 完成时更新
                )
                
                if should_update_bar:
                    self.progress_bar.update(status, details)
                else:
                    # 即使不更新进度条，也要更新统计数字
                    self.progress_bar.current = self.completed_jobs
                    if status == 'success':
                        self.progress_bar.success_count += 1
                    elif status in ['failed', 'error']:
                        self.progress_bar.failed_count += 1
                    elif status == 'no_data':
                        self.progress_bar.no_data_count += 1
    
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
        
        # 完成进度条
        if self.use_progress_bar:
            self.bar_manager.finish_bar(f"{self.job_name}_bar")


class ProgressTrackerManager:
    """进度跟踪器管理器"""
    
    def __init__(self):
        """初始化进度跟踪器管理器"""
        self.trackers: Dict[str, ProgressTracker] = {}
        self._lock = threading.Lock()
    
    def create_tracker(self, tracker_id: str, total_jobs: int, job_name: str, show_details: bool = True, use_progress_bar: bool = False, fixed_position: bool = True) -> ProgressTracker:
        """
        创建新的进度跟踪器
        
        Args:
            tracker_id: 跟踪器ID
            total_jobs: 总任务数
            job_name: 任务名称
            show_details: 是否显示详细信息
            use_progress_bar: 是否使用进度条模式
            fixed_position: 进度条是否固定在窗口底部
            
        Returns:
            ProgressTracker实例
        """
        with self._lock:
            tracker = ProgressTracker(total_jobs, job_name, show_details, use_progress_bar, fixed_position)
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
