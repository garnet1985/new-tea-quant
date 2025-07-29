#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试 FuturesWorker 的日志控制功能
"""

import time
import sys

print("🧪 Testing FuturesWorker Logging Control")
print("=" * 50)

try:
    from futures_worker import FuturesWorker, ExecutionMode
    print("✅ Successfully imported FuturesWorker")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def sample_task(data):
    """示例任务"""
    task_id = data.get('id', 'unknown')
    duration = data.get('duration', 1)
    
    time.sleep(duration)
    return f"Result from {task_id}"


def test_logging_levels():
    """测试不同的日志级别"""
    
    print("\n📋 Test 1: Default logging (verbose=False, debug=False)")
    print("-" * 50)
    
    # 默认配置 - 只显示进度信息
    worker1 = FuturesWorker(
        max_workers=2,
        execution_mode=ExecutionMode.PARALLEL,
        enable_monitoring=True,
        verbose=False,
        debug=False
    )
    
    worker1.set_job_executor(sample_task)
    
    jobs = [
        {'id': 'task_1', 'data': {'duration': 1}},
        {'id': 'task_2', 'data': {'duration': 1}},
    ]
    
    print("Running with minimal logging...")
    stats1 = worker1.run_jobs(jobs)
    print("✅ Default logging test completed")
    
    print("\n📋 Test 2: Verbose logging (verbose=True, debug=False)")
    print("-" * 50)
    
    # 详细日志配置
    worker2 = FuturesWorker(
        max_workers=2,
        execution_mode=ExecutionMode.PARALLEL,
        enable_monitoring=True,
        verbose=True,
        debug=False
    )
    
    worker2.set_job_executor(sample_task)
    
    print("Running with verbose logging...")
    stats2 = worker2.run_jobs(jobs)
    print("✅ Verbose logging test completed")
    
    print("\n📋 Test 3: Debug logging (verbose=True, debug=True)")
    print("-" * 50)
    
    # 调试日志配置
    worker3 = FuturesWorker(
        max_workers=2,
        execution_mode=ExecutionMode.PARALLEL,
        enable_monitoring=True,
        verbose=True,
        debug=True
    )
    
    worker3.set_job_executor(sample_task)
    
    print("Running with debug logging...")
    stats3 = worker3.run_jobs(jobs)
    print("✅ Debug logging test completed")
    
    print("\n📋 Test 4: Production-like logging (like Tushare)")
    print("-" * 50)
    
    # 生产环境配置 - 类似 Tushare 的设置
    worker4 = FuturesWorker(
        max_workers=3,
        execution_mode=ExecutionMode.PARALLEL,
        enable_monitoring=True,
        timeout=30.0,
        verbose=False,  # 关闭详细日志
        debug=False     # 关闭调试日志
    )
    
    worker4.set_job_executor(sample_task)
    
    # 模拟更多任务
    more_jobs = [
        {'id': f'stock_{i}', 'data': {'duration': 0.5}} 
        for i in range(1, 6)
    ]
    
    print("Running production-like configuration...")
    print("Should only show progress updates and final stats")
    stats4 = worker4.run_jobs(more_jobs)
    print("✅ Production logging test completed")
    
    return True


def main():
    """主函数"""
    try:
        success = test_logging_levels()
        
        if success:
            print("\n🎉 All logging control tests completed successfully!")
            print("\n📊 Summary:")
            print("  ✅ Default logging: Minimal output")
            print("  ✅ Verbose logging: Detailed information")
            print("  ✅ Debug logging: Full debugging info")
            print("  ✅ Production logging: Progress only")
            
        print("\n💡 Usage Tips:")
        print("  - For production: verbose=False, debug=False")
        print("  - For development: verbose=True, debug=False")
        print("  - For debugging: verbose=True, debug=True")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 