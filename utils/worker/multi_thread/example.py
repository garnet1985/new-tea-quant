#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FuturesWorker 使用示例
展示多线程执行器的基本用法和两种执行模式
"""

import time
import random
from .futures_worker import FuturesWorker, ExecutionMode


def io_intensive_task(data):
    """
    IO密集型任务示例：模拟API调用
    """
    task_id = data['task_id']
    url = data['url']
    
    # 模拟网络延迟
    time.sleep(random.uniform(0.1, 0.3))
    
    # 模拟API响应
    response_data = {
        'task_id': task_id,
        'url': url,
        'status': 'success',
        'data': f'Response from {url}',
        'timestamp': time.time()
    }
    
    return response_data


def database_query_task(data):
    """
    数据库查询任务示例
    """
    query_id = data['query_id']
    table = data['table']
    
    # 模拟数据库查询延迟
    time.sleep(random.uniform(0.05, 0.2))
    
    # 模拟查询结果
    result = {
        'query_id': query_id,
        'table': table,
        'rows': random.randint(10, 100),
        'execution_time': random.uniform(0.05, 0.2),
        'timestamp': time.time()
    }
    
    return result


def file_processing_task(data):
    """
    文件处理任务示例
    """
    file_id = data['file_id']
    file_path = data['file_path']
    
    # 模拟文件读取和处理延迟
    time.sleep(random.uniform(0.1, 0.5))
    
    # 模拟处理结果
    result = {
        'file_id': file_id,
        'file_path': file_path,
        'lines_processed': random.randint(100, 1000),
        'processing_time': random.uniform(0.1, 0.5),
        'timestamp': time.time()
    }
    
    return result


def demo_basic_usage():
    """演示基本用法"""
    print("\n" + "="*60)
    print("基本用法演示 - IO密集型任务")
    print("="*60)
    
    # 创建任务数据
    jobs = []
    for i in range(10):
        jobs.append({
            'id': f'api_task_{i}',
            'data': {
                'task_id': i,
                'url': f'https://api.example.com/data/{i}'
            }
        })
    
    # 创建FuturesWorker
    worker = FuturesWorker(
        max_workers=5,
        execution_mode=ExecutionMode.PARALLEL,
        job_executor=io_intensive_task,
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
    results = worker.get_results()
    successful_results = [r for r in results if r.status.value == 'completed']
    print(f"\n前3个API调用结果:")
    for i, result in enumerate(successful_results[:3]):
        data = result.result
        print(f"  {i+1}. 任务{data['task_id']}: {data['status']}")


def demo_parallel_vs_serial():
    """演示并行vs串行执行"""
    print("\n" + "="*60)
    print("并行 vs 串行执行对比")
    print("="*60)
    
    # 创建任务数据
    jobs = []
    for i in range(8):
        jobs.append({
            'id': f'db_query_{i}',
            'data': {
                'query_id': i,
                'table': f'table_{i % 3}'
            }
        })
    
    # 测试并行执行
    print("测试并行执行...")
    worker_parallel = FuturesWorker(
        max_workers=4,
        execution_mode=ExecutionMode.PARALLEL,
        job_executor=database_query_task,
        is_verbose=False
    )
    
    start_time = time.time()
    stats_parallel = worker_parallel.run_jobs(jobs)
    parallel_time = time.time() - start_time
    
    # 测试串行执行
    print("测试串行执行...")
    worker_serial = FuturesWorker(
        max_workers=1,
        execution_mode=ExecutionMode.SERIAL,
        job_executor=database_query_task,
        is_verbose=False
    )
    
    start_time = time.time()
    stats_serial = worker_serial.run_jobs(jobs)
    serial_time = time.time() - start_time
    
    # 显示对比结果
    print(f"\n执行时间对比:")
    print(f"并行执行耗时: {parallel_time:.2f}秒")
    print(f"串行执行耗时: {serial_time:.2f}秒")
    print(f"性能提升: {((serial_time - parallel_time) / serial_time * 100):.1f}%")


def demo_different_worker_counts():
    """演示不同线程数的性能"""
    print("\n" + "="*60)
    print("不同线程数性能对比")
    print("="*60)
    
    # 创建任务数据
    jobs = []
    for i in range(20):
        jobs.append({
            'id': f'file_task_{i}',
            'data': {
                'file_id': i,
                'file_path': f'/data/file_{i}.txt'
            }
        })
    
    # 测试不同线程数
    worker_counts = [1, 2, 4, 8]
    results = {}
    
    for worker_count in worker_counts:
        print(f"测试 {worker_count} 个线程...")
        
        worker = FuturesWorker(
            max_workers=worker_count,
            execution_mode=ExecutionMode.PARALLEL,
            job_executor=file_processing_task,
            is_verbose=False
        )
        
        start_time = time.time()
        stats = worker.run_jobs(jobs)
        execution_time = time.time() - start_time
        
        results[worker_count] = execution_time
        print(f"  {worker_count} 线程耗时: {execution_time:.2f}秒")
    
    # 显示性能对比
    print(f"\n性能对比结果:")
    baseline = results[1]
    for worker_count, exec_time in results.items():
        speedup = baseline / exec_time
        print(f"  {worker_count} 线程: {exec_time:.2f}秒 (加速比: {speedup:.1f}x)")


def demo_mixed_task_types():
    """演示混合任务类型"""
    print("\n" + "="*60)
    print("混合任务类型演示")
    print("="*60)
    
    # 创建混合任务
    jobs = []
    
    # API任务
    for i in range(5):
        jobs.append({
            'id': f'api_{i}',
            'data': {
                'task_id': i,
                'url': f'https://api.example.com/data/{i}'
            }
        })
    
    # 数据库任务
    for i in range(5):
        jobs.append({
            'id': f'db_{i}',
            'data': {
                'query_id': i,
                'table': f'table_{i}'
            }
        })
    
    # 文件处理任务
    for i in range(5):
        jobs.append({
            'id': f'file_{i}',
            'data': {
                'file_id': i,
                'file_path': f'/data/file_{i}.txt'
            }
        })
    
    # 创建执行器
    worker = FuturesWorker(
        max_workers=6,
        execution_mode=ExecutionMode.PARALLEL,
        job_executor=lambda data: {
            'api': io_intensive_task,
            'db': database_query_task,
            'file': file_processing_task
        }[data['id'].split('_')[0]](data),
        is_verbose=True
    )
    
    # 执行任务
    start_time = time.time()
    stats = worker.run_jobs(jobs)
    end_time = time.time()
    
    # 显示结果
    worker.print_stats()
    print(f"实际总耗时: {end_time - start_time:.2f}秒")
    
    # 按任务类型统计
    results = worker.get_results()
    successful_results = [r for r in results if r.status.value == 'completed']
    task_types = {}
    for result in successful_results:
        task_type = result.job_id.split('_')[0]
        if task_type not in task_types:
            task_types[task_type] = 0
        task_types[task_type] += 1
    
    print(f"\n任务类型统计:")
    for task_type, count in task_types.items():
        print(f"  {task_type}: {count} 个任务")


def demo_error_handling():
    """演示错误处理"""
    print("\n" + "="*60)
    print("错误处理演示")
    print("="*60)
    
    def error_prone_task(data):
        """容易出错的任务"""
        task_id = data['task_id']
        
        # 模拟随机错误
        if random.random() < 0.3:  # 30%概率出错
            raise Exception(f"任务 {task_id} 执行失败")
        
        time.sleep(0.1)  # 模拟处理时间
        return {'task_id': task_id, 'status': 'success'}
    
    # 创建任务
    jobs = []
    for i in range(10):
        jobs.append({
            'id': f'error_task_{i}',
            'data': {'task_id': i}
        })
    
    # 创建执行器
    worker = FuturesWorker(
        max_workers=3,
        execution_mode=ExecutionMode.PARALLEL,
        job_executor=error_prone_task,
        is_verbose=True
    )
    
    # 执行任务
    stats = worker.run_jobs(jobs)
    
    # 显示结果
    worker.print_stats()
    
    # 显示错误信息
    results = worker.get_results()
    failed_results = [r for r in results if r.status.value == 'failed']
    if failed_results:
        print(f"\n失败任务详情:")
        for result in failed_results:
            print(f"  任务 {result.job_id}: {result.error}")


if __name__ == "__main__":
    print("FuturesWorker 多线程执行器示例")
    print("="*60)
    
    try:
        # 基本用法演示
        demo_basic_usage()
        
        # 执行模式对比
        demo_parallel_vs_serial()
        
        # 线程数性能对比
        demo_different_worker_counts()
        
        # 混合任务类型
        demo_mixed_task_types()
        
        # 错误处理
        demo_error_handling()
        
    except KeyboardInterrupt:
        print("\n用户中断执行")
    except Exception as e:
        print(f"执行出错: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("示例演示完成！")
    print("="*60)
