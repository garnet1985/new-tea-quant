"""
分析API失败模式

实时监控并统计：
- 哪些API失败最多
- 哪些股票失败最多
- 失败的时间分布
"""

import re
from collections import Counter, defaultdict
from loguru import logger
import sys

logger.remove()
logger.add(sys.stderr, level="INFO")


def analyze_log_file(log_file_path):
    """分析日志文件"""
    
    api_failures = Counter()  # API失败计数
    stock_failures = Counter()  # 股票失败计数
    job_failures = []  # Job失败详情
    
    with open(log_file_path, 'r') as f:
        for line in f:
            # 匹配: ⚠️  [000001.SZ 平安银行] API [daily] 失败或返回空数据
            api_match = re.search(r'⚠️\s+\[(\S+)\s+([^\]]+)\] API \[(\w+)\] 失败或返回空数据', line)
            if api_match:
                stock_id = api_match.group(1)
                stock_name = api_match.group(2)
                api_name = api_match.group(3)
                
                api_failures[api_name] += 1
                stock_failures[f"{stock_id} {stock_name}"] += 1
            
            # 匹配: ⚠️  [000001.SZ 平安银行] Job执行失败，以下API未成功: monthly
            job_match = re.search(r'⚠️\s+\[(\S+)\s+([^\]]+)\] Job执行失败，以下API未成功: ([^，]+)', line)
            if job_match:
                stock_id = job_match.group(1)
                stock_name = job_match.group(2)
                failed_apis = job_match.group(3)
                
                job_failures.append({
                    'stock': f"{stock_id} {stock_name}",
                    'apis': failed_apis
                })
    
    return api_failures, stock_failures, job_failures


def analyze_stdin():
    """实时分析标准输入"""
    
    logger.info("=" * 60)
    logger.info("API失败实时统计（Ctrl+C停止）")
    logger.info("=" * 60)
    logger.info("提示：将程序输出重定向到此脚本")
    logger.info("用法：python start.py 2>&1 | python analyze_api_failures.py")
    logger.info("")
    
    api_failures = Counter()
    stock_failures = Counter()
    total_jobs = 0
    failed_jobs = 0
    
    try:
        for line in sys.stdin:
            # 打印原始行（可选）
            # print(line, end='')
            
            # 统计总任务数
            if '🔄 开始更新 stock_kline，共' in line:
                match = re.search(r'共\s+(\d+)\s+个任务', line)
                if match:
                    total_jobs = int(match.group(1))
                    logger.info(f"📊 总任务数: {total_jobs}")
            
            # 匹配API失败
            api_match = re.search(r'⚠️\s+\[(\S+).*?\] API \[(\w+)\] 失败或返回空数据', line)
            if api_match:
                stock_id = api_match.group(1)
                api_name = api_match.group(2)
                api_failures[api_name] += 1
            
            # 匹配Job失败
            if 'Job执行失败' in line:
                failed_jobs += 1
                
                # 每100个失败输出一次统计
                if failed_jobs % 100 == 0:
                    logger.info(f"\n📊 当前统计（已处理{failed_jobs}个失败）:")
                    logger.info(f"API失败次数:")
                    for api, count in api_failures.most_common(10):
                        logger.info(f"  - {api:15s}: {count:5d}次")
                    logger.info("")
    
    except KeyboardInterrupt:
        pass
    
    # 最终统计
    logger.info("\n" + "=" * 60)
    logger.info("最终统计")
    logger.info("=" * 60)
    logger.info(f"总任务数: {total_jobs}")
    logger.info(f"失败Job数: {failed_jobs}")
    logger.info(f"成功率: {((total_jobs - failed_jobs) / total_jobs * 100):.1f}%" if total_jobs > 0 else "N/A")
    logger.info("")
    
    logger.info("API失败排行:")
    for api, count in api_failures.most_common():
        pct = (count / failed_jobs * 100) if failed_jobs > 0 else 0
        logger.info(f"  {api:15s}: {count:5d}次 ({pct:5.1f}%)")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 分析日志文件
        log_file = sys.argv[1]
        logger.info(f"分析日志文件: {log_file}")
        api_failures, stock_failures, job_failures = analyze_log_file(log_file)
        
        logger.info("\n" + "=" * 60)
        logger.info("API失败统计")
        logger.info("=" * 60)
        for api, count in api_failures.most_common():
            logger.info(f"  {api:15s}: {count:5d}次")
        
        logger.info("\n" + "=" * 60)
        logger.info("失败最多的股票（前20）")
        logger.info("=" * 60)
        for stock, count in stock_failures.most_common(20):
            logger.info(f"  {stock:30s}: {count:2d}次")
        
        logger.info(f"\n总Job失败数: {len(job_failures)}")
    else:
        # 实时分析
        analyze_stdin()
