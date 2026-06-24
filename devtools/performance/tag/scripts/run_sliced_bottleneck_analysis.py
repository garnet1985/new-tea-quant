#!/usr/bin/env python3
"""
Sliced 模式详细瓶颈分析脚本

目标：精确测量每个阶段的耗时占比
- 初始化 & Plan 构建
- Reader（数据读取）
- 队列传输
- Compute（计算）
- 结果收集 & 写入

测试配置：50 entities, slice_open_days=50
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# 项目根目录
PROJECT_ROOT = Path("/Users/garnet/Desktop/new-tea-quant")
sys.path.insert(0, str(PROJECT_ROOT))

BASE_TAG_DIR = PROJECT_ROOT / "devtools" / "performance" / "tag" / "test_base_tags" / "calendar_sliced"
USERSPACE_TAGS = PROJECT_ROOT / "userspace" / "extensions" / "tags"
RESULTS_DIR = PROJECT_ROOT / "devtools" / "performance" / "tag" / "scripts" / "results" / "bottleneck_analysis"


def run_bottleneck_analysis(
    stock_limit: int = 50,
    slice_open_days: int = 50,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """运行详细的瓶颈分析。"""

    scenario_name = f"bench_bottleneck_{stock_limit}e_{slice_open_days}d"
    scenario_path = USERSPACE_TAGS / scenario_name

    # 准备测试场景
    if scenario_path.exists():
        shutil.rmtree(scenario_path)
    shutil.copytree(BASE_TAG_DIR, scenario_path)

    # 运行带 verbose 的 tag 命令，捕获详细日志
    cmd = [
        str(PROJECT_ROOT / "venv" / "bin" / "python3"),
        str(PROJECT_ROOT / "cli.py"),
        "tag",
        "--scenario", scenario_name,
        "--stock-limit", str(stock_limit),
        "--profile",
        "--verbose",  # 启用详细日志
    ]

    if dry_run:
        cmd.append("--dry-run")

    print(f"\n{'='*70}")
    print(f"  瓶颈分析: {stock_limit} entities × {slice_open_days} days/slice")
    print(f"{'='*70}")
    print(f"[RUN] {' '.join(cmd)}")

    # 记录总时间
    start_time = time.time()
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    total_wall_time = time.time() - start_time

    # 解析输出中的时间信息
    stdout_lines = result.stdout.split('\n')
    stderr_lines = result.stderr.split('\n')

    # 提取关键性能指标
    metrics = {
        "total_wall_seconds": round(total_wall_time, 3),
        "success": result.returncode == 0,
        "config": {
            "stock_limit": stock_limit,
            "slice_open_days": slice_open_days,
            "dry_run": dry_run,
        },
        "stages": {},
        "logs": {
            "stdout_tail": stdout_lines[-100:] if len(stdout_lines) > 100 else stdout_lines,
            "stderr_errors": [line for line in stderr_lines if 'ERROR' in line or 'Exception' in line],
        },
    }

    # 尝试读取性能报告
    report_path = scenario_path / "results" / "performance" / "1" / "0_performance_report.json"
    if report_path.exists():
        with open(report_path, 'r') as f:
            report_data = json.load(f)
            metrics["report_summary"] = report_data.get("summary", {})
            metrics["profile"] = report_data.get("profile", {})

    # 从日志中提取阶段信息
    stage_timings = extract_stage_timings(stdout_lines + stderr_lines)
    metrics["stage_timings"] = stage_timings

    # 清理
    if scenario_path.exists():
        shutil.rmtree(scenario_path)

    return metrics


def extract_stage_timings(log_lines: List[str]) -> Dict[str, Any]:
    """从日志中提取各阶段的耗时。"""

    timings = {}

    # 查找关键时间戳模式
    patterns = {
        "init_plan": [
            "plan slice_open_days=",
            "build_runtime_plan",
            "resolve_open_dates",
        ],
        "reader_start": [
            "reader_lane_main",
            "reader started",
            "reading slice",
        ],
        "compute_start": [
            "compute_lane_main",
            "compute started",
            "on_calendar_asof",
        ],
        "queue_transfer": [
            "payload_q.put",
            "payload_q.get",
            "relay transfer",
        ],
        "result_collect": [
            "finalize_all",
            "tag_values collected",
            "saved_tag_values",
        ],
    }

    for stage_name, keywords in patterns.items():
        matching_lines = []
        for line in log_lines:
            if any(kw in line.lower() for kw in keywords):
                matching_lines.append(line.strip())
        if matching_lines:
            timings[stage_name] = {
                "count": len(matching_lines),
                "samples": matching_lines[:5],  # 保留前5条样本
            }

    return timings


def analyze_profile_breakdown(profile: Dict[str, Any]) -> Dict[str, float]:
    """分析 profile 中的阶段占比。"""

    breakdown = {}

    stage_sec = profile.get("stage_sec", 0) or 0
    execute_sec = profile.get("execute_sec", 0) or 0
    report_sec = profile.get("report_sec", 0) or 0
    save_batch_sec = profile.get("save_batch_sec", 0) or 0
    wall_sec = profile.get("wall_sec", 0) or 0

    total = max(wall_sec, stage_sec + execute_sec + report_sec + save_batch_sec, 0.001)

    breakdown = {
        "Stage (IO/数据准备)": round(stage_sec, 3),
        "Execute (计算)": round(execute_sec, 3),
        "Report (结果保存)": round(report_sec, 3),
        "Save Batch (批量写入)": round(save_batch_sec, 3),
        "Wall Total (总耗时)": round(wall_sec, 3),
        "_percentages": {
            "Stage (%)": round(stage_sec / total * 100, 1),
            "Execute (%)": round(execute_sec / total * 100, 1),
            "Report (%)": round(report_sec / total * 100, 1),
            "Save Batch (%)": round(save_batch_sec / total * 100, 1),
        },
    }

    return breakdown


def generate_detailed_report(metrics: Dict[str, Any]) -> str:
    """生成详细的瓶颈分析报告。"""

    lines = []

    lines.append("# Sliced 模式瓶颈分析报告\n")
    lines.append(f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"**配置**: {metrics['config']['stock_limit']} entities × {metrics['config']['slice_open_days']} days/slice\n")
    lines.append(f"**状态**: {'✅ 成功' if metrics['success'] else '❌ 失败'}\n")

    # 总体指标
    lines.append("\n---\n")
    lines.append("## ⏱️ 总体性能\n")
    lines.append(f"\n| 指标 | 数值 |\n")
    lines.append("|------|------|\n")
    lines.append(f"| **Wall Time** | **{metrics['total_wall_seconds']}s** |\n")

    if "report_summary" in metrics:
        summary = metrics["report_summary"]
        lines.append(f"| Entities | {summary.get('total_entities', 'N/A')} |\n")
        lines.append(f"| Jobs | {summary.get('total_jobs', 'N/A')} |\n")
        lines.append(f"| Tag Values | {summary.get('saved_tag_values', 'N/A')} |\n")
        lines.append(f"| Parallelism Factor | {summary.get('parallelism_factor', 'N/A')}x |\n")

    # Profile 分解
    if "profile" in metrics and metrics["profile"]:
        lines.append("\n---\n")
        lines.append("## 📊 Profile 阶段分解\n")

        breakdown = analyze_profile_breakdown(metrics["profile"])

        lines.append("\n| 阶段 | 耗时 (s) | 占比 |\n")
        lines.append("|------|---------|------|\n")

        for stage_name, value in list(breakdown.items())[:-1]:  # 排除 _percentages
            pct = breakdown["_percentages"].get(f"{stage_name.split('(')[0].strip()} (%)", "N/A")
            bar = "█" * int(float(pct) / 2) if isinstance(pct, (int, float)) else ""
            lines.append(f"| {stage_name} | {value}s | {pct}% {bar} |\n")

        # 瓶颈识别
        lines.append("\n### 🔍 瓶颈识别\n")

        percentages = breakdown["_percentages"]
        max_stage = max(
            [(k.replace(' (%)', '').strip(), v) for k, v in percentages.items()],
            key=lambda x: x[1]
        )

        lines.append(f"\n**主要瓶颈**: **{max_stage[0]}** ({max_stage[1]}%)\n")

        if max_stage[1] > 70:
            lines.append("- ⚠️ 该阶段占用超过 70%，是明显瓶颈\n")
        elif max_stage[1] > 50:
            lines.append("- ⚡ 该阶段占用超过 50%，需要关注\n")
        else:
            lines.append("- ✅ 各阶段分布相对均衡\n")

        # 建议
        lines.append("\n### 💡 优化建议\n")

        if "Execute" in max_stage[0] and max_stage[1] > 50:
            lines.append("""
- **计算密集型场景**：
  - 优化 `on_calendar_asof()` 内部逻辑
  - 使用向量化操作（numpy/pandas）替代循环
  - 减少不必要的数据拷贝
  - 考虑缓存中间结果
""")

        elif "Stage" in max_stage[0] and max_stage[1] > 50:
            lines.append("""
- **IO 密集型场景**：
  - 增加 reader_workers 数量
  - 优化数据查询（添加索引、减少字段）
  - 使用连接池复用数据库连接
  - 考虑预加载热点数据
""")

        elif "Save" in max_stage[0] and max_stage[1] > 30:
            lines.append("""
- **写入瓶颈**：
  - 使用批量插入替代逐条插入
  - 增加 batch size
  - 考虑异步写入
  - 在 dry-run 模式下应接近 0%
""")

    # 日志样本
    if "stage_timings" in metrics and metrics["stage_timings"]:
        lines.append("\n---\n")
        lines.append("## 📝 关键日志样本\n")

        for stage_name, info in metrics["stage_timings"].items():
            lines.append(f"\n#### {stage_name}\n")
            lines.append(f"- 出现次数: {info['count']}\n")
            if info.get("samples"):
                lines.append("- 样本:\n")
                for sample in info["samples"][:3]:
                    lines.append(f"  - `{sample[:100]}`\n")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Sliced 模式瓶颈分析")
    parser.add_argument("--entities", type=int, default=50, help="实体数量")
    parser.add_argument("--slice-days", type=int, default=50, help="切片天数")
    parser.add_argument("--no-dry-run", action="store_true", help="禁用 dry run")
    args = parser.parse_args()

    dry_run = not args.no_dry_run

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # 运行分析
    metrics = run_bottleneck_analysis(
        stock_limit=args.entities,
        slice_open_days=args.slice_days,
        dry_run=dry_run,
    )

    # 生成报告
    report_content = generate_detailed_report(metrics)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = RESULTS_DIR / f"bottleneck_{args.entities}e_{args.slice_days}d_{timestamp}.md"

    with open(report_file, 'w') as f:
        f.write(report_content)

    # 保存原始数据
    data_file = RESULTS_DIR / f"bottleneck_{args.entities}e_{args.slice_days}d_{timestamp}.json"
    with open(data_file, 'w') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)

    print(f"\n{'='*70}")
    print(f"  分析完成")
    print(f"\n{report_content}")
    print(f"\n  报告保存: {report_file}")
    print(f"  数据保存: {data_file}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
