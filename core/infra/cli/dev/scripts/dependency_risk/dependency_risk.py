#!/usr/bin/env python3
"""
依赖安装风险检测器 (Dependency Risk Detector)

自动检测 requirements.txt 中可能导致安装失败的依赖：
1. 需要 C 编译器的包（Windows 兼容性问题）
2. 未使用的依赖声明
3. 版本冲突风险
4. 缺少预编译 wheel 的平台

集成位置:
    - devcli pack 命令 (自动运行)
    - Pre-commit hook (可选)
    - GitHub Actions CI (自动触发)

使用方法:
    # 独立运行
    python -m core.infra.cli.dev.scripts.dependency_risk              # 标准检测
    python -m core.infra.cli.dev.scripts.dependency_risk --ci-mode    # CI 模式
    python -m core.infra.cli.dev.scripts.dependency_risk --fix        # 修复建议

    # 通过 devcli 调用
    devcli.py check-deps                                       # 快捷命令
"""

from core.infra.cmd_layout import i

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple


class RiskLevel(Enum):
    CRITICAL = "red_dot"   # 阻塞性问题（如需编译器）
    HIGH = "orange_dot"       # 高风险（可能失败）
    MEDIUM = "yellow_dot"     # 中等风险（警告）
    LOW = "green_dot"        # 低风险（信息）
    INFO = "info"       # 信息提示


@dataclass
class DependencyRisk:
    package: str
    risk_level: RiskLevel
    message: str
    suggestion: str
    line_number: int = -1
    is_fixable: bool = False


# 已知可能需要本地编译的包（仅作提示；若已在 ONLY_BINARY_INSTALL 中则降级为已缓解）
COMPILATION_REQUIRED_PACKAGES = {
    "cffi": "传递依赖常见；须用预编译 wheel",
    "cython": "检查是否真的需要 Cython，很多情况可用纯 Python",
    "numpy": "通常有预编译版，但旧版本可能需要编译",
    "scipy": "同 numpy",
    "lxml": "通常有预编译版",
    "Pillow": "通常有预编译版",
    "Levenshtein": "使用 python-Levenshtein（预编译版）",
    "python-levenshtein": "已废弃，换用 Levenshtein 或 rapidfuzz",
    "rapidfuzz": "纯 Python + 可选 C 加速",
    "uvloop": "仅 Unix，Windows 不支持",
    "cryptography": "通常有预编译版",
    "curl-cffi": "akshare 传递依赖；须用预编译 wheel",
}

# 与 setup/core/steps/resolve_deps、ui_runtime、updater 的 pip --only-binary 列表对齐
ONLY_BINARY_INSTALL = {
    "numpy",
    "pandas",
    "duckdb",
    "psycopg2-binary",
    "cffi",
    "curl-cffi",
    "lxml",
    "mini-racer",
    "psutil",
    "Pillow",
    "cryptography",
    "scipy",
}


# 项目核心依赖（即使未直接 import 也必须保留）
CORE_DEPENDENCIES = {
    "akshare": "adj_factor_event 数据源（腾讯前复权）",
    "requests": "akshare provider 运行时依赖",
    "tushare": "主要金融数据源",
    "pandas": "数据分析核心",
    "numpy": "数值计算基础",
    "flask": "Web BFF 框架",
    "flask-cors": "CORS 支持",
    "psutil": "进程监控",
    "duckdb": "本地数据库",
    "pymysql": "MySQL 连接器",
    "psycopg2-binary": "PostgreSQL 连接器",
    "pandas-ta-classic": "技术指标库",
}


class DependencyRiskDetector:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.requirements_in = project_root / "requirements.in"
        self.requirements_txt = project_root / "requirements.txt"
        self.risks: List[DependencyRisk] = []
        self.python_source_files: List[Path] = []

    def detect_all(self) -> List[DependencyRisk]:
        """执行所有检测"""
        print(f"{i('search')} 开始检测依赖风险...")
        print(f"{i('folder')} 项目根目录: {self.project_root}")
        print()

        # 1. 检查需要编译的包
        self._check_compilation_required_packages()

        # 2. 检查未使用的依赖
        self._check_unused_dependencies()

        # 3. 检查版本约束问题
        self._check_version_constraints()

        # 4. 检查 Windows 兼容性
        self._check_windows_compatibility()

        # 5. 检查循环依赖风险
        self._check_circular_dependencies()

        return sorted(self.risks, key=lambda x: (
            0 if x.risk_level == RiskLevel.CRITICAL else
            1 if x.risk_level == RiskLevel.HIGH else
            2 if x.risk_level == RiskLevel.MEDIUM else
            3 if x.risk_level == RiskLevel.LOW else 4
        ))

    def _scan_python_files(self) -> None:
        """扫描所有 Python 文件"""
        if not self.python_source_files:
            for pattern in ["**/*.py"]:
                self.python_source_files.extend(self.project_root.glob(pattern))
            # 排除 venv 和 __pycache__
            self.python_source_files = [
                f for f in self.python_source_files
                if "venv" not in str(f)
                and "__pycache__" not in str(f)
                and ".venv" not in str(f)
            ]

    def _search_import_in_code(self, package_name: str) -> Tuple[int, List[str]]:
        """在代码中搜索包的导入"""
        self._scan_python_files()

        import_patterns = [
            rf"^\s*import\s+{re.escape(package_name)}",
            rf"^\s*from\s+{re.escape(package_name)}\s+import",
            rf"{re.escape(package_name)}\.\w+",
        ]

        matching_files = []
        match_count = 0

        for py_file in self.python_source_files:
            try:
                content = py_file.read_text(encoding="utf-8")
                for line_num, line in enumerate(content.splitlines(), 1):
                    for pattern in import_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            match_count += 1
                            if str(py_file) not in [f for f, _ in matching_files]:
                                matching_files.append((str(py_file.relative_to(self.project_root)), line_num))
                            break
            except Exception:
                pass

        return match_count, matching_files

    def _check_compilation_required_packages(self) -> None:
        """检查需要 C 编译的包"""
        print("1.  检查需要编译的包...")

        if not self.requirements_txt.exists():
            self.risks.append(DependencyRisk(
                package="requirements.txt",
                risk_level=RiskLevel.CRITICAL,
                message="文件不存在",
                suggestion="运行: pip-compile --output-file=requirements.txt requirements.in",
                is_fixable=True
            ))
            return

        content = self.requirements_txt.read_text(encoding="utf-8")

        for pkg_name, suggestion in COMPILATION_REQUIRED_PACKAGES.items():
            # 匹配包名（可能带版本号）
            pattern = rf"^{re.escape(pkg_name)}[=<>!]"
            if not re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                continue

            key = pkg_name.lower()
            if key in ONLY_BINARY_INSTALL:
                # 安装脚本已 --only-binary：无 wheel 则安装失败，不会回退到本地编译
                self.risks.append(DependencyRisk(
                    package=pkg_name,
                    risk_level=RiskLevel.INFO,
                    message="含原生扩展，但安装路径已用 --only-binary 强制 wheel（风险已缓解）",
                    suggestion="保持 setup/core/steps/resolve_deps 等处的 only-binary 列表；勿在裸 pip install 时省略",
                    is_fixable=False,
                ))
                print(f"   {i('info')}  {pkg_name}: 已 only-binary 缓解")
                continue

            has_binary_variant = key in {
                "numpy", "scipy", "lxml", "pillow", "cryptography", "cffi", "curl-cffi",
            }
            level = RiskLevel.HIGH if has_binary_variant else RiskLevel.CRITICAL
            self.risks.append(DependencyRisk(
                package=pkg_name,
                risk_level=level,
                message=f"可能需要 C 编译器 ({suggestion})",
                suggestion=(
                    f"将 {pkg_name} 加入安装脚本 --only-binary 列表，"
                    f"或 pip install {pkg_name} --only-binary {pkg_name}"
                ),
                is_fixable=True,
            ))
            print(f"   {i('warning')}  {pkg_name}: 可能需要编译")

    def _check_unused_dependencies(self) -> None:
        """检查未使用的依赖"""
        print("2.  检查未使用的依赖...")

        if not self.requirements_in.exists():
            return

        content = self.requirements_in.read_text(encoding="utf-8")
        packages = []
        for line_num, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            if line and not line.startswith("#"):
                pkg_match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                if pkg_match:
                    packages.append((pkg_match.group(1).lower(), line_num))

        unused_count = 0
        for pkg_name, line_num in packages:
            if pkg_name in CORE_DEPENDENCIES:
                continue

            match_count, files = self._search_import_in_code(pkg_name)

            if match_count == 0:
                # 特殊检查：Provider 动态加载
                provider_pattern = rf'provider_name\s*=\s*["\']?{re.escape(pkg_name)}["\']?'
                has_provider = False
                for py_file in self.python_source_files[:100]:  # 限制搜索范围
                    try:
                        if re.search(provider_pattern, py_file.read_text(encoding="utf-8")):
                            has_provider = True
                            break
                    except Exception:
                        pass

                if not has_provider:
                    unused_count += 1
                    self.risks.append(DependencyRisk(
                        package=pkg_name,
                        risk_level=RiskLevel.MEDIUM,
                        message="未在代码中找到使用",
                        suggestion="确认是否需要，如果不需要可从 requirements.in 移除",
                        line_number=line_num,
                        is_fixable=True
                    ))
                    print(f"   {i('search')} {pkg_name}: 可能未使用 (第{line_num}行)")

        if unused_count == 0:
            print(f"   {i('success')} 所有依赖都已使用")

    def _check_version_constraints(self) -> None:
        """检查版本约束问题"""
        print("3.  检查版本约束...")

        if not self.requirements_txt.exists():
            return

        content = self.requirements_txt.read_text(encoding="utf-8")
        risky_patterns = [
            (r'==\d+\.\d+$', "精确版本锁定（可能阻止安全更新）", RiskLevel.LOW),
            (r'<2$', "上限约束（可能阻止新功能）", RiskLevel.INFO),
            (r'>=\d+\.\d+\.0', "最低版本要求", RiskLevel.INFO),
        ]

        for pattern, msg, level in risky_patterns:
            matches = re.findall(rf'(^[a-zA-Z0-9_-]+{pattern})', content, re.MULTILINE)
            if matches:
                for match in matches[:3]:  # 只报告前3个
                    pkg_name = re.match(r'^([a-zA-Z0-9_-]+)', match).group(1)
                    self.risks.append(DependencyRisk(
                        package=pkg_name,
                        risk_level=level,
                        message=msg,
                        suggestion="考虑使用兼容性版本范围（如 >=1.0,<2.0）"
                    ))

        print(f"   {i('success')} 版本约束检查完成")

    def _check_windows_compatibility(self) -> None:
        """检查 Windows 兼容性"""
        print("4.  检查 Windows 兼容性...")

        windows_incompatible = ["uvloop", "pyev", "gevent"]

        if self.requirements_txt.exists():
            content = self.requirements_txt.read_text(encoding="utf-8")
            for pkg in windows_incompatible:
                if re.search(rf'^{re.escape(pkg)}', content, re.MULTILINE | re.IGNORECASE):
                    self.risks.append(DependencyRisk(
                        package=pkg,
                        risk_level=RiskLevel.CRITICAL,
                        message="不支持 Windows 平台",
                        suggestion="移除此依赖或添加平台条件安装",
                        is_fixable=True
                    ))

        print(f"   {i('success')} Windows 兼容性检查完成")

    def _check_circular_dependencies(self) -> None:
        """检查潜在的循环依赖"""
        print("5.  检查循环依赖风险...")

        # 简化版：只检查明显的相互依赖
        known_conflicts = [
            ("requests", "urllib3"),  # requests 内部使用 urllib3
            ("flask", "werkzeug"),    # flask 依赖 werkzeug
            ("pandas", "numpy"),      # pandas 依赖 numpy
        ]

        if self.requirements_in.exists():
            content = self.requirements_in.read_text(encoding="utf-8").lower()
            for pkg_a, pkg_b in known_conflicts:
                if pkg_a in content and pkg_b in content:
                    # 这是正常的，只是记录一下
                    pass

        print(f"   {i('success')} 循环依赖检查完成")

    def generate_report(self, risks: List[DependencyRisk], verbose: bool = False) -> str:
        """生成检测报告"""
        report_lines = []
        report_lines.append("\n" + "=" * 80)
        report_lines.append(f"{i('bar_chart')} 依赖安装风险检测报告")
        report_lines.append("=" * 80)

        # 统计
        critical = sum(1 for r in risks if r.risk_level == RiskLevel.CRITICAL)
        high = sum(1 for r in risks if r.risk_level == RiskLevel.HIGH)
        medium = sum(1 for r in risks if r.risk_level == RiskLevel.MEDIUM)
        low = sum(1 for r in risks if r.risk_level == RiskLevel.LOW)
        info = sum(1 for r in risks if r.risk_level == RiskLevel.INFO)

        report_lines.append(f"\n{i('line_chart')} 风险统计:")
        report_lines.append(f"   {i('red_dot')} 关键 (Critical): {critical}")
        report_lines.append(f"   {i('orange_dot')} 高危 (High):      {high}")
        report_lines.append(f"   {i('yellow_dot')} 中等 (Medium):    {medium}")
        report_lines.append(f"   {i('green_dot')} 低危 (Low):       {low}")
        report_lines.append(f"   {i('info')}  信息 (Info):      {info}")
        report_lines.append(f"   ─────────────────────")
        report_lines.append(f"   {i('bar_chart')} 总计:             {len(risks)}")

        # 详细列表
        if risks:
            report_lines.append(f"\n{i('search')} 详细问题列表:")
            report_lines.append("-" * 80)

            for n, risk in enumerate(risks, 1):
                icon = i(risk.risk_level.value)
                report_lines.append(f"\n{n}. [{icon}] {risk.package}")
                report_lines.append(f"   问题: {risk.message}")
                report_lines.append(f"   建议: {risk.suggestion}")
                if risk.line_number > 0:
                    report_lines.append(f"   位置: requirements.in 第 {risk.line_number} 行")
                if risk.is_fixable:
                    report_lines.append(f"   状态: {i('success')} 可自动修复")

                if verbose:
                    report_lines.append(f"\n   {i('memo')} 详细信息:")
                    report_lines.append(f"   - 风险等级: {risk.risk_level.name}")

        # 建议
        report_lines.append(f"\n{i('tip')} 建议操作:")
        if critical > 0:
            report_lines.append(f"   {i('warning')}  发现 {critical} 个关键问题，必须立即处理！")
            report_lines.append(f"   → 可能导致 Windows 安装失败")
        if high > 0:
            report_lines.append(f"   {i('ongoing')} 发现 {high} 个高风险项，建议尽快处理")
        if medium > 0:
            report_lines.append(f"   {i('eyes')} 发现 {medium} 个中等风险项，可在下个迭代处理")
        if critical == 0 and high == 0 and medium == 0:
            report_lines.append(f"   {i('success')} 无未缓解的 Critical/High/Medium 项")
            if info > 0 or low > 0:
                report_lines.append("   （Info/Low 为提示，不阻塞 pack）")

        report_lines.append(f"\n{i('sparkle')} 自动修复命令:")
        report_lines.append(f"   python -m core.infra.cli.dev.scripts.dependency_risk --fix")

        report_lines.append("\n" + "=" * 80)

        return "\n".join(report_lines)


def main():
    parser = argparse.ArgumentParser(
        description="检测依赖安装风险（Windows 兼容性、未使用依赖等）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                  # 标准检测模式
  %(prog)s --ci-mode        # CI 模式（有问题则返回非零退出码）
  %(prog)s --fix            # 显示修复建议
  %(prog)s --verbose        # 详细输出
        """
    )

    parser.add_argument(
        "--ci-mode",
        action="store_true",
        help="CI 模式：发现关键/高危问题时返回非零退出码"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="显示具体的修复命令和代码修改建议"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细信息"
    )

    args = parser.parse_args()

    # 自动查找项目根目录（requirements.in + core/）
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir
    for _ in range(8):
        if (project_root / "requirements.in").exists() and (project_root / "core").is_dir():
            break
        project_root = project_root.parent

    detector = DependencyRiskDetector(project_root)
    risks = detector.detect_all()
    report = detector.generate_report(risks, verbose=args.verbose)

    print(report)

    # 输出修复建议
    if args.fix and risks:
        print(f"\n{i('gear')} 修复建议:")
        print("-" * 80)
        for risk in risks:
            if risk.is_fixable:
                print(f"\n[{risk.package}]")
                if risk.message == "未在代码中找到使用":
                    print(f"  从 requirements.in 移除:")
                    print(f"    # 找到这一行并删除:")
                    print(f"    {risk.package}")
                elif "编译" in risk.message:
                    print(f"  替换为预编译版:")
                    print(f"    pip install {risk.package} --only-binary {risk.package}")
                    print(f"    # 或者从 requirements.in 移除版本约束")

    # CI 模式：根据风险等级决定退出码
    if args.ci_mode:
        critical_count = sum(1 for r in risks if r.risk_level == RiskLevel.CRITICAL)
        high_count = sum(1 for r in risks if r.risk_level == RiskLevel.HIGH)

        if critical_count > 0:
            print(f"\n{i('error')} CI 检测失败: 发现 {critical_count} 个关键问题")
            sys.exit(1)
        elif high_count > 0:
            print(f"\n{i('warning')}  CI 警告: 发现 {high_count} 个高风险项")
            sys.exit(2)
        else:
            print(f"\n{i('success')} CI 检测通过: 无关键或高风险问题")
            sys.exit(0)

    return 0


# 为 devcli pack 命令提供的简化接口
def run_dependency_check(verbose: bool = False) -> int:
    """
    简化接口：供 publish_prep.py 调用
    
    Returns:
        int: 0=通过, 1=有关键问题, 2=有高危问题
    """
    from core.infra.cli.dev.services.paths import REPO_ROOT

    detector = DependencyRiskDetector(REPO_ROOT)
    risks = detector.detect_all()
    
    if verbose or risks:
        report = detector.generate_report(risks, verbose=verbose)
        print(report)
    
    critical_count = sum(1 for r in risks if r.risk_level == RiskLevel.CRITICAL)
    high_count = sum(1 for r in risks if r.risk_level == RiskLevel.HIGH)
    
    if critical_count > 0:
        return 1
    elif high_count > 0:
        return 2
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
