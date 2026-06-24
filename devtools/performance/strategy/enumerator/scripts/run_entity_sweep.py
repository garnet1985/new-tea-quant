#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entity Per Job 实验脚本

目标：
  - 实验1：单进程下改变 entities_per_job，观察 IO/内存变化
  - 实验2：多进程组合 (entities × workers) 矩阵测试

用法：
    # 运行完整实验（约 30-60 分钟）
    python run_entity_sweep.py --phase all

    # 只运行实验组1（单进程 sweep）
    python run_entity_sweep.py --phase phase1

    # 只运行实验组2（多进程矩阵）
    python run_entity_sweep.py --phase phase2

输出：
    experiments/results/
    ├── phase1_single_process/
    │   ├── sweep_data.csv          # 原始数据
    │   └── analysis.md             # 分析报告
    └── phase2_multi_process/
        ├── matrix_data.csv         # 原始数据
        └── analysis.md             # 分析报告
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── 项目路径 ──────────────────────────────────────────────
# run_benchmark.py 在 enumerator/ 层（5 个 parent）
# 本脚本在 experiments/ 层，多一层，所以 6 个 parent
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
BENCHMARK_STRATEGIES_DIR = PROJECT_ROOT / "devtools" / "benchmarks" / "performance" / "benchmark_strategies"
USERSPACE_STRATEGIES_DIR = PROJECT_ROOT / "userspace" / "strategies"
EXPERIMENTS_BASE = Path(__file__).resolve().parent / "results"

# ── 实验配置 ──────────────────────────────────────────────
TEMP_STRATEGY_NAME = "exp_entity_sweep"

# 默认股票池大小（可通过命令行覆盖）
DEFAULT_SAMPLE_SIZE = 5000  # 使用更大股票池以体现批量优势

# 实验1：单进程 entities_per_job sweep
PHASE1_CONFIG = {
    "name": "Single Process Entity Sweep",
    "description": "固定 workers=1，观察 entities_per_job 对性能的影响",
    "max_workers": 1,
    "entities_per_job_list": [1, 5, 10, 20, 50, 100],
}

# 实验2：多进程组合矩阵
PHASE2_CONFIG = {
    "name": "Multi-Process Matrix",
    "description": "测试 (entities_per_job × max_workers) 组合",
    "matrix": [
        # (entities_per_job, max_workers)
        (1, 8),    # baseline: 当前默认
        (10, 8),   # 小 batch + 多进程
        (10, 4),   # 小 batch + 中进程
        (20, 8),   # 中 batch + 多进程
        (20, 4),   # 中 batch + 中进程
        (50, 4),   # 大 batch + 中进程
        (50, 2),   # 大 batch + 少进程
        (100, 4),  # 超大 batch + 中进程
        (100, 2),  # 超大 batch + 少进程
    ],
}


@dataclass
class ExperimentResult:
    """单次实验结果"""
    experiment_id: str
    phase: str
    entities_per_job: int
    max_workers: int
    timestamp: str
    
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
    execution_mode: str = ""
    
    # 状态
    success: bool = False
    error_message: str = ""
    raw_report_path: Optional[str] = None


def _resolve_python() -> str:
    return sys.executable


def _prepare_strategy(
    *,
    entities_per_job: int,
    max_workers: int,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> Path:
    """准备实验用的临时策略目录"""
    src = BENCHMARK_STRATEGIES_DIR / "stock_based"
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
        
        # 2. 注入 performance 配置
        perf_config = f'''
# ── Experiment Injection (auto-generated) ──
"performance": {{
    "dispatch": {{
        "entities_per_job": {entities_per_job},
        "max_parallel_jobs_cap": {max_workers},
    }}
}},
'''
        
        if '"performance"' in content:
            # 替换已有的 performance 配置
            import re
            content = re.sub(
                r'"performance"\s*:\s*\{[^}]*\}',
                perf_config.strip(),
                content,
                flags=re.DOTALL
            )
        else:
            # 在 settings 字典末尾添加
            content = content.rstrip().rstrip('}')
            content += perf_config + "}\n"
        
        settings_path.write_text(content, encoding="utf-8")
    
    print(f"[PREP] Strategy ready: {dst}")
    print(f"       entities_per_job={entities_per_job}, max_workers={max_workers}, sample_size={sample_size}")
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
        "execution_mode": runtime.get("execution_mode", ""),
    }


def run_single_experiment(
    experiment_id: str,
    phase: str,
    entities_per_job: int,
    max_workers: int,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> ExperimentResult:
    """运行单次实验"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result = ExperimentResult(
        experiment_id=experiment_id,
        phase=phase,
        entities_per_job=entities_per_job,
        max_workers=max_workers,
        timestamp=timestamp,
    )
    
    print(f"\n{'='*60}")
    print(f"  Experiment: {experiment_id}")
    print(f"  Phase: {phase}")
    print(f"  Config: entities={entities_per_job}, workers={max_workers}, stocks={sample_size}")
    print(f"{'='*60}")
    
    try:
        # 1. 准备策略
        _prepare_strategy(
            entities_per_job=entities_per_job, 
            max_workers=max_workers,
            sample_size=sample_size
        )
        
        # 2. 清理缓存
        _clear_cache()
        
        # 3. 运行枚举
        success, report_path = _run_enumeration()
        
        if not success or not report_path:
            result.success = False
            result.error_message = "Enumeration failed or no report generated"
            return result
        
        # 4. 提取指标
        metrics = _extract_metrics(report_path)
        
        # 更新 result
        for key, value in metrics.items():
            if hasattr(result, key):
                setattr(result, key, value)
        
        result.success = True
        result.raw_report_path = str(report_path)
        
        # 复制原始报告到 results 目录
        phase_dir = EXPERIMENTS_BASE / phase
        phase_dir.mkdir(parents=True, exist_ok=True)
        raw_copy = phase_dir / f"raw_{experiment_id}_{timestamp}.json"
        shutil.copy2(report_path, raw_copy)
        
        print(f"\n[RESULT] Wall={result.wall_clock_seconds:.3f}s, "
              f"Parallelism={result.parallelism_factor:.2f}x, "
              f"Memory Δ={result.parent_delta_mb:+.1f}MB")
        
    except Exception as e:
        result.success = False
        result.error_message = str(e)
        import traceback
        print(f"[ERROR] {e}\n{traceback.format_exc()}")
    
    finally:
        # 清理策略
        _cleanup_strategy()
    
    return result


def save_results_to_csv(results: List[ExperimentResult], phase: str) -> Path:
    """保存结果到 CSV"""
    phase_dir = EXPERIMENTS_BASE / phase
    phase_dir.mkdir(parents=True, exist_ok=True)
    
    csv_path = phase_dir / "sweep_data.csv"
    
    fieldnames = [
        "experiment_id", "timestamp", "phase",
        "entities_per_job", "max_workers",
        "success", "error_message",
        "wall_clock_seconds", "wall_clock_minutes",
        "parallelism_factor", "sum_worker_total_seconds",
        "avg_wall_clock_per_stock_ms",
        "total_stocks", "total_klines", "total_opportunities", "stocks_skipped",
        "parent_start_mb", "parent_end_mb", "parent_delta_mb", "avg_peak_per_stock_mb",
        "storage_load_calls", "storage_load_time_seconds", "file_writes",
        "db_engine", "cache_hit", "execution_mode",
        "raw_report_path",
    ]
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            row = asdict(r)
            writer.writerow(row)
    
    print(f"\n[SAVE] Results saved to {csv_path}")
    return csv_path


def generate_analysis_markdown(results: List[ExperimentResult], phase: str) -> Path:
    """生成分析报告 Markdown"""
    phase_dir = EXPERIMENTS_BASE / phase
    md_path = phase_dir / "analysis.md"
    
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    lines = [
        f"# Entity Per Job Experiment Report",
        "",
        f"> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> Phase: **{phase}**",
        "",
        "---",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Experiments | {len(results)} |",
        f"| Successful | {len(successful)} |",
        f"| Failed | {len(failed)} |",
        "",
    ]
    
    if successful:
        lines.extend([
            "## Performance Comparison",
            "",
            "| Config | Entities/Job | Workers | Wall Time (s) | Parallelism | Memory Δ (MB) | K-Lines | Opportunities |",
            "|--------|-------------|---------|----------------|-------------|---------------|---------|--------------|",
        ])
        
        # 按 entities_per_job 排序
        sorted_results = sorted(successful, key=lambda x: (x.entities_per_job, x.max_workers))
        
        for r in sorted_results:
            config_label = f"{r.entities_per_job}x{r.max_workers}"
            lines.append(
                f"| {config_label} | {r.entities_per_job} | {r.max_workers} | "
                f"**{r.wall_clock_seconds:.3f}** | {r.parallelism_factor:.2f}x | "
                f"{r.parent_delta_mb:+.1f} | {r.total_klines:,} | {r.total_opportunities} |"
            )
        
        # 找最优配置
        best = min(successful, key=lambda x: x.wall_clock_seconds)
        fastest_parallelism = max(successful, key=lambda x: x.parallelism_factor)
        lowest_memory = min(successful, key=lambda x: abs(x.parent_delta_mb))
        
        lines.extend([
            "",
            "### Key Findings",
            "",
            f"- **Fastest Configuration**: {best.entities_per_job}x{best.max_workers} "
            f"(Wall={best.wall_clock_seconds:.3f}s)",
            f"- **Best Parallelism**: {fastest_parallelism.entities_per_job}x{fastest_parallelism.max_workers} "
            f"(Parallelism={fastest_parallelism.parallelism_factor:.2f}x)",
            f"- **Lowest Memory Overhead**: {lowest_memory.entities_per_job}x{lowest_memory.max_workers} "
            f"(Δ={lowest_memory.parent_delta_mb:+.1f}MB)",
            "",
        ])
        
        # IO 分析
        if len(successful) > 1:
            lines.extend([
                "## IO & Memory Analysis",
                "",
                "| Entities/Job | Workers | Storage Calls | Load Time (s) | Avg Peak/Stock (MB) |",
                "|-------------|---------|---------------|---------------|--------------------|",
            ])
            
            for r in sorted_results:
                lines.append(
                    f"| {r.entities_per_job} | {r.max_workers} | "
                    f"{r.storage_load_calls} | {r.storage_load_time_seconds:.4f} | "
                    f"{r.avg_peak_per_stock_mb:.1f} |"
                )
            
            lines.append("")
    
    if failed:
        lines.extend([
            "## Failed Experiments",
            "",
            "| Experiment ID | Error |",
            "|---------------|-------|",
        ])
        for r in failed:
            lines.append(f"| {r.experiment_id} | {r.error_message[:100]} |")
        lines.append("")
    
    lines.extend([
        "---",
        "*Report generated by run_entity_sweep.py*",
        "",
    ])
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"[ANALYSIS] Report saved to {md_path}")
    return md_path


def run_phase1(sample_size: int = DEFAULT_SAMPLE_SIZE) -> List[ExperimentResult]:
    """实验组1：单进程 entities_per_job sweep"""
    print(f"\n{'#'*60}")
    print(f"# Phase 1: {PHASE1_CONFIG['description']}")
    print(f"# Sample Size: {sample_size} stocks")
    print(f"{'#'*60}")
    
    results = []
    
    for idx, epj in enumerate(PHASE1_CONFIG["entities_per_job_list"], 1):
        exp_id = f"P1_{idx:02d}_epj{epj}"
        
        result = run_single_experiment(
            experiment_id=exp_id,
            phase="phase1_single_process",
            entities_per_job=epj,
            max_workers=PHASE1_CONFIG["max_workers"],
            sample_size=sample_size,
        )
        
        results.append(result)
        
        # 短暂休息让系统稳定
        time.sleep(2)
    
    # 保存结果
    if results:
        save_results_to_csv(results, "phase1_single_process")
        generate_analysis_markdown(results, "phase1_single_process")
    
    return results


def run_phase2(sample_size: int = DEFAULT_SAMPLE_SIZE) -> List[ExperimentResult]:
    """实验组2：多进程组合矩阵"""
    print(f"\n{'#'*60}")
    print(f"# Phase 2: {PHASE2_CONFIG['description']}")
    print(f"# Sample Size: {sample_size} stocks")
    print(f"{'#'*60}")
    
    results = []
    
    for idx, (epj, workers) in enumerate(PHASE2_CONFIG["matrix"], 1):
        exp_id = f"P2_{idx:02d}_epj{epj}w{workers}"
        
        result = run_single_experiment(
            experiment_id=exp_id,
            phase="phase2_multi_process",
            entities_per_job=epj,
            max_workers=workers,
            sample_size=sample_size,
        )
        
        results.append(result)
        
        # 短暂休息
        time.sleep(2)
    
    # 保存结果
    if results:
        save_results_to_csv(results, "phase2_multi_process")
        generate_analysis_markdown(results, "phase2_multi_process")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Entity Per Job Sweep Experiments")
    parser.add_argument(
        "--phase",
        choices=["phase1", "phase2", "all"],
        default="all",
        help="Which phase(s) to run (default: all)",
    )
    parser.add_argument(
        "--stocks",
        type=int,
        default=DEFAULT_SAMPLE_SIZE,
        help=f"Number of stocks in sample pool (default: {DEFAULT_SAMPLE_SIZE})",
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("  Entity Per Job Sweep Experiment Suite")
    print(f"  Project Root: {PROJECT_ROOT}")
    print(f"  Output Base: {EXPERIMENTS_BASE}")
    print(f"  Sample Size: {args.stocks} stocks")
    print("=" * 60)
    
    # 创建输出目录
    EXPERIMENTS_BASE.mkdir(parents=True, exist_ok=True)
    
    all_results = []
    
    if args.phase in ["phase1", "all"]:
        results_p1 = run_phase1(sample_size=args.stocks)
        all_results.extend(results_p1)
    
    if args.phase in ["phase2", "all"]:
        results_p2 = run_phase2(sample_size=args.stocks)
        all_results.extend(results_p2)
    
    # 最终汇总
    print(f"\n{'='*60}")
    print("  Experiment Complete")
    print(f"{'='*60}")
    
    successful = [r for r in all_results if r.success]
    failed = [r for r in all_results if not r.success]
    
    print(f"  Total: {len(all_results)}")
    print(f"  Successful: {len(successful)}")
    print(f"  Failed: {len(failed)}")
    
    if failed:
        print("\n  Failed experiments:")
        for r in failed:
            print(f"    - {r.experiment_id}: {r.error_message[:80]}")
    
    if successful:
        print("\n  Top 5 Fastest:")
        sorted_by_time = sorted(successful, key=lambda x: x.wall_clock_seconds)[:5]
        for i, r in enumerate(sorted_by_time, 1):
            print(f"    {i}. {r.experiment_id}: {r.wall_clock_seconds:.3f}s "
                  f"({r.entities_per_job}x{r.max_workers}, P={r.parallelism_factor:.2f}x)")
    
    if len(failed) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
