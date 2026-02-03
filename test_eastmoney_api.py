#!/usr/bin/env python3
"""测试东方财富 API 调用"""
import requests

url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
params = {
    "secid": "0.000001",  # 平安银行
    "ut": "fa5fd1943c7b386f172d6893dbfba10b",
    "fields1": "f1,f2,f3,f4,f5,f6",
    "fields2": "f51,f53",
    "klt": "101",
    "fqt": "1",
    "end": "20241231",
    "beg": "20000101",
}
# 伪装成浏览器，避免被反爬拦截
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://quote.eastmoney.com/",
    "Origin": "https://quote.eastmoney.com",
    "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

print("请求 URL:", f"{url}?secid={params['secid']}&ut={params['ut']}&fields1=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6&fields2=f51%2Cf53&klt=101&fqt=1&end={params['end']}&beg={params['beg']}")
print("-" * 80)

# 使用 Session：先访问 quote 页面获取 Cookie，再请求 API（模拟浏览器行为）
session = requests.Session()
session.headers.update(headers)
try:
    print("1. 预热：访问 quote 页面...")
    session.get("https://quote.eastmoney.com/sz000001.html", timeout=10)
    print("2. 请求 API...")
    r = session.get(url, params=params, timeout=30)
    print(f"状态码: {r.status_code}")
    data = r.json()
    print(f"rc: {data.get('rc')}")
    print(f"data 存在: {'data' in data}")
    if data.get("data") and data["data"].get("klines"):
        klines = data["data"]["klines"]
        print(f"klines 条数: {len(klines)}")
        print(f"前 3 条: {klines[:3]}")
    else:
        print(f"完整响应: {data}")
except Exception as e:
    print(f"错误: {e}")
