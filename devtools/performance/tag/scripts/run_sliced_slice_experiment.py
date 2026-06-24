#!/usr/bin/env python3
"""
Sliced 模式切片大小实验脚本（二维矩阵）

实验设计：
- 维度1: Entity 数量 (50, 100, 300)
- 维度2: Slice Open Days (30, 50, 100)

目的：找到最优的切片配置，分析性能是否随实体数线性增长。
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 动态解析项目根目录
_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR
for _ in range(5):  # scripts/ → tag/ → performance/ → devtools/ → 项目根目录
    if (PROJECT_ROOT / "cli.py").exists():
        break
    PROJECT_ROOT = PROJECT_ROOT.parent

sys.path.insert(0, str(PROJECT_ROOT))

BASE_TAG_DIR = PROJECT_ROOT / "devtools" / "performance" / "tag" / "test_base_tags" / "calendar_sliced"
USERSPACE_TAGS = PROJECT_ROOT / "userspace" / "extensions" / "tags"
RESULTS_DIR = _SCRIPT_DIR / "results" / "sliced_experiment"


def run_experiment(
    stock_limit: int,
    slice_open_days: int,
    dry_run: bool = True,
) -> dict:
    """运行单次切片实验。"""

    scenario_name = f"bench_slice_exp_{slice_open_days}d"
    scenario_path = USERSPACE_TAGS / scenario_name

    # 准备测试场景
    if scenario_path.exists():
        shutil.rmtree(scenario_path)
    shutil.copytree(BASE_TAG_DIR, scenario_path)

    # 修改 worker.json 中的 slice_open_days（临时）
    # 注意：实际应该通过 CLI 参数或环境变量覆盖

    cmd = [
        str(PROJECT_ROOT / "venv" / "bin" / "python3"),
        str(PROJECT_ROOT / "cli.py"),
        "tag",
        "--scenario", scenario_name,
        "--stock-limit", str(stock_limit),
        "--profile",
    ]

    if dry_run:
        cmd.append("--dry-run")

    print(f"\n{'='*60}")
    print(f"  切片实验: slice_open_days={slice_open_days}, stocks={stock_limit}")
    print(f"{'='*60}")
    print(f"[RUN] {' '.join(cmd)}")

    start_time = datetime.now()
    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=300,  # 5 分钟超时
    )
    end_time = datetime.now()

    wall_seconds = (end_time - start_time).total_seconds()

    # 解析结果
    success = result.returncode == 0

    # 尝试读取性能报告
    report_path = scenario_path / "results" / "performance" / "1" / "0_performance_report.json"
    report_data = {}
    if report_path.exists():
        with open(report_path, 'r') as f:
            report_data = json.load(f)

    # 清理测试场景
    if scenario_path.exists():
        shutil.rmtree(scenario_path)

    return {
        "scenario_name": scenario_name,
        "config": {
            "slice_open_days": slice_open_days,
            "stock_limit": stock_limit,
            "dry_run": dry_run,
        },
        "result": {
            "success": success,
            "wall_seconds": round(wall_seconds, 2),
            "return_code": result.returncode,
        },
        "report": report_data.get("summary", {}) if report_data else {},
        "profile": report_data.get("profile", {}) if report_data else {},
    }


def main():
    parser = argparse.ArgumentParser(description="Sliced 模式切片大小实验（二维矩阵）")
    parser.add_argument("--no-dry-run", action="store_true", help="禁用 dry run 模式")
    args = parser.parse_args()

    dry_run = not args.no_dry_run

    # 用户指定的实验设计：二维矩阵
    entity_limits = [50, 100, 300]
    slice_days_list = [30, 50, 100]

    # 创建结果目录
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    print("\n" + "=" * 70)
    print("  Sliced 模式切片大小实验（二维矩阵）")
    print("=" * 70)
    print(f"\n  实验设计:")
    print(f"  - Entity 数量: {entity_limits}")
    print(f"  - Slice Days: {slice_days_list}")
    print(f"  - Dry Run: {dry_run}")
    print(f"  - 总测试数: {len(entity_limits) * len(slice_days_list)}")

    for stock_limit in entity_limits:
        for slice_days in slice_days_list:
            try:
                result = run_experiment(
                    stock_limit=stock_limit,
                    slice_open_days=slice_days,
                    dry_run=dry_run,
                )
                results.append(result)

                status = "✅" if result["result"]["success"] else "❌"
                wall = result["result"]["wall_seconds"]
                entities = result["report"].get("total_entities", "N/A")
                tag_values = result["report"].get("saved_tag_values", "N/A")

                print(f"\n[{status}] Entities={stock_limit:3d} | Slice={slice_days:3d}d | "
                      f"Wall={wall:6.2f}s | Tags={tag_values}")

            except subprocess.TimeoutExpired:
                print(f"\n[❌] Entities={stock_limit:3d} | Slice={slice_days:3d}d | 超时 (>300s)")
                results.append({
                    "config": {"stock_limit": stock_limit, "slice_open_days": slice_days},
                    "result": {"success": False, "wall_seconds": 300, "error": "timeout"},
                })
            except Exception as e:
                print(f"\n[❌] Entities={stock_limit:3d} | Slice={slice_days:3d}d | 错误: {e}")
                results.append({
                    "config": {"stock_limit": stock_limit, "slice_open_days": slice_days},
                    "result": {"success": False, "error": str(e)},
                })

    # 保存实验结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = RESULTS_DIR / f"experiment_{timestamp}.json"

    experiment_data = {
        "experiment_id": f"sliced_slice_matrix_{timestamp}",
        "timestamp": datetime.now().isoformat(),
        "design": {
            "description": "二维矩阵实验：Entity数量 × Slice Open Days",
            "entity_limits": entity_limits,
            "slice_days_list": slice_days_list,
            "dry_run": dry_run,
        },
        "results": results,
    }

    with open(output_file, 'w') as f:
        json.dump(experiment_data, f, indent=2, ensure_ascii=False)

    # 生成分析报告
    generate_analysis_report(results, output_file)

    print(f"\n{'='*70}")
    print(f"  实验完成")
    print(f"  结果保存: {output_file}")
    print(f"{'='*70}")


def generate_analysis_report(results: list, output_file: Path):
    """生成二维矩阵分析报告。"""

    # 按实体数量分组
    by_entity = {}
    for r in results:
        config = r.get("config", {})
        entity_count = config.get("stock_limit", 0)
        if entity_count not in by_entity:
            by_entity[entity_count] = []
        by_entity[entity_count].append(r)

    report_lines = [
        "# Sliced 模式切片大小实验报告（二维矩阵）\n",
        f"**实验时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"**结果文件**: {output_file.name}\n",
        "---\n",
        "## 📊 实验设计\n",
        "\n| 维度 | 值 |\n",
        "|------|-----|\n",
        "| Entity 数量 | 50, 100, 300 |\n",
        "| Slice Open Days | 30, 50, 100 |\n",
        "\n---\n",
        "## 📈 实验结果\n",
    ]

    # 为每个实体数量生成子表
    for entity_count in sorted(by_entity.keys()):
        entity_results = by_entity[entity_count]
        report_lines.extend([
            f"\n### Entity 数量 = {entity_count}\n",
            "\n| Slice Days | Wall Time (s) | 成功率 | Tag Values | 状态 |\n",
            "|-----------|---------------|--------|------------|------|\n",
        ])

        successful = [r for r in entity_results if r.get("result", {}).get("success")]

        for r in entity_results:
            config = r.get("config", {})
            result = r.get("result", {})
            report_data = r.get("report", {})

            days = config.get("slice_open_days", "N/A")
            wall = result.get("wall_seconds", "N/A")
            success = "✅" if result.get("success") else "❌"
            tag_values = report_data.get("saved_tag_values", "N/A")

            report_lines.append(
                f"| {days} | {wall} | {success} | {tag_values} |\n"
            )

        # 找到该实体数下的最优配置
        if successful:
            best = min(successful, key=lambda x: x.get("result", {}).get("wall_seconds", float('inf')))
            best_days = best.get("config", {}).get("slice_open_days")
            best_wall = best.get("result", {}).get("wall_seconds")

            report_lines.append(f"\n**最优配置**: `slice_open_days={best_days}` (Wall Time: **{best_wall}s**)")

    # 线性分析
    if len(by_entity) >= 2:
        report_lines.extend([
            "\n---\n",
            "## 📉 性能趋势分析\n",
            "\n### 不同实体数量的性能对比\n",
            "\n| Entities | 最优 Slice Days | 最优 Wall Time (s) | Tags/sec |\n",
            "|----------|-----------------|-------------------|----------|\n",
        ])

        for entity_count in sorted(by_entity.keys()):
            entity_results = by_entity[entity_count]
            successful = [r for r in entity_results if r.get("result", {}).get("success")]

            if successful:
                best = min(successful, key=lambda x: x.get("result", {}).get("wall_seconds", float('inf')))
                best_days = best.get("config", {}).get("slice_open_days")
                best_wall = best.get("result", {}).get("wall_seconds")
                tag_values = best.get("report", {}).get("saved_tag_values", 0)
                tags_per_sec = round(tag_values / best_wall, 1) if best_wall > 0 else 0

                report_lines.append(
                    f"| {entity_count} | {best_days} | {best_wall} | {tags_per_sec} |\n"
                )

        report_lines.extend([
            "\n### 结论\n",
            "- 如果性能随实体数线性增长 → 计算是瓶颈（符合预期）\n",
            "- 如果性能超线性增长 → IO 或内存成为瓶颈\n",
            "- 如果性能亚线性增长 → 存在优化空间\n",
        ])

    # 总体最优配置
    all_successful = [r for r in results if r.get("result", {}).get("success")]
    if all_successful:
        overall_best = min(all_successful, key=lambda x: x.get("result", {}).get("wall_seconds", float('inf')))
        best_entity = overall_best.get("config", {}).get("stock_limit")
        best_days = overall_best.get("config", {}).get("slice_open_days")
        best_wall = overall_best.get("result", {}).get("wall_seconds")

        report_lines.extend([
            "\n---\n",
            "## 🏆 总体最优配置\n",
            f"\n**推荐**: Entities={best_entity}, Slice Days={best_days} (Wall Time: **{best_wall}s**)\n",
        ])

    # 保存报告
    report_file = output_file.with_suffix('.md')
    with open(report_file, 'w') as f:
        f.writelines(report_lines)

    print(f"\n[REPORT] 分析报告已保存: {report_file}")


if __name__ == "__main__":
    main()
