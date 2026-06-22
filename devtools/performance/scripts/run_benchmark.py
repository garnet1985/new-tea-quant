#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
枚举器性能基准测试 Runner

用法:
    python run_benchmark.py --mode stock_based
    python run_benchmark.py --mode calendar_sliced
    python run_benchmark.py --mode all

流程:
    1. 从 benchmark_strategies/ 复制策略到 userspace/strategies/
    2. 清理缓存保证冷启动
    3. 调用 core 策略引擎执行枚举
    4. 解析 0_performance_report.json
    5. 生成 Markdown 性能报告
    6. 清理复制的策略目录
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── 项目路径 ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
BENCHMARK_STRATEGIES_DIR = PROJECT_ROOT / "devtools" / "benchmarks" / "performance" / "benchmark_strategies"
USERSPACE_STRATEGIES_DIR = PROJECT_ROOT / "userspace" / "strategies"
OUTPUT_BASE = Path(__file__).resolve().parent

# 模式 → benchmark 策略目录名
MODE_STRATEGY_MAP = {
    "stock_based": "stock_based",
    "calendar_sliced": "cross_sectional",
}

# 模式 → userspace 中的临时策略名
MODE_TEMP_NAME = {
    "stock_based": "benchmark_stock_based",
    "calendar_sliced": "benchmark_calendar_sliced",
}


def _resolve_python() -> str:
    """获取当前 Python 解释器路径。"""
    return sys.executable


def _copy_strategy(mode: str) -> Path:
    """复制 benchmark 策略到 userspace，返回目标目录。"""
    src = BENCHMARK_STRATEGIES_DIR / MODE_STRATEGY_MAP[mode]
    dst = USERSPACE_STRATEGIES_DIR / MODE_TEMP_NAME[mode]

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"[COPY] {src} -> {dst}")
    return dst


def _cleanup_strategy(mode: str) -> None:
    """清理复制的策略目录。"""
    dst = USERSPACE_STRATEGIES_DIR / MODE_TEMP_NAME[mode]
    if dst.exists():
        shutil.rmtree(dst)
        print(f"[CLEAN] Removed {dst}")


def _clear_cache() -> None:
    """清理 DB 缓存以保证冷启动。"""
    cache_dirs = [
        PROJECT_ROOT / ".cache" / "duckdb",
        PROJECT_ROOT / ".cache" / "strategy",
    ]
    for d in cache_dirs:
        if d.exists():
            # 只清理文件级缓存（不删目录结构）
            for f in d.rglob("*"):
                if f.is_file():
                    f.unlink()
            print(f"[CACHE] Cleared {d}")


def _run_enumeration(strategy_name: str) -> bool:
    """调用 CLI 执行枚举。返回是否成功。"""
    python = _resolve_python()
    cli_path = PROJECT_ROOT / "cli.py"

    cmd = [
        python, str(cli_path), "strategy_enumerate",
        "--strategy", strategy_name,
        "-f",
    ]

    print(f"\n[RUN] {' '.join(cmd)}")
    print("-" * 60)

    start = time.perf_counter()
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    elapsed = time.perf_counter() - start

    print(f"[DONE] Exit code: {result.returncode}, Wall: {elapsed:.2f}s")

    if result.returncode != 0:
        print("[STDERR]", result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr)
        return False

    return True


def _find_performance_report(strategy_name: str) -> Optional[Path]:
    """查找最新版本的 performance report。"""
    enum_dir = USERSPACE_STRATEGIES_DIR / strategy_name / "results" / "simulations" / "enum"
    if not enum_dir.is_dir():
        return None

    versions = sorted(
        [d for d in enum_dir.iterdir() if d.is_dir() and d.name.isdigit()],
        key=lambda x: int(x.name),
        reverse=True,
    )
    for v in versions:
        report = v / "0_performance_report.json"
        if report.is_file():
            return report
    return None


def _load_report(report_path: Path) -> Dict[str, Any]:
    """加载并解析 performance report JSON。"""
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fmt(v: Any, fmt: str = "", fallback: str = "N/A") -> str:
    """安全格式化数值，非数值类型返回 fallback。"""
    if v is None:
        return fallback
    try:
        return f"{v:{fmt}}"
    except (ValueError, TypeError):
        return str(v)


def _generate_markdown(report: Dict[str, Any], mode: str) -> str:
    """从 performance report 生成 Markdown 报告。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    summary = report.get("summary", {})
    runtime = report.get("runtime", {})
    data = report.get("data", {})
    storage = report.get("storage", {})
    memory = report.get("memory", {})
    phases = report.get("worker_phase_sums_seconds", {})
    breakdown = report.get("time_breakdown", {})
    file_io = report.get("file_io", {})

    exec_mode = runtime.get('execution_mode', mode)
    is_calendar_sliced = (exec_mode == "calendar_sliced")

    lines = [
        f"# Enumerator Performance Benchmark Report",
        "",
        f"> Generated: {now} | Mode: **{exec_mode}**",
        "",
        "---",
        "",
        "## Environment",
        "",
        "| Item | Value |",
        "|------|-------|",
        f"| Execution Mode | `{exec_mode}` |",
        f"| DB Engine | `{runtime.get('db_engine', 'N/A')}` |",
        f"| Max Workers | {runtime.get('max_workers', 'N/A')} |",
        f"| Stock Count | {runtime.get('stock_count', summary.get('total_stocks', 'N/A'))} |",
        f"| Date Range | {runtime.get('start_date', 'N/A')} ~ {runtime.get('end_date', 'N/A')} |",
        f"| Cache Hit | {'Yes' if runtime.get('cache_hit') else 'No (Cold Start)'} |",
        "",
        "## Throughput Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Stocks | {_fmt(summary.get('total_stocks'))} |",
        f"| Stocks Skipped (short data) | {_fmt(summary.get('stocks_skipped_short_data'))} |",
        f"| Total K-Lines | {_fmt(data.get('total_kline_count'), ',')} |",
        f"| Total Opportunities | {_fmt(data.get('total_opportunity_count'))} |",
        f"| Total Targets | {_fmt(data.get('total_target_count'))} |",
        f"| Avg Opportunities/Stock | {_fmt(data.get('avg_opportunities_per_stock'), '.2f')} |",
        "",
        "## Timing",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Wall Clock | **{_fmt(summary.get('wall_clock_seconds'), '.3f')}s** ({_fmt(summary.get('wall_clock_minutes'), '.2f')}min) |",
    ]

    if not is_calendar_sliced:
        # stock_based 模式：显示并行度相关指标
        lines.extend([
            f"| Sum Worker Total | {_fmt(summary.get('sum_worker_total_seconds'), '.3f')}s |",
            f"| Parallelism Factor | **{summary.get('parallelism_factor', 0):.2f}x** |",
            f"| Avg per Stock | {summary.get('avg_wall_clock_per_stock_seconds', 0)*1000:.1f}ms |",
        ])
    else:
        # calendar_sliced 模式：显示 Reader/Compute 分解
        wall = summary.get('wall_clock_seconds', 0) or 0
        compute = summary.get('sum_worker_total_seconds', 0) or 0
        lines.extend([
            f"| Compute Time (profiler) | {_fmt(compute, '.3f')}s |",
            f"| Overhead (Reader+Schedule) | {_fmt(wall - compute, '.3f')}s |",
            f"| Compute Ratio | {_fmt(100 * compute / max(wall, 0.001), '.1f')}% |",
        ])

    lines.extend([
        "",
        "## Worker Phase Breakdown (sum across all stocks)",
        "",
        "| Phase | Time (s) | % of Worker | Avg/Stock (ms) |",
        "|-------|----------|-------------|----------------|",
    ])

    total_worker = phases.get("total", 1)
    n_stocks = max(summary.get("total_stocks", 1), 1)

    phase_labels = {
        "load_contracts": "Load Contracts",
        "calculate_indicators": "Calculate Indicators",
        "build_cursor": "Build Cursor",
        "load_extras": "Load Extras",
        "enumerate": "Enumerate (Strategy)",
        "serialize": "Serialize",
        "save_csv": "Save CSV",
    }

    for key, label in phase_labels.items():
        t = phases.get(key, 0)
        pct = (t / total_worker * 100) if total_worker > 0 else 0
        avg_ms = t / n_stocks * 1000
        lines.append(f"| {label} | {t:.4f} | {pct:.1f}% | {avg_ms:.1f} |")

    lines.extend([
        "",
        "## I/O & Storage",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Storage Load Calls | {_fmt(storage.get('total_load_calls'))} |",
        f"| Avg Calls/Stock | {_fmt(storage.get('avg_load_calls_per_stock'), '.1f')} |",
        f"| Sum Load Time | {_fmt(storage.get('sum_load_time_seconds'), '.4f')}s |",
        f"| Avg Load Time/Call | {_fmt(storage.get('avg_load_time_per_call_ms'), '.2f')}ms |",
        f"| File Writes | {_fmt(file_io.get('total_writes'))} |",
        f"| File Write Size | {_fmt(file_io.get('sum_write_size_mb'), '.3f')}MB |",
        "",
        "## Memory",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Parent Start RSS | {_fmt(memory.get('parent_start_mb'), '.1f')}MB |",
        f"| Parent End RSS | {_fmt(memory.get('parent_end_mb'), '.1f')}MB |",
        f"| Parent Delta | {_fmt(memory.get('parent_delta_mb'), '+.1f')}MB |",
        f"| Avg Peak/Stock | {_fmt(memory.get('avg_peak_per_stock_mb'), '.1f')}MB |",
        "",
        "## Per-Stock Timing Detail",
        "",
        "| Phase | Avg (ms) | Dominant |",
        "|-------|----------|----------|",
    ])

    phase_avg_map = {
        "Load Data": breakdown.get("avg_load_data_ms", 0),
        "Load Contracts": breakdown.get("avg_load_contracts_ms", 0),
        "Calc Indicators": breakdown.get("avg_calculate_indicators_ms", 0),
        "Build Cursor": breakdown.get("avg_build_cursor_ms", 0),
        "Load Extras": breakdown.get("avg_load_extras_ms", 0),
        "Enumerate": breakdown.get("avg_enumerate_ms", 0),
        "Serialize": breakdown.get("avg_serialize_ms", 0),
        "Save CSV": breakdown.get("avg_save_csv_ms", 0),
        "Total/Stock": breakdown.get("avg_total_per_stock_ms", 0),
    }

    dominant = breakdown.get("dominant_phase", "unknown")
    for name, avg_ms in phase_avg_map.items():
        is_dominant = " <-- dominant" if name.lower().replace(" ", "_") == dominant.replace("_", "") else ""
        lines.append(f"| {name} | {_fmt(avg_ms, '.2f')} |{is_dominant}|")

    lines.extend([
        "",
        "---",
        f"*Report generated by run_benchmark.py | schema_version={report.get('schema_version', '?')}*",
        "",
    ])

    return "\n".join(lines)


def run_single_mode(mode: str) -> Optional[Path]:
    """运行单个模式的基准测试。返回生成的报告路径。"""
    strategy_name = MODE_TEMP_NAME[mode]
    output_dir = OUTPUT_BASE / mode / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Benchmark Mode: {mode}")
    print(f"  Strategy: {strategy_name}")
    print(f"{'='*60}")

    # 1. 复制策略
    _copy_strategy(mode)

    try:
        # 2. 清理缓存（冷启动）
        _clear_cache()

        # 3. 运行枚举
        success = _run_enumeration(strategy_name)
        if not success:
            print(f"[FAIL] Enumeration failed for {mode}")
            return None

        # 4. 查找报告
        report_path = _find_performance_report(strategy_name)
        if not report_path:
            print(f"[WARN] No performance report found for {strategy_name}")
            return None

        # 5. 加载并解析
        report = _load_report(report_path)
        print(f"\n[REPORT] Loaded from {report_path}")
        print(f"  stocks={report.get('summary', {}).get('total_stocks')}, "
              f"wall={report.get('summary', {}).get('wall_clock_seconds', 0):.3f}s, "
              f"parallelism={report.get('summary', {}).get('parallelism_factor', 0):.2f}x")
        if report.get("runtime"):
            rt = report["runtime"]
            print(f"  mode={rt.get('execution_mode')}, workers={rt.get('max_workers')}, "
                  f"db={rt.get('db_engine')}, cache={'hit' if rt.get('cache_hit') else 'miss'}")

        # 6. 生成 Markdown 报告
        md_content = _generate_markdown(report, mode)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        md_path = output_dir / f"benchmark_report_{timestamp}.md"

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"\n[OUTPUT] Report saved to {md_path}")

        # 同时复制一份原始 JSON 到 output 目录
        json_copy = output_dir / f"raw_report_{timestamp}.json"
        shutil.copy2(report_path, json_copy)
        print(f"[OUTPUT] Raw JSON saved to {json_copy}")

        return md_path

    finally:
        # 7. 清理策略
        _cleanup_strategy(mode)


def main():
    parser = argparse.ArgumentParser(description="Enumerator Performance Benchmark Runner")
    parser.add_argument(
        "--mode",
        choices=["stock_based", "calendar_sliced", "all"],
        default="all",
        help="Benchmark mode to run (default: all)",
    )
    args = parser.parse_args()

    modes = ["stock_based", "calendar_sliced"] if args.mode == "all" else [args.mode]
    results: List[str] = []

    for mode in modes:
        report_path = run_single_mode(mode)
        if report_path:
            results.append(f"{mode}: {report_path}")

    print(f"\n{'='*60}")
    print("  Benchmark Complete")
    print(f"{'='*60}")
    for r in results:
        print(f"  - {r}")

    if len(results) < len(modes):
        sys.exit(1)


if __name__ == "__main__":
    main()
