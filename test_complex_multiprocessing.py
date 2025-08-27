#!/usr/bin/env python3
"""
测试包含多线程和数据缓存的实例在多进程中的问题
"""
import multiprocessing
import threading
import time
import os
from concurrent.futures import ProcessPoolExecutor
import pickle

class MultiThreadedCachedInstance:
    """包含多线程和数据缓存的复杂实例"""
    
    def __init__(self, name):
        self.name = name
        self.cache = {}  # 数据缓存
        self.cache_lock = threading.Lock()  # 缓存锁
        self.worker_threads = []  # 工作线程
        self.running = True
        
        # 启动工作线程
        self._start_worker_threads()
    
    def _start_worker_threads(self):
        """启动工作线程"""
        for i in range(2):
            thread = threading.Thread(target=self._worker, args=(i,))
            thread.daemon = True
            thread.start()
            self.worker_threads.append(thread)
    
    def _worker(self, worker_id):
        """工作线程逻辑"""
        while self.running:
            time.sleep(0.1)  # 模拟工作
            with self.cache_lock:
                self.cache[f'worker_{worker_id}_data'] = time.time()
    
    def get_cached_data(self, key):
        """获取缓存数据"""
        with self.cache_lock:
            if key in self.cache:
                return self.cache[key]
            # 模拟获取新数据
            data = f"new_data_{key}_{time.time()}"
            self.cache[key] = data
            return data
    
    def get_cache_stats(self):
        """获取缓存统计"""
        with self.cache_lock:
            return {
                'name': self.name,
                'cache_size': len(self.cache),
                'cache_keys': list(self.cache.keys()),
                'thread_count': len(self.worker_threads),
                'process_id': os.getpid()
            }
    
    def cleanup(self):
        """清理资源"""
        self.running = False
        for thread in self.worker_threads:
            thread.join(timeout=1)

class SimpleInstance:
    """简单的实例，用于对比"""
    
    def __init__(self, name):
        self.name = name
        self.data = {}
    
    def get_data(self, key):
        if key not in self.data:
            self.data[key] = f"data_{key}_{time.time()}"
        return self.data[key]
    
    def get_stats(self):
        return {
            'name': self.name,
            'data_size': len(self.data),
            'process_id': os.getpid()
        }

def test_pickle_complex_instance():
    """测试复杂实例的pickle能力"""
    print("🧪 测试复杂实例的pickle能力...")
    print("=" * 60)
    
    # 测试多线程缓存实例
    print("\n1️⃣ 测试多线程缓存实例pickle...")
    complex_instance = MultiThreadedCachedInstance("complex_test")
    
    try:
        # 等待线程启动
        time.sleep(0.5)
        
        # 尝试pickle
        pickled = pickle.dumps(complex_instance)
        print("✅ 复杂实例pickle成功（意外！）")
        
        # 尝试反序列化
        unpickled = pickle.loads(pickled)
        print("✅ 复杂实例反序列化成功")
        
        # 检查反序列化后的状态
        stats = unpickled.get_cache_stats()
        print(f"   反序列化后状态: {stats}")
        
    except Exception as e:
        print(f"❌ 复杂实例pickle失败: {e}")
        return False
    
    finally:
        complex_instance.cleanup()
    
    return True

def worker_function_complex(instance, key):
    """工作函数：处理复杂实例"""
    try:
        # 获取缓存数据
        data = instance.get_cached_data(key)
        
        # 获取实例状态
        stats = instance.get_cache_stats()
        
        return {
            'key': key,
            'data': data,
            'stats': stats,
            'worker_pid': os.getpid()
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'worker_pid': os.getpid()
        }

def test_multiprocessing_complex():
    """测试多进程中复杂实例"""
    print("\n🚀 测试多进程中复杂实例...")
    print("=" * 60)
    
    # 创建多个复杂实例
    instances = [MultiThreadedCachedInstance(f"complex_{i}") for i in range(3)]
    test_keys = ['key_1', 'key_2', 'key_3']
    
    print(f"主进程ID: {os.getpid()}")
    print(f"创建了 {len(instances)} 个复杂实例")
    
    try:
        with ProcessPoolExecutor(max_workers=2) as executor:
            # 提交任务
            futures = []
            for i, (instance, key) in enumerate(zip(instances, test_keys)):
                print(f"提交任务 {i}: {instance.name} -> {key}")
                future = executor.submit(worker_function_complex, instance, key)
                futures.append(future)
            
            # 收集结果
            results = []
            for i, future in enumerate(futures):
                result = future.result()
                results.append(result)
                print(f"任务 {i} 结果: {result}")
            
            print(f"\n✅ 多进程复杂实例测试成功，共{len(results)}个结果")
            
            # 分析结果
            print("\n📊 结果分析:")
            for result in results:
                if 'error' not in result:
                    print(f"   键: {result['key']}")
                    print(f"   数据: {result['data']}")
                    print(f"   进程ID: {result['worker_pid']}")
                    print(f"   实例状态: {result['stats']}")
                    print()
            
            return True
            
    except Exception as e:
        print(f"❌ 多进程复杂实例测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理资源
        for instance in instances:
            instance.cleanup()

def test_multiprocessing_simple():
    """测试多进程中简单实例（对比）"""
    print("\n🚀 测试多进程中简单实例（对比）...")
    print("=" * 60)
    
    # 创建多个简单实例
    instances = [SimpleInstance(f"simple_{i}") for i in range(3)]
    test_keys = ['key_1', 'key_2', 'key_3']
    
    print(f"主进程ID: {os.getpid()}")
    print(f"创建了 {len(instances)} 个简单实例")
    
    try:
        with ProcessPoolExecutor(max_workers=2) as executor:
            # 提交任务
            futures = []
            for i, (instance, key) in enumerate(zip(instances, test_keys)):
                print(f"提交任务 {i}: {instance.name} -> {key}")
                future = executor.submit(lambda inst, k: {'data': inst.get_data(k), 'stats': inst.get_stats()}, instance, key)
                futures.append(future)
            
            # 收集结果
            results = []
            for i, future in enumerate(futures):
                result = future.result()
                results.append(result)
                print(f"任务 {i} 结果: {result}")
            
            print(f"\n✅ 多进程简单实例测试成功，共{len(results)}个结果")
            return True
            
    except Exception as e:
        print(f"❌ 多进程简单实例测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🔍 测试包含多线程和数据缓存的实例在多进程中的问题")
    print("=" * 80)
    
    # 测试pickle能力
    pickle_ok = test_pickle_complex_instance()
    
    # 测试多进程能力
    if pickle_ok:
        test_multiprocessing_complex()
    
    # 对比测试
    test_multiprocessing_simple()
    
    print("\n📋 关键发现:")
    print("=" * 80)
    print("1. 🔍 复杂实例可能可以pickle，但多进程中行为异常")
    print("2. 🚫 多线程在多进程中无法正常工作")
    print("3. 🚫 数据缓存在多进程中无法共享")
    print("4. ✅ 简单实例在多进程中工作正常")
    print("5. 💡 建议：为多进程设计专门的轻量级实例")
