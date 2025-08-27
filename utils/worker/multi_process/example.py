#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ProcessWorker 使用示例
展示多进程执行器的基本用法和两种执行模式
"""

import time
import random
import multiprocessing as mp
from .process_worker import ProcessWorker, ExecutionMode


def cpu_intensive_task(data):
    """
    CPU密集型任务示例：模拟股票技术分析计算
    """
    stock_id = data['stock_id']
    
    # 模拟复杂的计算过程
    result = 0
    for i in range(1000000):  # 100万次计算
        result += i * random.random()
    
    # 模拟技术指标计算
    if result > 500000:
        signal = "买入"
        confidence = 0.8
    elif result > 300000:
        signal = "持有"
        confidence = 0.6
    else:
        signal = "卖出"
        confidence = 0.7
    
    # 模拟一些IO等待（如数据库查询）
    time.sleep(0.01)
    
    return {
        'stock_id': stock_id,
        'signal': signal,
        'confidence': confidence,
        'score': result,
        'timestamp': time.time()
    }


def demo_basic_usage():
    """演示基本用法"""
    print("\n" + "="*60)
    print("基本用法演示")
    print("="*60)
    
    # 创建任务数据
    jobs = []
    for i in range(10):
        jobs.append({
            'id': f'stock_{i:03d}',
            'data': {'stock_id': f'000{i:03d}.SZ'}
        })
    
    # 创建ProcessWorker
    worker = ProcessWorker(
        max_workers=4,
        execution_mode=ExecutionMode.QUEUE,
        job_executor=cpu_intensive_task,
        is_verbose=True
    )
    
    # 执行任务
    start_time = time.time()
    stats = worker.run_jobs(jobs)
    end_time = time.time()
    
    # 显示结果
    worker.print_stats()
    print(f"实际总耗时: {end_time - start_time:.2f}秒")
    
    # 显示部分结果
    results = worker.get_successful_results()
    print(f"\n前3个分析结果:")
    for i, result in enumerate(results[:3]):
        data = result.result
        print(f"  {i+1}. {data['stock_id']}: {data['signal']} (置信度: {data['confidence']:.1f})")


def demo_batch_mode():
    """演示BATCH模式"""
    print("\n" + "="*60)
    print("BATCH模式演示：batch间串行，batch内并行")
    print("="*60)
    
    # 创建更多任务数据
    jobs = []
    for i in range(20):
        jobs.append({
            'id': f'batch_stock_{i:03d}',
            'data': {'stock_id': f'000{i:03d}.SZ'}
        })
    
    # 创建ProcessWorker，使用BATCH模式
    worker = ProcessWorker(
        max_workers=4,
        execution_mode=ExecutionMode.BATCH,
        batch_size=8,  # 每个batch 8个任务
        job_executor=cpu_intensive_task,
        is_verbose=True
    )
    
    # 执行任务
    start_time = time.time()
    stats = worker.run_jobs(jobs)
    end_time = time.time()
    
    # 显示结果
    worker.print_stats()
    print(f"实际总耗时: {end_time - start_time:.2f}秒")


def demo_queue_mode():
    """演示QUEUE模式"""
    print("\n" + "="*60)
    print("QUEUE模式演示：持续填充进程池")
    print("="*60)
    
    # 创建任务数据
    jobs = []
    for i in range(20):
        jobs.append({
            'id': f'queue_stock_{i:03d}',
            'data': {'stock_id': f'000{i:03d}.SZ'}
        })
    
    # 创建ProcessWorker，使用QUEUE模式
    worker = ProcessWorker(
        max_workers=4,
        execution_mode=ExecutionMode.QUEUE,
        job_executor=cpu_intensive_task,
        is_verbose=True
    )
    
    # 执行任务
    start_time = time.time()
    stats = worker.run_jobs(jobs)
    end_time = time.time()
    
    # 显示结果
    worker.print_stats()
    print(f"实际总耗时: {end_time - start_time:.2f}秒")


def demo_auto_workers():
    """演示自动进程数设置"""
    print("\n" + "="*60)
    print("自动进程数设置演示")
    print("="*60)
    
    print(f"系统CPU核心数: {mp.cpu_count()}")
    
    # 创建任务数据
    jobs = []
    for i in range(8):
        jobs.append({
            'id': f'auto_stock_{i:03d}',
            'data': {'stock_id': f'000{i:03d}.SZ'}
        })
    
    # 创建ProcessWorker，不指定max_workers（自动使用CPU核心数）
    worker = ProcessWorker(
        execution_mode=ExecutionMode.QUEUE,
        job_executor=cpu_intensive_task,
        is_verbose=True
    )
    
    print(f"自动设置的进程数: {worker.max_workers}")
    
    # 执行任务
    stats = worker.run_jobs(jobs)
    worker.print_stats()


def demo_performance_comparison():
    """演示性能对比"""
    print("\n" + "="*60)
    print("性能对比演示")
    print("="*60)
    
    # 创建任务数据
    jobs = []
    for i in range(16):
        jobs.append({
            'id': f'perf_stock_{i:03d}',
            'data': {'stock_id': f'000{i:03d}.SZ'}
        })
    
    # 测试BATCH模式
    print("测试BATCH模式...")
    worker_batch = ProcessWorker(
        max_workers=4,
        execution_mode=ExecutionMode.BATCH,
        batch_size=8,
        job_executor=cpu_intensive_task,
        is_verbose=False
    )
    
    start_time = time.time()
    stats_batch = worker_batch.run_jobs(jobs)
    batch_time = time.time() - start_time
    
    # 测试QUEUE模式
    print("测试QUEUE模式...")
    worker_queue = ProcessWorker(
        max_workers=4,
        execution_mode=ExecutionMode.QUEUE,
        job_executor=cpu_intensive_task,
        is_verbose=False
    )
    
    start_time = time.time()
    stats_queue = worker_queue.run_jobs(jobs)
    queue_time = time.time() - start_time
    
    # 显示对比结果
    print(f"\n性能对比结果:")
    print(f"BATCH模式耗时: {batch_time:.2f}秒")
    print(f"QUEUE模式耗时: {queue_time:.2f}秒")
    print(f"性能提升: {((batch_time - queue_time) / batch_time * 100):.1f}%")


if __name__ == "__main__":
    print("ProcessWorker 多进程执行器示例")
    print("="*60)
    print(f"系统信息: {mp.cpu_count()}个CPU核心")
    
    try:
        # 基本用法演示
        demo_basic_usage()
        
        # 执行模式演示
        demo_batch_mode()
        demo_queue_mode()
        
        # 自动配置演示
        demo_auto_workers()
        
        # 性能对比演示
        demo_performance_comparison()
        
    except KeyboardInterrupt:
        print("\n用户中断执行")
    except Exception as e:
        print(f"执行出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("示例演示完成！")
    print("="*60)
