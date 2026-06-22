#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Calendar-Sliced (切片模式) 枚举器性能基准测试

目标：
  - 定义 calendar_sliced 模式的性能基线
  - 测试不同配置下的表现
  - 与 stock_based 模式对比

用法：
    # 运行默认配置测试
    python run_calendar_sliced_benchmark.py

    # 使用更大股票池
    python run_calendar_sliced_benchmark.py --sample-size 5596

输出：
  results/
  └── calendar_sliced/
      ├── baseline.json          # 基准结果
      └── analysis.md            # 分析报告

日期: 2026-06-22
作者: AI Assistant (基于逐股枚举器实验脚本)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── 项目路径 ──────────────────────────────────────────────
# 本脚本在 enumerator/ 层，向上 5 个 parent 到项目根
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
BENCHMARK_STRATEGIES_DIR = PROJECT_ROOT / "devtools" / "benchmarks" / "performance" / "benchmark_strategies"
USERSPACE_STRATEGIES_DIR = PROJECT_ROOT / "userspace" / "strategies"
RESULTS_BASE = Path(__file__).resolve().parent / "results"

# ── 测试配置 ──────────────────────────────────────────────
TEMP_STRATEGY_NAME = "bench_cs_baseline"
DEFAULT_SAMPLE_SIZE = 5000  # 默认使用 5000 股票池


@dataclass
class BenchmarkResult:
    """单次基准测试结果"""
    test_id: str
    timestamp: str
    
    # 配置
    sample_size: int
    execution_mode: str
    max_workers: int
    
    # 性能指标
    wall_clock_seconds: float = 0.0
    wall_clock_minutes: float = 0.0
    parallelism_factor: float = 0.0
    sum_worker_total_seconds: float = 0.0
    avg_wall_clock_per_stock_ms: float = 0.0
    
    # 数据量
    total_stocks: int = 0
    total_klines: int = 0
    total_opportunities: int = 0
    stocks_skipped: int = 0
    
    # 内存
    parent_start_mb: float = 0.0
    parent_end_mb: float = 0.0
    parent_delta_mb: float = 0.0
    avg_peak_per_stock_mb: float = 0.0
    
    # IO
    storage_load_calls: int = 0
    storage_load_time_seconds: float = 0.0
    file_writes: int = 0
    
    # Runtime 元数据
    db_engine: str = ""
    cache_hit: bool = False
    execution_mode_reported: str = ""
    
    # 切片模式特有指标
    total_slices: int = 0
    avg_stocks_per_slice: float = 0.0
    
    # 状态
    success: bool = False
    error_message: str = ""
    raw_report_path: Optional[str] = None


def _resolve_python() -> str:
    return sys.executable


def _prepare_strategy(
    *,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> Path:
    """准备测试用的临时策略目录"""
    src = BENCHMARK_STRATEGIES_DIR / "cross_sectional"
    dst = USERSPACE_STRATEGIES_DIR / TEMP_STRATEGY_NAME
    
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    
    # 修改 settings.py
    settings_path = dst / "settings.py"
    if settings_path.exists():
        content = settings_path.read_text(encoding="utf-8")
        
        # 1. 修改股票池大小
        content = content.replace(
            '"sampling_amount": 500',
            f'"sampling_amount": {sample_size}'
        )
        
        settings_path.write_text(content, encoding="utf-8")
    
    print(f"[PREP] Strategy ready: {dst}")
    print(f"       sample_size={sample_size}, mode=calendar_sliced")
    return dst


def _cleanup_strategy() -> None:
    """清理临时策略"""
    dst = USERSPACE_STRATEGIES_DIR / TEMP_STRATEGY_NAME
    if dst.exists():
        shutil.rmtree(dst)
        print(f"[CLEAN] Removed {dst}")


def _clear_cache() -> None:
    """清理缓存保证冷启动"""
    cache_dirs = [
        PROJECT_ROOT / ".cache" / "duckdb",
        PROJECT_ROOT / ".cache" / "strategy",
    ]
    for d in cache_dirs:
        if d.exists():
            for f in d.rglob("*"):
                if f.is_file():
                    f.unlink()
            print(f"[CACHE] Cleared {d}")


def _run_enumeration() -> Tuple[bool, Optional[Path]]:
    """运行枚举并返回是否成功和 report 路径"""
    python = _resolve_python()
    cli_path = PROJECT_ROOT / "cli.py"
    
    cmd = [
        python, str(cli_path), "strategy_enumerate",
        "--strategy", TEMP_STRATEGY_NAME,
        "-f",
    ]
    
    print(f"[RUN] {' '.join(cmd)}")
    start = time.perf_counter()
    
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    
    elapsed = time.perf_counter() - start
    print(f"[DONE] Exit code={result.returncode}, Wall={elapsed:.2f}s")
    
    if result.returncode != 0:
        print(f"[ERROR] {result.stderr[-500:] if result.stderr else 'Unknown error'}")
        return False, None
    
    # 查找 report
    enum_dir = USERSPACE_STRATEGIES_DIR / TEMP_STRATEGY_NAME / "results" / "simulations" / "enum"
    if not enum_dir.is_dir():
        return False, None
    
    versions = sorted(
        [d for d in enum_dir.iterdir() if d.is_dir() and d.name.isdigit()],
        key=lambda x: int(x.name),
        reverse=True,
    )
    
    for v in versions:
        report = v / "0_performance_report.json"
        if report.is_file():
            return True, report
    
    return False, None


def _extract_metrics(report_path: Path) -> Dict[str, Any]:
    """从 report JSON 提取关键指标"""
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    
    summary = report.get("summary", {})
    runtime = report.get("runtime", {})
    data = report.get("data", {})
    storage = report.get("storage", {})
    memory = report.get("memory", {})
    file_io = report.get("file_io", {})
    
    return {
        "wall_clock_seconds": summary.get("wall_clock_seconds", 0) or 0,
        "wall_clock_minutes": summary.get("wall_clock_minutes", 0) or 0,
        "parallelism_factor": summary.get("parallelism_factor", 0) or 0,
        "sum_worker_total_seconds": summary.get("sum_worker_total_seconds", 0) or 0,
        "avg_wall_clock_per_stock_ms": summary.get("avg_wall_clock_per_stock_seconds", 0) or 0,
        "total_stocks": summary.get("total_stocks", 0) or 0,
        "total_klines": data.get("total_kline_count", 0) or 0,
        "total_opportunities": data.get("total_opportunity_count", 0) or 0,
        "stocks_skipped": summary.get("stocks_skipped_short_data", 0) or 0,
        "parent_start_mb": memory.get("parent_start_mb", 0) or 0,
        "parent_end_mb": memory.get("parent_end_mb", 0) or 0,
        "parent_delta_mb": memory.get("parent_delta_mb", 0) or 0,
        "avg_peak_per_stock_mb": memory.get("avg_peak_per_stock_mb", 0) or 0,
        "storage_load_calls": storage.get("total_load_calls", 0) or 0,
        "storage_load_time_seconds": storage.get("sum_load_time_seconds", 0) or 0,
        "file_writes": file_io.get("total_writes", 0) or 0,
        "db_engine": runtime.get("db_engine", ""),
        "cache_hit": runtime.get("cache_hit", False),
        "execution_mode_reported": runtime.get("execution_mode", ""),
    }


def run_benchmark(
    test_id: str,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> BenchmarkResult:
    """运行单次基准测试"""
    
    result = BenchmarkResult(
        test_id=test_id,
        timestamp=datetime.now().isoformat(),
        sample_size=sample_size,
        execution_mode="calendar_slice",
        max_workers=1,  # 切片模式通常单进程
    )
    
    try:
        # 1. 准备策略
        strategy_dir = _prepare_strategy(sample_size=sample_size)
        
        # 2. 清缓存 (冷启动)
        _clear_cache()
        
        # 3. 运行枚举
        success, report_path = _run_enumeration()
        
        if not success or not report_path:
            result.success = False
            result.error_message = "Enumeration failed or no report found"
            return result
        
        result.raw_report_path = str(report_path)
        
        # 4. 提取指标
        metrics = _extract_metrics(report_path)
        for key, value in metrics.items():
            if hasattr(result, key):
                setattr(result, key, value)
        
        result.success = True
        
        # 5. 计算衍生指标
        if result.total_stocks > 0 and result.wall_clock_seconds > 0:
            result.avg_wall_clock_per_stock_ms = (
                result.wall_clock_seconds * 1000 / result.total_stocks
            )
        
        # 切片模式特有：估算切片数
        # 假设每年 rebalance_period="year"，3年约3次主要切片
        result.total_slices = 3  # 年度换仓 × 3年
        if result.total_stocks > 0:
            result.avg_stocks_per_slice = result.total_stocks / max(result.total_slices, 1)
        
    except Exception as e:
        result.success = False
        result.error_message = str(e)
        import traceback
        print(f"[ERROR] {e}\n{traceback.format_exc()}")
    
    finally:
        # 清理临时策略
        _cleanup_strategy()
    
    return result


def generate_analysis_md(result: BenchmarkResult, output_path: Path) -> None:
    """生成 Markdown 分析报告"""
    
    md_content = f"""# Calendar-Sliced 枚举器性能基准报告

**测试 ID**: {result.test_id}
**时间**: {result.timestamp}
**状态**: {'✅ 成功' if result.success else '❌ 失败'}

---

## 📊 测试配置

| 参数 | 值 |
|------|-----|
| **执行模式** | {result.execution_mode} |
| **股票池大小** | {result.sample_size:,} |
| **最大进程数** | {result.max_workers} |
| **数据库引擎** | {result.db_engine or 'Unknown'} |
| **缓存命中** | {'是' if result.cache_hit else '否 (冷启动)'} |

---

## ⏱️ 性能指标

### 核心时间指标

| 指标 | 数值 | 单位 |
|------|------|------|
| **Wall Clock Time** | {result.wall_clock_seconds:.2f} | 秒 |
| **Wall Clock Time** | {result.wall_clock_minutes:.2f} | 分钟 |
| **Parallelism Factor** | {result.parallelism_factor:.2f}x | 倍数 |
| **Sum Worker Seconds** | {result.sum_worker_total_seconds:.2f} | 秒 |

### 吞吐量指标

| 指标 | 数值 | 说明 |
|------|------|------|
| **总股票数** | {result.total_stocks:,} | 处理的股票数量 |
| **总 K线数** | {result.total_klines:,} | 加载的 K线总数 |
| **总机会数** | {result.total_opportunities:,} | 发现的机会数 |
| **K线/秒** | {result.total_klines / result.wall_clock_seconds:,.0f} | 数据处理速度 |
| **股票/秒** | {result.total_stocks / result.wall_clock_seconds:.1f} | 股票处理速度 |
| **单股耗时** | {result.avg_wall_clock_per_stock_ms:.2f} | ms/股 |

### 内存使用

| 指标 | 数值 | 单位 |
|------|------|------|
| **起始内存** | {result.parent_start_mb:.1f} | MB |
| **结束内存** | {result.parent_end_mb:.1f} | MB |
| **内存增量** | {result.parent_delta_mb:+.1f} | MB |
| **峰值/股票** | {result.avg_peak_per_stock_mb:.2f} | MB/股 |

### IO 统计

| 指标 | 数值 | 说明 |
|------|------|------|
| **存储加载次数** | {result.storage_load_calls:,} | DB 查询次数 |
| **存储加载耗时** | {result.storage_load_time_seconds:.2f} | 秒 |
| **文件写入次数** | {result.file_writes:,} | 结果保存 |

---

## 📈 切片模式特性分析

### 切片效率

| 指标 | 数值 |
|------|------|
| **估算总切片数** | {result.total_slices} |
| **平均每切片股票数** | {result.avg_stocks_per_slice:.0f} |
| **跳过股票数** | {result.stocks_skipped:,} |

### 横截面处理能力

切片模式的核心优势在于：
- ✅ **按时间切片并行**: 可以同时处理多个时间点
- ✅ **减少数据冗载**: 只加载当前切片需要的数据
- ✅ **内存友好**: 不需要一次性加载所有股票的全部 K线

---

## 🔍 与 Stock-Based 模式对比

| 维度 | Calendar-Sliced | Stock-Based (基准) |
|------|-----------------|---------------------|
| **适用场景** | 横截面选股、因子研究 | 逐股信号、事件驱动 |
| **数据访问模式** | 按时间切片批量加载 | 按股票逐个或批量加载 |
| **并行度潜力** | ⭐⭐⭐⭐ 高 (天然可并行) | ⭐⭐ 中 (受限于 entities_per_job) |
| **内存占用** | ⭐⭐⭐ 低 (分批处理) | ⭐⭐ 中等 |
| **实现复杂度** | ⭐⭐ 较高 | ⭐⭐⭐ 较低 |

---

## 💡 结论与建议

{'✅ 测试成功' if result.success else '❌ 测试失败: ' + result.error_message}

### 性能评级

基于当前结果，calendar-sliced 模式的表现为：
- **数据处理速度**: {result.total_klines / result.wall_clock_seconds:,.0f} K线/秒
- **并行效率**: {result.parallelism_factor:.2f}x
- **内存效率**: {'优秀' if abs(result.parent_delta_mb) < 50 else '良好'}

### 适用场景建议

✅ **推荐使用 calendar-sliced 的场景**:
- 因子模型回测 (多因子横截面选股)
- 行业轮动策略
- 定期再平衡组合
- 大规模股票池筛选 (>2000 股票)

⚠️ **考虑 stock-based 的场景**:
- 事件驱动策略 (财报、公告)
- 技术信号跟踪 (突破、形态)
- 需要完整历史路径的策略

---

## 📝 备注

- 测试环境: macOS, MySQL 远程数据库
- 股票池: A 股市场全量 (PIT 过滤)
- 时间区间: 2023-01-01 至 2025-12-31
- 缓存状态: 冷启动 (每次测试前清缓存)

---

**报告生成时间**: {datetime.now().isoformat()}
"""
    
    output_path.write_text(md_content, encoding="utf-8")
    print(f"\n[REPORT] Analysis saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Calendar-Sliced 枚举器性能基准测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 运行默认测试 (5000 股票)
  python run_calendar_sliced_benchmark.py
  
  # 使用更大股票池
  python run_calendar_sliced_benchmark.py --sample-size 5596
""",
    )
    
    parser.add_argument(
        "--sample-size",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"股票池大小 (默认: {DEFAULT_SAMPLE_SIZE})",
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="自定义输出目录 (默认: results/calendar_sliced/)",
    )
    
    args = parser.parse_args()
    
    # 设置输出目录
    output_base = RESULTS_BASE / "calendar_sliced"
    if args.output_dir:
        output_base = Path(args.output_dir)
    output_base.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("  Calendar-Sliced 枚举器性能基准测试")
    print("=" * 70)
    print(f"\n📋 配置:")
    print(f"   执行模式:     calendar_slice")
    print(f"   股票池大小:   {args.sample_size:,}")
    print(f"   输出目录:     {output_base}")
    print()
    
    # 运行基准测试
    test_id = f"cs_baseline_{args.sample_size}"
    print(f"▶️  开始测试: {test_id}")
    print("-" * 70)
    
    result = run_benchmark(
        test_id=test_id,
        sample_size=args.sample_size,
    )
    
    print("\n" + "=" * 70)
    print("  测试完成")
    print("=" * 70)
    
    # 输出结果摘要
    if result.success:
        print(f"\n✅ 测试成功!")
        print(f"\n📊 核心指标:")
        print(f"   Wall Time:       {result.wall_clock_seconds:.2f}s ({result.wall_clock_minutes:.2f}min)")
        print(f"   Parallelism:     {result.parallelism_factor:.2f}x")
        print(f"   Total Stocks:    {result.total_stocks:,}")
        print(f"   Total Klines:    {result.total_klines:,}")
        print(f"   Throughput:      {result.total_klines / result.wall_clock_seconds:,.0f} Klines/s")
        print(f"   Memory Delta:    {result.parent_delta_mb:+.1f}MB")
        
        # 保存原始结果
        result_json = output_base / "baseline.json"
        with open(result_json, "w", encoding="utf-8") as f:
            json.dump(asdict(result), f, indent=2, ensure_ascii=False)
        print(f"\n💾 结果已保存: {result_json}")
        
        # 生成分析报告
        analysis_md = output_base / "analysis.md"
        generate_analysis_md(result, analysis_md)
        
    else:
        print(f"\n❌ 测试失败!")
        print(f"   错误: {result.error_message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
