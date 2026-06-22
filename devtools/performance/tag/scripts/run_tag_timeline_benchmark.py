#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Entity Timeline 模式 Tag 性能基准测试

目标：
  - 定义 entity_timeline 模式的性能基线
  - 测试不同 entities_per_job 配置下的表现
  - 收集详细的性能指标和 profile 数据

用法：
    # 运行默认配置测试
    python run_tag_timeline_benchmark.py

    # 使用更小的股票池（快速验证）
    python run_tag_timeline_benchmark.py --stock-limit 500

    # 自定义 entities_per_job
    python run_tag_timeline_benchmark.py --epj 10

输出：
  results/timeline/
  └── baseline.json              # 基准结果

日期: 2026-06-22
"""

from __future__ import annotations

import argparse
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
_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR
for _ in range(5):  # scripts/ → tag/ → performance/ → devtools/ → 项目根目录
    if (PROJECT_ROOT / "cli.py").exists():
        break
    PROJECT_ROOT = PROJECT_ROOT.parent

RESULTS_BASE = _SCRIPT_DIR / "results" / "timeline"
TEST_BASE_TAGS_DIR = _SCRIPT_DIR.parent / "test_base_tags" / "entity_timeline"
USERSPACE_TAGS_DIR = PROJECT_ROOT / "userspace" / "extensions" / "tags"
TEMP_SCENARIO_NAME = "bench_tag_timeline"
DEFAULT_STOCK_LIMIT = 5596  # 默认使用全量 A 股
DEFAULT_EPJ = 5  # 默认 entities_per_job


@dataclass
class TagBenchmarkResult:
    """单次 Tag 基准测试结果"""
    test_id: str
    timestamp: str

    # 配置
    scenario: str
    execution_mode: str = "entity_timeline"
    stock_limit: int = 0
    entities_per_job: int = 1
    max_workers: int = 1

    # 性能指标
    wall_clock_seconds: float = 0.0
    wall_clock_minutes: float = 0.0
    parallelism_factor: float = 0.0

    # 数据量
    total_entities: int = 0
    total_jobs: int = 0
    completed_jobs: int = 0
    failed_jobs: int = 0
    saved_tag_values: int = 0

    # Profile 数据（TagRunProfile）
    stage_sec: float = 0.0
    execute_sec: float = 0.0
    report_sec: float = 0.0
    save_batch_sec: float = 0.0
    stage_jobs: int = 0
    execute_jobs: int = 0
    report_jobs: int = 0
    pickle_bytes: int = 0
    payload_rows: int = 0

    # Runtime 元数据
    db_engine: str = ""

    # 状态
    success: bool = False
    error_message: str = ""
    raw_report_path: Optional[str] = None


def _resolve_python() -> str:
    """优先使用项目虚拟环境中的 Python"""
    venv_python = PROJECT_ROOT / "venv" / "bin" / "python3"
    if venv_python.exists():
        return str(venv_python)
    # 回退到系统 Python
    return sys.executable


def _clear_cache() -> None:
    """清理缓存保证冷启动"""
    cache_dirs = [
        PROJECT_ROOT / ".cache" / "duckdb",
        PROJECT_ROOT / ".cache" / "tag",
        PROJECT_ROOT / ".cache" / "strategy",
    ]
    for d in cache_dirs:
        if d.exists():
            for f in d.rglob("*"):
                if f.is_file():
                    f.unlink()
            print(f"[CACHE] Cleared {d}")


def _prepare_benchmark_scenario() -> str:
    """
    从 test_base_tags 复制基准场景到 userspace。
    测试时自动将频率改为 daily 以确保能执行计算。

    Returns:
        scenario_name: 复制后的场景名称（用于 --scenario 参数）
    """
    src = TEST_BASE_TAGS_DIR
    dst = USERSPACE_TAGS_DIR / TEMP_SCENARIO_NAME

    # 清理可能存在的旧临时场景
    if dst.exists():
        shutil.rmtree(dst)

    # 复制 base tag 场景
    shutil.copytree(src, dst)
    print(f"[PREP] Benchmark scenario ready: {dst}")
    print(f"       Source: {src}")

    # 修改 settings：将周频改为日频（测试用）
    settings_path = dst / "settings.py"
    if settings_path.exists():
        with open(settings_path, "r", encoding="utf-8") as f:
            content = f.read()
        # 替换 frequency 为 daily
        content = content.replace('"frequency": "weekly"', '"frequency": "daily"')
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[PREP] Modified settings: frequency -> daily (for testing)")

    return TEMP_SCENARIO_NAME


def _cleanup_benchmark_scenario() -> None:
    """清理临时基准场景"""
    dst = USERSPACE_TAGS_DIR / TEMP_SCENARIO_NAME
    if dst.exists():
        shutil.rmtree(dst)
        print(f"[CLEAN] Removed benchmark scenario: {dst}")


def _run_tag_scenario(
    scenario: str,
    *,
    stock_limit: Optional[int] = None,
    entities_per_job: int = DEFAULT_EPJ,
    execute_mode: str = "batch",
    enable_profile: bool = True,
    dry_run: bool = True,  # 默认使用 dry run 模式
) -> Tuple[bool, Optional[Path]]:
    """运行 tag 场景并返回是否成功和 report 路径"""
    python = _resolve_python()
    cli_path = PROJECT_ROOT / "cli.py"

    cmd = [
        python, str(cli_path), "tag",
        "--scenario", scenario,
    ]

    if stock_limit is not None:
        cmd.extend(["--stock-limit", str(stock_limit)])

    if entities_per_job != DEFAULT_EPJ:
        cmd.extend(["--entities-per-job", str(entities_per_job)])

    if execute_mode != "batch":
        cmd.extend(["--execute-mode", execute_mode])

    if enable_profile:
        cmd.append("--profile")

    # Dry run 模式：不写入数据库
    if dry_run:
        cmd.append("--dry-run")

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
        print(f"[ERROR] {result.stderr[-1000:] if result.stderr else 'Unknown error'}")
        return False, None

    # 打印 CLI 输出以便调试
    if result.stdout:
        print(f"[STDOUT] {result.stdout[-500:]}")
    if result.stderr:
        print(f"[STDERR] {result.stderr[-500:]}")

    # 查找 performance report
    scenario_path = PROJECT_ROOT / "userspace" / "extensions" / "tags" / scenario
    results_dir = scenario_path / "results" / "performance"

    if not results_dir.is_dir():
        print(f"[WARN] No results directory found: {results_dir}")
        return True, None

    # 找到最新的版本目录
    versions = sorted(
        [d for d in results_dir.iterdir() if d.is_dir() and d.name.isdigit()],
        key=lambda x: int(x.name),
        reverse=True,
    )

    for v in versions:
        report = v / "0_performance_report.json"
        if report.is_file():
            return True, report

    return True, None


def _extract_metrics(report_path: Path) -> Dict[str, Any]:
    """从 performance_report.json 提取关键指标"""
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    summary = report.get("summary", {})
    profile = report.get("profile") or {}
    config = report.get("configuration") or {}

    metrics = {
        "wall_clock_seconds": summary.get("wall_clock_seconds", 0) or 0,
        "wall_clock_minutes": summary.get("wall_clock_minutes", 0) or 0,
        "parallelism_factor": summary.get("parallelism_factor", 0) or 0,
        "total_entities": summary.get("total_entities", 0) or 0,
        "total_jobs": summary.get("total_jobs", 0) or 0,
        "completed_jobs": summary.get("completed_jobs", 0) or 0,
        "failed_jobs": summary.get("failed_jobs", 0) or 0,
        "saved_tag_values": summary.get("saved_tag_values", 0) or 0,
        "stage_sec": profile.get("stage_sec", 0) or 0,
        "execute_sec": profile.get("execute_sec", 0) or 0,
        "report_sec": profile.get("report_sec", 0) or 0,
        "save_batch_sec": profile.get("save_batch_sec", 0) or 0,
        "stage_jobs": profile.get("stage_jobs", 0) or 0,
        "execute_jobs": profile.get("execute_jobs", 0) or 0,
        "report_jobs": profile.get("report_jobs", 0) or 0,
        "pickle_bytes": profile.get("pickle_bytes", 0) or 0,
        "payload_rows": profile.get("payload_rows", 0) or 0,
        "db_engine": config.get("db_engine", ""),
    }

    return metrics


def run_benchmark(
    test_id: str,
    stock_limit: int = DEFAULT_STOCK_LIMIT,
    entities_per_job: int = DEFAULT_EPJ,
    dry_run: bool = True,  # 默认使用 dry run
) -> TagBenchmarkResult:
    """运行单次基准测试"""

    # 1. 准备基准场景（从 test_base_tags 复制到 userspace）
    scenario_name = _prepare_benchmark_scenario()

    result = TagBenchmarkResult(
        test_id=test_id,
        timestamp=datetime.now().isoformat(),
        scenario=scenario_name,
        execution_mode="entity_timeline",
        stock_limit=stock_limit,
        entities_per_job=entities_per_job,
    )

    try:
        # 2. 清缓存 (冷启动)
        _clear_cache()

        # 3. 运行 tag 场景
        success, report_path = _run_tag_scenario(
            scenario=scenario_name,
            stock_limit=stock_limit,
            entities_per_job=entities_per_job,
            enable_profile=True,
            dry_run=dry_run,
        )

        if not success:
            result.success = False
            result.error_message = "Tag execution failed"
            return result

        if report_path and report_path.exists():
            result.raw_report_path = str(report_path)

            # 3. 提取指标
            metrics = _extract_metrics(report_path)
            for key, value in metrics.items():
                if hasattr(result, key):
                    setattr(result, key, value)

            # 复制原始报告到 results 目录
            RESULTS_BASE.mkdir(parents=True, exist_ok=True)
            import shutil as _shutil
            _shutil.copy2(report_path, RESULTS_BASE / "raw_performance_report.json")
            print(f"[DEBUG] 原始报告已保存到: {RESULTS_BASE / 'raw_performance_report.json'}")

        result.success = True

        # 4. 计算衍生指标
        if result.total_entities > 0 and result.wall_clock_seconds > 0:
            result.parallelism_factor = (
                (result.stage_sec + result.execute_sec + result.report_sec) /
                result.wall_clock_seconds
                if (result.stage_sec + result.execute_sec + result.report_sec) > 0
                else 0
            )

    except Exception as e:
        result.success = False
        result.error_message = str(e)
        import traceback
        print(f"[ERROR] {e}\n{traceback.format_exc()}")

    finally:
        # 5. 清理临时基准场景
        _cleanup_benchmark_scenario()

    return result


def generate_analysis_md(result: TagBenchmarkResult, output_path: Path) -> None:
    """生成 Markdown 分析报告"""

    # 检查是否有有效数据
    has_data = result.wall_clock_seconds > 0 or result.total_entities > 0

    if not has_data:
        md_content = f"""# Entity Timeline Tag 性能基准报告

**测试 ID**: {result.test_id}
**时间**: {result.timestamp}
**场景**: {result.scenario}
**状态**: {'✅ 成功' if result.success else '❌ 失败'}

---

## ⚠️ 无性能数据

测试执行完成但未收集到性能数据。可能的原因：
1. Dry run 模式下未正确生成 performance report
2. CLI 执行失败或被中断
3. 结果目录未创建

**建议**:
- 检查 CLI 输出日志
- 尝试使用 `--no-dry-run` 参数运行
- 确认 tag 场景配置正确

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"\n[REPORT] 分析报告已保存（无数据）: {output_path}")
        return

    # 有数据时生成完整报告
    safe_div = lambda a, b: a / b if b > 0 else 0

    md_content = f"""# Entity Timeline Tag 性能基准报告

**测试 ID**: {result.test_id}
**时间**: {result.timestamp}
**场景**: {result.scenario}
**状态**: {'✅ 成功' if result.success else '❌ 失败'}

---

## 📊 测试配置

| 参数 | 值 |
|------|-----|
| **执行模式** | {result.execution_mode} |
| **场景** | {result.scenario} |
| **实体数量限制** | {result.stock_limit:,} |
| **Entities/Job** | {result.entities_per_job} |
| **数据库引擎** | {result.db_engine or 'Unknown'} |

---

## ⏱️ 性能指标

### 核心时间指标

| 指标 | 数值 | 单位 | 说明 |
|------|------|------|------|
| **Wall Clock Time** | {result.wall_clock_seconds:.2f} | 秒 | 总耗时 |
| **Wall Clock Time** | {result.wall_clock_minutes:.2f} | 分钟 | 总耗时 |
| **Parallelism Factor** | {result.parallelism_factor:.2f}x | 倍数 | 并行效率 |

### 吞吐量指标

| 指标 | 数值 | 说明 |
|------|------|------|
| **总实体数** | {result.total_entities:,} | 处理的实体数量 |
| **总任务数** | {result.total_jobs:,} | dispatch jobs |
| **完成任务数** | {result.completed_jobs:,} | 成功的任务 |
| **失败任务数** | {result.failed_jobs:,} | 失败的任务 |
| **写入 Tag 数** | {result.saved_tag_values:,} | 写入的标签值数量 |
| **实体/秒** | {safe_div(result.total_entities, result.wall_clock_seconds):.1f} | 实体处理速度 |
| **单实体耗时** | {safe_div(result.wall_clock_seconds * 1000, result.total_entities):.2f} ms | ms/实体 |

### Profile 细分（TagRunProfile）

| 阶段 | 耗时 (s) | 任务数 | 平均耗时 (ms) | 说明 |
|------|---------|--------|--------------|------|
| **Stage** | {result.stage_sec:.2f} | {result.stage_jobs} | {safe_div(result.stage_sec * 1000, result.stage_jobs):.1f} | 数据准备 |
| **Execute** | {result.execute_sec:.2f} | {result.execute_jobs} | {safe_div(result.execute_sec * 1000, result.execute_jobs):.1f} | 标签计算 |
| **Report** | {result.report_sec:.2f} | {result.report_jobs} | {safe_div(result.report_sec * 1000, result.report_jobs):.1f} | 结果保存 |
| **Save Batch** | {result.save_batch_sec:.2f} | - | - | 批量写入 DB |

### 时间占比分析

{'#### ✅ 有完整 Profile 数据' if result.stage_sec > 0 or result.execute_sec > 0 else '#### ⚠️ 无 Profile 数据'}
"""

    if result.stage_sec > 0 or result.execute_sec > 0:
        total_profile = result.stage_sec + result.execute_sec + result.report_sec
        if total_profile > 0:
            md_content += f"""
| 阶段 | 占比 | 判断 |
|------|------|------|
| **Stage** | {safe_div(result.stage_sec, total_profile) * 100:.1f}% | {'⚠️ 可能是瓶颈' if safe_div(result.stage_sec, total_profile) > 0.5 else '✅ 正常'} |
| **Execute** | {safe_div(result.execute_sec, total_profile) * 100:.1f}% | {'⚠️ 可能是瓶颈' if safe_div(result.execute_sec, total_profile) > 0.5 else '✅ 正常'} |
| **Report** | {safe_div(result.report_sec, total_profile) * 100:.1f}% | {'⚠️ 可能是瓶颈' if safe_div(result.report_sec, total_profile) > 0.3 else '✅ 正常'} |

**瓶颈判断**:
- 主导阶段: **{max([('Stage', result.stage_sec), ('Execute', result.execute_sec), ('Report', result.report_sec)], key=lambda x: x[1])[0]}**
- 建议: {"优化数据加载" if safe_div(result.stage_sec, total_profile) > 0.5 else "优化计算逻辑" if safe_div(result.execute_sec, total_profile) > 0.5 else "优化保存策略"}
"""
        else:
            md_content += "\n*需要重新运行测试以获取此数据*\n"
    else:
        md_content += "\n*需要重新运行测试以获取此数据*\n"

    md_content += f"""

## 📈 与 Strategy 性能测试对比

| 维度 | Tag (Entity Timeline) | Strategy (Stock-Based) | 差异分析 |
|------|----------------------|------------------------|----------|
| **执行模式** | 逐实体 timeline | 逐股回测 | 类似模式 |
| **Wall Time** | {result.wall_clock_seconds:.2f}s | ~27.66s (参考) | 待对比 |
| **并行度** | {result.parallelism_factor:.2f}x | ~1.33x (参考) | 待对比 |
| **适用场景** | 标签计算 | 策略回测 | 不同目的 |

---

## 🔍 结论与建议

### 性能评级

{"✅ 达标" if result.wall_clock_seconds < 60 else "⚠️ 需优化"} - Wall Time {'<' if result.wall_clock_seconds < 60 else '>'} 60秒 ({result.stock_limit:,} 实体)

### 关键发现

1. **数据处理阶段 (Stage)** 占比 {safe_div(result.stage_sec, (result.stage_sec + result.execute_sec + result.report_sec)) * 100:.1f}%
2. **计算阶段 (Execute)** 占比 {safe_div(result.execute_sec, (result.stage_sec + result.execute_sec + result.report_sec)) * 100:.1f}%
3. **保存阶段 (Report)** 占比 {safe_div(result.report_sec, (result.stage_sec + result.execute_sec + result.report_sec)) * 100:.1f}%

### 优化建议

- 如果 Stage 占比 >50%: 考虑优化数据源查询或增加缓存
- 如果 Execute 占比 >50%: 考虑优化 tag_worker.py 的 calculate_tag 逻辑
- 如果 Report 占比 >30%: 考虑增大 save_batch_size 或使用批量写入

---

*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*由 run_tag_timeline_benchmark.py 自动生成*
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\n[REPORT] 分析报告已保存: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Entity Timeline Tag Benchmark")
    parser.add_argument(
        "--stock-limit",
        type=int,
        default=DEFAULT_STOCK_LIMIT,
        help=f"实体数量限制 (default: {DEFAULT_STOCK_LIMIT})",
    )
    parser.add_argument(
        "--epj",
        type=int,
        default=DEFAULT_EPJ,
        help=f"Entities per job (default: {DEFAULT_EPJ})",
    )
    parser.add_argument(
        "--execute-mode",
        type=str,
        default="batch",
        choices=["queue", "batch", "elastic"],
        help="执行模式 (default: batch)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="禁用 dry run 模式（实际写入数据库）",
    )
    args = parser.parse_args()

    # Dry run 模式（默认启用）
    dry_run = not args.no_dry_run

    print("=" * 60)
    print("  Entity Timeline Tag 性能基准测试")
    print(f"  Project Root: {PROJECT_ROOT}")
    print(f"  Output Base: {RESULTS_BASE}")
    print(f"  Base Tag: entity_timeline (from test_base_tags)")
    print(f"  Stock Limit: {args.stock_limit}")
    print(f"  Entities/Job: {args.epj}")
    print(f"  Dry Run: {'✅ 启用（不写入数据库）' if dry_run else '❌ 禁用（将写入数据库）'}")
    print("=" * 60)

    # 创建输出目录
    RESULTS_BASE.mkdir(parents=True, exist_ok=True)

    # 运行基准测试
    test_id = f"timeline_baseline_{args.stock_limit}_epj{args.epj}"
    result = run_benchmark(
        test_id=test_id,
        stock_limit=args.stock_limit,
        entities_per_job=args.epj,
        dry_run=dry_run,
    )

    # 保存结果为 JSON
    baseline_path = RESULTS_BASE / "baseline.json"
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2, ensure_ascii=False)
    print(f"\n[SAVE] Baseline saved to {baseline_path}")

    # 生成 Markdown 报告
    report_path = RESULTS_BASE / "analysis.md"
    generate_analysis_md(result, report_path)

    # 打印摘要
    print(f"\n{'='*60}")
    print("  测试完成")
    print(f"{'='*60}")
    print(f"  状态: {'✅ 成功' if result.success else '❌ 失败'}")
    print(f"  Wall Time: {result.wall_clock_seconds:.2f}s ({result.wall_clock_minutes:.2f}min)")
    print(f"  实体数: {result.total_entities:,}")
    print(f"  任务数: {result.total_jobs:,} (成功: {result.completed_jobs:,}, 失败: {result.failed_jobs:,})")
    print(f"  写入 Tag: {result.saved_tag_values:,}")
    print(f"  并行度: {result.parallelism_factor:.2f}x")

    if not result.success:
        print(f"\n  错误: {result.error_message}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
