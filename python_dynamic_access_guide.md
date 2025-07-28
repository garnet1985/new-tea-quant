# Python 动态属性访问指南

## 问题：`api.daily` 和 `api['daily']` 是否等价？

**答案：不是所有对象都支持这两种语法！**

## 1. 不同对象的支持情况

### 1.1 字典对象 ✅
```python
# 字典支持 [] 语法
data = {'daily': some_function, 'weekly': some_function}
result1 = data['daily']()  # ✅ 可以
result2 = data.daily()     # ❌ 不可以（除非是特殊字典）
```

### 1.2 普通对象 ❌
```python
# 普通对象不支持 [] 语法
class API:
    def __init__(self):
        self.daily = lambda: print("daily")
        self.weekly = lambda: print("weekly")

api = API()
api.daily()     # ✅ 可以
api['daily']()  # ❌ TypeError: 'API' object is not subscriptable
```

### 1.3 实现了 `__getitem__` 的对象 ✅
```python
# 实现了 __getitem__ 的对象支持 [] 语法
class API:
    def __init__(self):
        self.daily = lambda: print("daily")
        self.weekly = lambda: print("weekly")
    
    def __getitem__(self, key):
        return getattr(self, key)

api = API()
api.daily()     # ✅ 可以
api['daily']()  # ✅ 可以
```

## 2. Tushare API 的情况

Tushare 的 `DataApi` 对象**不支持** `[]` 语法：

```python
import tushare as ts
api = ts.pro_api()

# ✅ 这些可以工作
api.daily()
api.weekly()
api.monthly()

# ❌ 这些会失败
api['daily']()   # TypeError: 'DataApi' object is not subscriptable
api['weekly']()  # TypeError: 'DataApi' object is not subscriptable
```

## 3. 正确的动态访问方法

### 3.1 使用 `getattr()` （推荐）
```python
def fetch_kline_data(self, job: dict):
    method = getattr(self.api, job['term'])
    return method(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
```

### 3.2 使用字典映射
```python
def fetch_kline_data(self, job: dict):
    api_methods = {
        'daily': self.api.daily,
        'weekly': self.api.weekly,
        'monthly': self.api.monthly
    }
    method = api_methods[job['term']]
    return method(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
```

### 3.3 使用 if-elif 链
```python
def fetch_kline_data(self, job: dict):
    if job['term'] == 'daily':
        return self.api.daily(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
    elif job['term'] == 'weekly':
        return self.api.weekly(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
    elif job['term'] == 'monthly':
        return self.api.monthly(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
```

## 4. 与 JavaScript 的对比

### JavaScript
```javascript
// JavaScript 中对象属性访问
const api = {
    daily: () => console.log('daily'),
    weekly: () => console.log('weekly')
};

// 两种语法都支持
api.daily();    // ✅ 可以
api['daily'](); // ✅ 可以
```

### Python
```python
# Python 中需要对象实现 __getitem__ 才支持 []
class API:
    def __init__(self):
        self.daily = lambda: print('daily')
        self.weekly = lambda: print('weekly')
    
    def __getitem__(self, key):
        return getattr(self, key)

api = API()
api.daily()     # ✅ 可以
api['daily']()  # ✅ 可以（因为实现了 __getitem__）
```

## 5. 最佳实践建议

1. **使用 `getattr()`**：最通用和 Pythonic 的方式
2. **添加错误处理**：
   ```python
   def fetch_kline_data(self, job: dict):
       try:
           method = getattr(self.api, job['term'])
           return method(ts_code=job['ts_code'], start_date=job['start_date'], end_date=job['end_date'])
       except AttributeError:
           raise ValueError(f"Unknown term: {job['term']}")
   ```

3. **提供默认值**：
   ```python
   method = getattr(self.api, job['term'], None)
   if method is None:
       raise ValueError(f"Unknown term: {job['term']}")
   ```

## 6. 总结

- **`api.daily`**：直接属性访问，适用于已知属性名
- **`api['daily']`**：需要对象实现 `__getitem__` 方法
- **`getattr(api, 'daily')`**：最通用的动态访问方式，推荐使用

对于 Tushare API，应该使用 `getattr(self.api, job['term'])` 而不是 `self.api[job['term']]`。 