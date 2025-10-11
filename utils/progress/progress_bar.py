#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
酷炫的进度条显示
"""

import sys
import threading
import time
import os
from typing import Dict, Any, Optional
from datetime import datetime


class ProgressBar:
    """酷炫的进度条"""
    
    def __init__(self, total: int, width: int = 50, show_details: bool = True, fixed_position: bool = True):
        """
        初始化进度条
        
        Args:
            total: 总任务数
            width: 进度条宽度
            show_details: 是否显示详细信息
            fixed_position: 是否固定在窗口底部
        """
        self.total = total
        self.width = width
        self.show_details = show_details
        self.fixed_position = fixed_position
        self.current = 0
        self.start_time = datetime.now()
        self.last_update_time = self.start_time
        
        # 线程锁
        self.lock = threading.Lock()
        
        # 状态统计
        self.success_count = 0
        self.failed_count = 0
        self.no_data_count = 0
        
        # 固定位置相关
        self.is_initialized = False
        self.terminal_height = self._get_terminal_height()
        
        # 显示进度条
        self._display()
    
    def _get_terminal_height(self) -> int:
        """获取终端高度"""
        try:
            # 尝试获取终端高度
            if hasattr(os, 'get_terminal_size'):
                height = os.get_terminal_size().lines
                # 确保进度条在最后一行
                return height
            else:
                # 备用方法
                import subprocess
                result = subprocess.run(['tput', 'lines'], capture_output=True, text=True)
                if result.returncode == 0:
                    return int(result.stdout.strip())
        except Exception as e:
            logger.debug(f"Failed to get terminal height from tput: {e}")
        
        # 如果无法检测，尝试从环境变量获取
        try:
            height = int(os.environ.get('LINES', '24'))
            return height
        except Exception as e:
            logger.debug(f"Failed to get terminal height from env: {e}")
            
        return 24  # 默认高度
    
    def _move_to_bottom(self):
        """移动到终端底部"""
        if self.fixed_position:
            # 移动到终端底部
            sys.stderr.write(f"\033[{self.terminal_height};1H")
            sys.stderr.flush()
    
    def _save_cursor_position(self):
        """保存光标位置"""
        if self.fixed_position:
            sys.stderr.write("\033[s")
            sys.stderr.flush()
    
    def _restore_cursor_position(self):
        """恢复光标位置"""
        if self.fixed_position:
            sys.stderr.write("\033[u")
            sys.stderr.flush()
    
    def update(self, status: str, details: str = ""):
        """
        更新进度
        
        Args:
            status: 任务状态 ('success', 'failed', 'no_data', 'error')
            details: 详细信息
        """
        with self.lock:
            self.current += 1
            
            # 更新统计
            if status == 'success':
                self.success_count += 1
            elif status in ['failed', 'error']:
                self.failed_count += 1
            elif status == 'no_data':
                self.no_data_count += 1
            
            self.last_update_time = datetime.now()
            self._display()
    
    def _display(self):
        """显示进度条"""
        if self.total == 0:
            return
        
        # 计算进度百分比
        progress = (self.current / self.total) * 100
        
        # 计算进度条填充长度
        filled_length = int(self.width * self.current // self.total)
        
        # 构建进度条
        bar = '█' * filled_length + '░' * (self.width - filled_length)
        
        # 计算耗时
        elapsed_time = (datetime.now() - self.start_time).total_seconds()
        
        # 估算剩余时间
        if self.current > 0 and self.current < self.total:
            avg_time_per_task = elapsed_time / self.current
            remaining_tasks = self.total - self.current
            estimated_remaining = avg_time_per_task * remaining_tasks
            eta_str = f"ETA: {estimated_remaining:.0f}s"
        else:
            eta_str = "完成"
        
        # 构建状态信息
        status_info = f"✅ {self.success_count} ❌ {self.failed_count} ⚠️ {self.no_data_count}"
        
        # 构建完整的进度条
        progress_bar = f"\n[{bar}] {progress:.1f}% ({self.current}/{self.total}) {status_info} ⏱️{elapsed_time:.0f}s {eta_str}\n\n"
        
        if self.fixed_position:
            # 固定位置模式：完全独立于日志输出
            # 保存当前光标位置
            sys.stderr.write("\033[s")
            # 移动到终端底部
            sys.stderr.write(f"\033[{self.terminal_height};1H")
            # 清除当前行
            sys.stderr.write("\033[2K")
            # 显示进度条
            sys.stderr.write(progress_bar)
            # 恢复光标位置
            sys.stderr.write("\033[u")
            sys.stderr.flush()
        else:
            # 普通模式：使用\r覆盖当前行
            sys.stderr.write(f"\r{progress_bar}")
            sys.stderr.flush()
            
            # 如果完成，换行
            if self.current >= self.total:
                sys.stderr.write("\n")
                sys.stderr.flush()
    
    def finish(self):
        """完成进度条"""
        with self.lock:
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            
            # 显示最终统计
            final_stats = f"🎉 任务完成! 总计: {self.current}, 成功: {self.success_count}, 失败: {self.failed_count}, 无数据: {self.no_data_count}, 耗时: {elapsed_time:.1f}s"
            
            if self.fixed_position:
                # 固定位置模式：完全独立于日志输出
                # 保存当前光标位置
                sys.stderr.write("\033[s")
                # 移动到终端底部
                sys.stderr.write(f"\033[{self.terminal_height};1H")
                # 清除当前行
                sys.stderr.write("\033[2K")
                # 显示最终统计
                sys.stderr.write(final_stats)
                # 恢复光标位置
                sys.stderr.write("\033[u")
                sys.stderr.flush()
            else:
                # 普通模式：直接输出
                sys.stderr.write(final_stats + "\n")
                sys.stderr.flush()


class ProgressBarManager:
    """进度条管理器"""
    
    def __init__(self):
        """初始化进度条管理器"""
        self.bars: Dict[str, ProgressBar] = {}
        self._lock = threading.Lock()
    
    def create_bar(self, bar_id: str, total: int, width: int = 50, show_details: bool = True, fixed_position: bool = True) -> ProgressBar:
        """
        创建新的进度条
        
        Args:
            bar_id: 进度条ID
            total: 总任务数
            width: 进度条宽度
            show_details: 是否显示详细信息
            fixed_position: 是否固定在窗口底部
            
        Returns:
            ProgressBar实例
        """
        with self._lock:
            bar = ProgressBar(total, width, show_details, fixed_position)
            self.bars[bar_id] = bar
            return bar
    
    def get_bar(self, bar_id: str) -> Optional[ProgressBar]:
        """
        获取进度条
        
        Args:
            bar_id: 进度条ID
            
        Returns:
            ProgressBar实例，如果不存在返回None
        """
        with self._lock:
            return self.bars.get(bar_id)
    
    def finish_bar(self, bar_id: str):
        """
        完成进度条
        
        Args:
            bar_id: 进度条ID
        """
        with self._lock:
            bar = self.bars.get(bar_id)
            if bar:
                bar.finish()
                del self.bars[bar_id]
