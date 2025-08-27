#!/usr/bin/env python3
"""
测试多进程中实例对象的行为
"""
import multiprocessing
import threading
import pickle
from concurrent.futures import ProcessPoolExecutor
import os

class SimpleInstance:
    """简单的实例类，可以pickle"""
    def __init__(self, name):
        self.name = name
        self.counter = 0
        self.data = [1, 2, 3, 4, 5]
    
    def process_data(self, input_data):
        """处理数据的方法"""
        self.counter += 1
        result = sum(self.data) + input_data
        return {
            'instance_name': self.name,
            'counter': self.counter,
            'input': input_data,
            'result': result,
            'process_id': os.getpid(),
            'parent_process': getattr(self, 'parent_pid', 'unknown')
        }

class ComplexInstance:
    """复杂的实例类，包含不可pickle的对象"""
    def __init__(self, name):
        self.name = name
        self.lock = threading.Lock()  # ❌ 不可pickle
    
    def process_data(self, input_data):
        """处理数据的方法"""
        with self.lock:
            result = input_data * 2
            return {
                'instance_name': self.name,
                'result': result,
                'process_id': os.getpid()
            }

def test_pickle_ability():
    """测试实例对象的pickle能力"""
    print("🧪 测试实例对象的pickle能力...")
    print("=" * 50)
    
    # 测试简单实例
    print("\n1️⃣ 测试简单实例pickle...")
    simple_instance = SimpleInstance("simple_test")
    simple_instance.parent_pid = os.getpid()
    
    try:
        pickled = pickle.dumps(simple_instance)
        unpickled = pickle.loads(pickled)
        print("✅ 简单实例pickle成功")
        
        # 测试反序列化后的方法调用
        result = unpickled.process_data(100)
        print(f"   反序列化后方法调用成功: {result}")
        
    except Exception as e:
        print(f"❌ 简单实例pickle失败: {e}")
    
    # 测试复杂实例
    print("\n2️⃣ 测试复杂实例pickle...")
    complex_instance = ComplexInstance("complex_test")
    
    try:
        pickled = pickle.dumps(complex_instance)
        print("✅ 复杂实例pickle成功")
        
    except Exception as e:
        print(f"❌ 复杂实例pickle失败: {e}")

def worker_function_simple(instance, data):
    """工作函数：处理简单实例"""
    try:
        # 记录父进程ID
        instance.parent_pid = os.getppid()
        result = instance.process_data(data)
        return result
    except Exception as e:
        return {'error': str(e), 'process_id': os.getpid()}

def test_multiprocessing_simple():
    """测试多进程中简单实例"""
    print("\n🚀 测试多进程中简单实例...")
    print("=" * 50)
    
    # 创建多个简单实例
    instances = [SimpleInstance(f"instance_{i}") for i in range(3)]
    test_data = [10, 20, 30]
    
    print(f"主进程ID: {os.getpid()}")
    print(f"创建了 {len(instances)} 个实例")
    
    try:
        with ProcessPoolExecutor(max_workers=2) as executor:
            # 提交任务
            futures = []
            for i, (instance, data) in enumerate(zip(instances, test_data)):
                print(f"提交任务 {i}: {instance.name} -> {data}")
                future = executor.submit(worker_function_simple, instance, data)
                futures.append(future)
            
            # 收集结果
            results = []
            for i, future in enumerate(futures):
                result = future.result()
                results.append(result)
                print(f"任务 {i} 结果: {result}")
            
            print(f"\n✅ 多进程简单实例测试成功，共{len(results)}个结果")
            
            # 分析结果
            print("\n📊 结果分析:")
            for result in results:
                if 'error' not in result:
                    print(f"   {result['instance_name']}: 进程{result['process_id']}, 父进程{result['parent_process']}")
            
            return True
            
    except Exception as e:
        print(f"❌ 多进程简单实例测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_multiprocessing_complex():
    """测试多进程中复杂实例"""
    print("\n🚀 测试多进程中复杂实例...")
    print("=" * 50)
    
    # 创建多个复杂实例
    instances = [ComplexInstance(f"complex_{i}") for i in range(3)]
    test_data = [10, 20, 30]
    
    print(f"主进程ID: {os.getpid()}")
    print(f"创建了 {len(instances)} 个复杂实例")
    
    try:
        with ProcessPoolExecutor(max_workers=2) as executor:
            # 提交任务
            futures = []
            for i, (instance, data) in enumerate(zip(instances, test_data)):
                print(f"提交任务 {i}: {instance.name} -> {data}")
                future = executor.submit(worker_function_simple, instance, data)
                futures.append(future)
            
            # 收集结果
            results = []
            for i, future in enumerate(futures):
                result = future.result()
                results.append(result)
                print(f"任务 {i} 结果: {result}")
            
            print(f"\n✅ 多进程复杂实例测试成功，共{len(results)}个结果")
            return True
            
    except Exception as e:
        print(f"❌ 多进程复杂实例测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🔍 多进程实例对象行为测试")
    print("=" * 60)
    
    # 测试pickle能力
    test_pickle_ability()
    
    # 测试多进程能力
    test_multiprocessing_simple()
    test_multiprocessing_complex()
    
    print("\n📋 最终总结:")
    print("=" * 60)
    print("1. ✅ 简单实例（无锁、无连接）: 可以pickle和多进程")
    print("2. ❌ 复杂实例（有锁、有连接）: 无法pickle和多进程")
    print("3. 🔄 多进程中实例是独立的副本，不会共享状态")
    print("4. 📝 每个子进程都有自己的实例副本")
    print("5. �� 子进程无法访问主进程的实例状态")
