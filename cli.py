#!/usr/bin/env python3
"""
股票分析应用主入口

使用示例：
    python cli.py                      # 默认: scan
    python cli.py scan                 # 扫描投资机会
    python cli.py simulate             # 运行模拟链路（price_factor + capital_allocation）
    python cli.py -d                   # 更新全部已启用数据源
    python cli.py -d sys_stock_klines  # 仅 renew 单个 data source（表名或 key）
    python cli.py -r stock_klines      # 同上（推荐写法）
    python cli.py renew stock_klines   # 同上
    python cli.py renew list           # 列出可 renew 的表名 / key
    python cli.py -r stock_klines -f   # 强制 refresh（从 default_start_date 重拉）
    python cli.py -rf gdp              # 等同 -r gdp -f
    python cli.py analysis             # 分析结果
    python cli.py tag                  # 执行所有标签场景
    python cli.py tag --scenario xxx   # 执行指定标签场景
    python cli.py enumerate            # 枚举投资机会（测试用）
    python cli.py price_factor         # 价格因子回放模拟（基于枚举输出结果）
    python cli.py capital_allocation   # 资金分配模拟（基于枚举输出结果，真实资金约束）
    
    # 新快捷命令（模块首字母 + 行为命令）：
    python cli.py -d                   # DataSource（默认 renew）
    python cli.py -dr                  # DataSource renew（等同 -d）
    python cli.py -t                   # Tag（默认 generating）
    python cli.py -tg                  # Tag generating（等同 -t）
    python cli.py -s                   # Strategy（默认 scan，等同 -sc）
    python cli.py -sc                  # Strategy scan
    python cli.py -se                  # Strategy enumerate
    python cli.py -sp                  # Strategy price factor simulate
    python cli.py -sa                  # Strategy capital allocation simulate
    python cli.py -sy                  # Strategy analysis
    python cli.py -u                   # 检查并应用 core 版本更新
    python cli.py -update              # 同上
    python cli.py -e example           # 导出策略交流包（userspace/example-strategy.zip）
    python cli.py -e tag:my_tag        # 仅导出单个 tag
    python cli.py -i ./demo-strategy.zip     # 导入（重名拒绝）
    python cli.py -i ./demo-strategy.zip --skip-existing  # 跳过已存在
    python cli.py -i ./demo-strategy.zip -f  # 覆盖已存在
    python cli.py -i ./demo-strategy.zip --dry-run  # 仅预览
    python cli.py -s -new my_strategy       # 从模板复制新建策略
    python cli.py -t -new demo/my_tag       # 从模板复制新建 Tag 场景
"""
import sys
import os
import argparse
import asyncio
import warnings
import logging
from typing import Optional

# ============================================================================
# 路径设置（必须在导入其他模块之前）
# ============================================================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def ensure_venv_for_cli() -> None:
    """
    若当前不在虚拟环境中，优先重启到项目 venv 解释器，避免缺少依赖（如 pandas）。
    可用 NTQ_SKIP_AUTO_VENV=1 关闭该行为。
    """
    raw = os.environ.get("NTQ_SKIP_AUTO_VENV", "").strip().lower()
    if raw in ("1", "true", "yes"):
        return
    if sys.prefix != sys.base_prefix:
        return

    repo_root = os.path.dirname(os.path.abspath(__file__))
    if os.name == "nt":
        vpy = os.path.join(repo_root, "venv", "Scripts", "python.exe")
    else:
        vpy = os.path.join(repo_root, "venv", "bin", "python")

    if os.path.isfile(vpy):
        os.execv(vpy, [vpy, os.path.abspath(__file__), *sys.argv[1:]])


ensure_venv_for_cli()


def _skip_auto_install_from_argv() -> bool:
    """与 ``-h`` / ``-v`` / ``-u`` 等无需拉起应用的参数对齐。"""
    raw = os.environ.get("NTQ_SKIP_AUTO_INSTALL", "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    argv = sys.argv[1:]
    if not argv:
        return False
    skip_flags = {
        "-h",
        "--help",
        "-v",
        "--version",
        "-u",
        "-update",
        "--update",
        # 策略包 import/export 仅读写 userspace 文件，不依赖 DB / 完整 install 流水线
        "-e",
        "-i",
    }
    if any(token in skip_flags for token in argv):
        return True
    return "-new" in argv or "--new" in argv


def ensure_app_installed_if_needed() -> None:
    """
    执行业务命令前：若 CLI 应用未安装，自动运行 ``install.py``（与 launcher 触发 UI 安装对称）。
    """
    if _skip_auto_install_from_argv():
        return

    try:
        from setup.install_runtime import needs_install
    except ModuleNotFoundError:
        # core 尚不可导入时，交给后续 import 块的错误提示
        return

    if not needs_install("cli"):
        return

    print("检测到应用尚未完成安装，正在运行 install.py …", flush=True)
    from setup.cli_runtime import ensure_cli_install_via_install_py

    code = ensure_cli_install_via_install_py()
    if code != 0:
        raise SystemExit(code)


ensure_app_installed_if_needed()

# ============================================================================
# 警告抑制（必须在导入第三方库之前）
# ============================================================================
def setup_warnings():
    """配置警告抑制"""
    warnings.filterwarnings('ignore', category=FutureWarning, module='tushare')
    warnings.filterwarnings('ignore', category=FutureWarning, message='.*fillna.*method.*')
    warnings.filterwarnings('ignore', category=FutureWarning, module='pandas')
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='pandas')
    warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')
    warnings.filterwarnings('ignore', category=DeprecationWarning, module='numpy')

setup_warnings()

logger = logging.getLogger(__name__)

# ============================================================================
# 导入应用模块
# ============================================================================
try:
    from core.modules.data_manager import DataManager
    from core.modules.data_source.data_source_manager import DataSourceManager
    from core.modules.tag import TagManager
    from core.infra.logging.logging_manager import LoggingManager
    from core.system import system_meta
except ModuleNotFoundError as e:
    # 常见：用户未运行 install.py / 未创建 venv，导致 pandas 等依赖缺失
    missing = getattr(e, "name", None) or str(e)
    sys.stderr.write(
        "\n".join(
            [
                f"❌ 缺少依赖包: {missing}",
                "",
                "建议：在仓库根目录先执行一次安装（会创建 venv/ 并安装 requirements.txt）：",
                "  python3 install.py",
                "  或：python3 cli.py -sp  （将自动尝试 install.py）",
                "",
                "如果你已手动管理虚拟环境，请激活对应 venv 后再运行：",
                "  pip install -r requirements.txt",
                "",
                "如需跳过自动 venv（不推荐），可设置：NTQ_SKIP_AUTO_VENV=1",
                "",
            ]
        )
        + "\n"
    )
    raise SystemExit(1) from e


# ============================================================================
# 应用主类
# ============================================================================
class App:
    """股票分析应用主类"""
    
    def __init__(self, is_verbose: bool = False):
        """
        初始化应用
        
        Args:
            is_verbose: 是否启用详细日志（已由全局 logging 控制，此参数仅作向后兼容）
        """
        self.is_verbose = is_verbose
        
        # 初始化核心组件
        self.data_manager = DataManager(is_verbose=self.is_verbose)
        self.db = self.data_manager.db  # 向后兼容
        self.data_source = DataSourceManager(is_verbose=self.is_verbose)

        # 延迟初始化的组件
        self.tag_manager = None
        self.strategy_manager = None

    # ========================================================================
    # 数据更新相关
    # ========================================================================

    async def renew_data(
        self,
        table_name: Optional[str] = None,
        *,
        force: bool = False,
    ):
        """
        更新数据（``DataSourceManager.renew``）。

        Args:
            table_name: 表名或 data source key；``None`` 表示全部已启用。
            force: 强制全量重拉（见 userspace/config/data.json）。
        """
        self.data_source.renew(table_name=table_name, force=force)

    # ========================================================================
    # 策略（StrategyManager 由 CommandExecutor 直接拉取）
    # ========================================================================

    def _ensure_strategy_manager(self):
        if self.strategy_manager is None:
            from core.modules.strategy import StrategyManager

            self.strategy_manager = StrategyManager(is_verbose=self.is_verbose)
        return self.strategy_manager

    # ========================================================================
    # 标签相关
    # ========================================================================

    def tag(self, scenario_name: str = None):
        """
        执行标签计算

        Args:
            scenario_name: 场景名称（可选，不提供则执行所有场景）
        """
        if self.tag_manager is None:
            self.tag_manager = TagManager(is_verbose=self.is_verbose)
        self.tag_manager.execute(scenario_name=scenario_name)

    # ========================================================================
    # 工具方法
    # ========================================================================
    
    def export_adj_factor_csv(
        self,
        base_date: str = None,
        *,
        start_date: str = None,
        end_date: str = None,
        file_path: str = None,
    ):
        """
        手动导出复权因子事件 CSV。

        Args:
            base_date: 未指定 ``file_path`` 时用于季度文件名（``adj_factor_events_YYYYQn.csv``）。
            start_date: 导出起始 ``event_date``（YYYYMMDD）；默认库内 MIN(event_date)。
            end_date: 导出结束日期；默认库内 MAX(event_date)。
            file_path: 输出路径；默认 ``csv_dir/adj_factor_events_{start}_{end}.csv``。
        """
        adj_model = self.data_manager.stock.kline._adj_factor_event
        resolved_start = (
            str(start_date).replace("-", "")[:8]
            if start_date
            else adj_model.get_min_event_date()
        )
        end = end_date or adj_model.get_max_event_date()
        if file_path:
            out = file_path
        elif base_date and not end_date and start_date is None:
            file_name = adj_model.get_current_quarter_csv_name(base_date=base_date)
            out = os.path.join(adj_model.csv_dir, file_name)
        else:
            out = os.path.join(
                adj_model.csv_dir,
                f"adj_factor_events_{resolved_start or 'earliest'}_{end or 'latest'}.csv",
            )
        logger.info("📤 导出复权因子事件 CSV: %s .. %s -> %s", resolved_start, end or "?", out)
        exported = adj_model.export_to_csv(
            file_path=out, start_date=start_date, end_date=end_date
        )
        logger.info(f"✅ 导出完成: {exported} 条 -> {out}")


# ============================================================================
# 命令行参数解析
# ============================================================================
def create_argument_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='📊 股票分析应用 - 数据更新、扫描、模拟、分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_get_help_epilog()
    )
    
    # 位置参数（主命令；与 -d 合用时第一个也可为表名，见 resolve_command）
    parser.add_argument(
        'command',
        nargs='?',
        help='命令名；或 ``-d <表名>`` 时写表名 / data source key（如 sys_stock_klines）',
    )
    parser.add_argument(
        'table_name',
        nargs='?',
        default='',
        help='renew 目标表（与 renew 命令合用，如 ``renew sys_stock_klines``）',
    )
    
    # 快捷 flag
    _add_shortcut_flags(parser)
    
    # 额外参数
    _add_extra_arguments(parser)
    
    return parser


def _add_shortcut_flags(parser):
    """添加快捷 flag"""
    # DataSource
    parser.add_argument('-d', dest='data_flag', action='store_true',
                       help='DataSource renew（全部）；表名用位置参数或 ``-r``')
    parser.add_argument('-dr', dest='data_renew_flag', action='store_true',
                       help='等同 -d')
    parser.add_argument(
        '-r',
        '--renew',
        dest='renew_arg',
        nargs='?',
        const='',
        default=None,
        metavar='SOURCE',
        help='Renew：无 SOURCE=全部；有 SOURCE=单个表名或 data source key（如 stock_klines）',
    )
    parser.add_argument(
        '-rf',
        dest='renew_force_arg',
        nargs='?',
        const='',
        default=None,
        metavar='SOURCE',
        help='强制 refresh：无 SOURCE=全部；-rf gdp=单个（等同 -r SOURCE -f）',
    )

    # Tag
    parser.add_argument('-t', dest='tag_flag', action='store_true',
                       help='Tag 模块（默认 generating）；与 -new 合用可从模板新建场景')
    parser.add_argument('-tg', dest='tag_generate_flag', action='store_true',
                       help='Tag generating（等同 -t）')

    # Strategy
    parser.add_argument('-s', dest='strategy_flag', action='store_true',
                       help='Strategy 模块（默认 scan，等同 -sc）；与 -new 合用可从模板新建策略')
    parser.add_argument('-sc', dest='strategy_scan_flag', action='store_true',
                       help='Strategy scan')
    parser.add_argument('-se', dest='strategy_enum_flag', action='store_true',
                       help='Strategy enumerate（写入 results/simulations/enum/{version}）')
    parser.add_argument('-sp', dest='strategy_price_flag', action='store_true',
                       help='Strategy price factor simulation（基于枚举输出）')
    parser.add_argument('-sa', dest='strategy_capital_flag', action='store_true',
                       help='Strategy capital allocation simulation（基于枚举输出）')
    parser.add_argument('-sy', dest='strategy_analysis_flag', action='store_true',
                       help='Strategy analysis（分析模拟结果）')

    parser.add_argument('-u', '-update', dest='update_flag', action='store_true',
                       help='检查远端 core 版本并在确认后执行应用升级')

    parser.add_argument(
        '-e',
        dest='export_strategy_arg',
        nargs='?',
        const='',
        default=None,
        metavar='STRATEGY',
        help='导出包：-e example（策略包）| -e tag:NAME | -e adapter:NAME | -e strategy:NAME（单实体）',
    )
    parser.add_argument(
        '-i',
        dest='import_package_arg',
        nargs='?',
        const='',
        default=None,
        metavar='PATH',
        help='导入包；默认重名拒绝；-f 覆盖；--skip-existing 跳过已有；--dry-run 仅预览',
    )


def _run_app_update() -> int:
    """``-u`` / ``-update``：探测版本并可选运行 userspace updater 流水线。"""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent
    updater_dir = None
    for candidate in (
        repo_root / "userspace" / "system" / "updater",
        repo_root / "setup" / "updater",
    ):
        if (candidate / "upgrade_entry.py").is_file():
            updater_dir = candidate
            break
    if updater_dir is None:
        sys.stderr.write(
            "未找到升级器（userspace/system/updater 或 setup/updater）。"
            "请先完成 init userspace 或从仓库安装 updater。\n"
        )
        return 1

    upd_path = str(updater_dir.resolve())
    if upd_path not in sys.path:
        sys.path.insert(0, upd_path)

    from upgrade_entry import run_interactive_upgrade  # noqa: E402

    assume_yes = os.environ.get("NTQ_UPDATE_ASSUME_YES", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    return run_interactive_upgrade(repo_root, assume_yes=assume_yes)


def _add_extra_arguments(parser):
    """添加额外参数"""
    parser.add_argument(
        '-new',
        dest='scaffold_new_arg',
        metavar='PATH',
        help='从模板复制新建：cli.py -s -new <路径> 建策略；cli.py -t -new <路径> 建 Tag',
    )
    parser.add_argument('--strategy', type=str,
                       help='指定策略名称（用于 scan/simulate/enumerate/价格与资金模拟）；'
                            '省略时：enumerate/-se/-sp/-sa 默认使用「唯一」is_enabled 的策略，'
                            '多个启用时取名称排序第一个并提示使用本参数')
    parser.add_argument('--session', type=str,
                       help='指定session ID（用于 analysis）')
    parser.add_argument('--scenario', type=str,
                       help='指定场景名称（用于 tag）')
    parser.add_argument('--stocks', type=int, default=None,
                       help='测试股票数量（用于 enumerate，如果不提供则从 settings 读取）')
    parser.add_argument(
        '-f',
        '--force',
        '--force-refresh',
        dest='force_flag',
        action='store_true',
        help='renew/-r/-d：强制 refresh（default_start_date 起全量重拉，跳过日缓存）；'
             'scan：demo；enumerate(-se)：跳过 DbCache；'
             'import(-i)：覆盖已存在的 strategy/tag/adapter 目录',
    )
    parser.add_argument('--base-date', type=str,
                       help='基准日期（YYYYMMDD 或 YYYY-MM-DD，用于 export_adj_factor_csv）')
    parser.add_argument('-v', '--version', action='store_true',
                       help='显示当前 core 版本信息并退出')
    parser.add_argument(
        '-o',
        '--output',
        dest='export_output_arg',
        type=str,
        default=None,
        metavar='PATH',
        help='导出输出路径（仅与 -e 合用）',
    )
    parser.add_argument(
        '--skip-existing',
        dest='import_skip_existing_flag',
        action='store_true',
        help='导入时跳过 userspace 中已存在的 strategy/tag/adapter 目录（仅 -i）',
    )
    parser.add_argument(
        '--dry-run',
        dest='import_dry_run_flag',
        action='store_true',
        help='导入预览，不写入磁盘（仅 -i）',
    )
    parser.add_argument('-V', '--verbose', action='store_true',
                       help='详细输出模式')


def _get_help_epilog() -> str:
    """获取帮助信息的 epilog"""
    return '''
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
命令说明:
  scan                 扫描投资机会（根据策略筛选当前符合条件的股票）
  simulate             上层模拟链路（依赖枚举输出）：price_factor + capital_allocation
  simulate_price       价格因子回放模拟（基于枚举输出机会结果）
  simulate_allocation  资金分配模拟（基于枚举输出机会结果，真实资金约束）
  renew [SOURCE]       更新数据；省略则全部；``renew list`` 列出可选 SOURCE
  -r [SOURCE]          同上（推荐：``-r stock_klines`` 只跑一个 data source）
  -d                   更新全部已启用 data source（表名请用 ``-r`` 或 ``renew``）
  -f                   与 renew/-r 合用：强制 refresh 单表或全部
  -rf [SOURCE]         等同 ``-r [SOURCE] -f``（推荐写法语义）
  analysis             分析结果（分析模拟回测的结果）
  tag                  执行标签计算（计算并存储所有或指定场景的标签）
  enumerate            枚举投资机会（测试用，枚举所有可能的机会）
  price_factor         simulate_price 的兼容别名
  capital_allocation   simulate_allocation 的兼容别名
  export_adj_factor_csv 手动导出复权因子事件季度 CSV

快捷缩写:
  -d           DataSource（默认 renew）
  -dr          DataSource renew
  -t           Tag（默认 generating）
  -tg          Tag generating
  -s           Strategy（默认 scan）
  -sc          Strategy scan
  -se          Strategy enumerate
  -sp          Strategy price factor simulation
  -sa          Strategy capital allocation simulation
  -sy          Strategy analysis
  -u, -update  检查 core 远端版本并在确认后升级
  -e STRATEGY  导出策略交流包（zip）
  -i PATH      导入策略交流包（重名拒绝；-f 覆盖）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
使用示例:

  单一命令:
    %(prog)s                      默认运行 scan
    %(prog)s scan                 扫描投资机会
    %(prog)s simulate             上层模拟链路（price_factor + capital_allocation）
    %(prog)s simulate_price       价格因子模拟
    %(prog)s simulate_allocation  资金分配模拟
    %(prog)s renew                更新数据
    %(prog)s analysis             分析结果
    %(prog)s tag                  执行所有标签场景
    %(prog)s tag --scenario xxx   执行指定标签场景

  快捷方式:
    %(prog)s -d                   更新全部 data source
    %(prog)s -r stock_klines      仅更新单个 data source
    %(prog)s -r gdp -f            强制 refresh 单个 data source
    %(prog)s -rf stock_klines     同上（-r + -f）
    %(prog)s renew list           列出可 renew 的表名 / key
    %(prog)s -t                   Tag generating
    %(prog)s -s                   Strategy scan
    %(prog)s -se                  Strategy enumerate
    %(prog)s -se -f               Strategy enumerate（强制刷新，跳过缓存复用）
    %(prog)s -sp                  Strategy price factor simulation
    %(prog)s -sp -f               Strategy price factor（跳过指纹读缓存，强制重算）
    %(prog)s -sa                  Strategy capital allocation simulation
    %(prog)s -sy                  Strategy analysis
    %(prog)s -u                   检查并应用 core 版本更新
    %(prog)s -s -new my_strategy    从模板复制新建策略
    %(prog)s -t -new demo/my_tag    从模板复制新建 Tag 场景
    %(prog)s -e example           导出策略包 userspace/example-strategy.zip
    %(prog)s -e tag:my_tag        仅导出 tag 目录
    %(prog)s -i ./pkg-strategy.zip        导入策略包
    %(prog)s -i ./pkg-strategy.zip --skip-existing
    %(prog)s -i ./pkg-strategy.zip -f     导入并覆盖重名目录
    %(prog)s -i ./pkg-strategy.zip --dry-run

  额外参数:
    %(prog)s simulate --strategy example    只运行指定策略
    %(prog)s analysis --session xxx         分析指定session
    %(prog)s tag --scenario xxx             执行指定标签场景
    %(prog)s price_factor --strategy xx     使用 PriceFactorFlow 对指定策略做因子回放
    %(prog)s -se -V                         详细输出模式

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    '''


_VALID_CLI_COMMANDS = frozenset({
    'scan', 'simulate', 'simulate_price', 'simulate_allocation',
    'renew', 'analysis', 'tag', 'enumerate', 'price_factor', 'capital_allocation',
    'export_adj_factor_csv',
})


def _normalize_cli_flags(args) -> None:
    """合并互斥/等价 flag（在 resolve_command 之前调用）。"""
    renew_force_arg = getattr(args, "renew_force_arg", None)
    if renew_force_arg is None:
        return

    args.force_flag = True
    if getattr(args, "renew_arg", None) is not None:
        logger.error("❌ 不能同时使用 -r 与 -rf")
        sys.exit(1)
    args.renew_arg = renew_force_arg


def resolve_command(args) -> str:
    """
    解析本次运行要执行的命令
    
    Args:
        args: 解析后的命令行参数
    
    Returns:
        str: 要执行的命令名称
    
    Raises:
        SystemExit: 如果命令冲突或无效
    """
    # 从位置参数获取命令
    cmd_from_positional = None
    if args.command:
        aliases = {
            "price_factor": "simulate_price",
            "capital_allocation": "simulate_allocation",
        }
        normalized = aliases.get(args.command, args.command)
        if normalized not in _VALID_CLI_COMMANDS:
            if (
                args.data_flag
                or args.data_renew_flag
                or getattr(args, "renew_arg", None) is not None
            ):
                if str(getattr(args, "table_name", "") or "").strip():
                    logger.error("❌ 不能同时指定两个表名（command 与 table_name）")
                    sys.exit(1)
                if getattr(args, "renew_table_name", ""):
                    logger.error("❌ 不能同时用 -r 与位置参数指定两个 SOURCE")
                    sys.exit(1)
                args.renew_table_name = str(args.command).strip()
            else:
                logger.error(f"❌ 无效的命令: {args.command}")
                logger.info(f"有效命令: {', '.join(sorted(_VALID_CLI_COMMANDS))}")
                sys.exit(1)
        else:
            cmd_from_positional = normalized
    
    # 从快捷 flag 获取命令
    flag_to_command = {
        # DataSource
        'data_flag': 'renew',
        'data_renew_flag': 'renew',

        # Tag
        'tag_flag': 'tag',
        'tag_generate_flag': 'tag',

        # Strategy
        'strategy_flag': 'scan',
        'strategy_scan_flag': 'scan',
        'strategy_enum_flag': 'enumerate',
        'strategy_price_flag': 'simulate_price',
        'strategy_capital_flag': 'simulate_allocation',
        'strategy_analysis_flag': 'analysis',
    }
    
    flags = [flag_to_command[k] for k, v in flag_to_command.items() if getattr(args, k, False)]
    if getattr(args, "renew_arg", None) is not None:
        flags.append("renew")

    # 验证命令一致性
    if cmd_from_positional and flags and cmd_from_positional not in flags:
        logger.error("❌ 命令冲突：位置参数和快捷 flag 指定了不同的命令")
        logger.info("请只使用一种方式指定命令，例如：`cli.py renew` 或 `cli.py -d`")
        sys.exit(1)
    
    if not cmd_from_positional and len(set(flags)) > 1:
        logger.error("❌ 命令冲突：同时指定了多个快捷命令（请每次只用一个快捷参数）")
        logger.info("每次运行只能执行一个命令，请保留一个 flag 即可")
        sys.exit(1)
    
    # 返回命令（优先位置参数，其次 flag，最后默认值）
    if cmd_from_positional:
        return cmd_from_positional
    if flags:
        return flags[0]
    
    # 默认：scan
    return 'scan'


def attach_renew_cli_context(args, command: str) -> None:
    """解析 renew 的 SOURCE（表名 / data source key）与 -f（仅 command == renew 时生效）。"""
    if command != 'renew':
        args.renew_table_name = ''
        args.renew_force = False
        return

    args.renew_force = bool(getattr(args, 'force_flag', False))

    renew_arg = getattr(args, 'renew_arg', None)
    if renew_arg is not None:
        source = str(renew_arg).strip()
        if source:
            if getattr(args, 'renew_table_name', ''):
                logger.error("❌ 不能同时用 -r 与其它方式指定两个 SOURCE")
                sys.exit(1)
            args.renew_table_name = source
        return

    if getattr(args, 'renew_table_name', ''):
        return

    args.renew_table_name = str(getattr(args, 'table_name', '') or '').strip()


def _resolve_package_cli(args, parser: argparse.ArgumentParser) -> Optional[int]:
    """
    Handle ``-e`` / ``-i`` before normal command dispatch.

    Returns exit code when handled, else ``None``.
    """
    export_arg = getattr(args, "export_strategy_arg", None)
    import_arg = getattr(args, "import_package_arg", None)
    if export_arg is not None and import_arg is not None:
        parser.error("不能同时使用 -e 与 -i")

    if export_arg is not None:
        name = str(export_arg).strip()
        if not name:
            parser.error("-e 需要策略名称（例: cli.py -e example）")
        if args.command or _package_cli_has_other_flags(args):
            parser.error("策略包导出 (-e) 不能与其它命令或模块快捷 flag 合用")
        from core.modules.strategy.launcher.package_cli import run_export

        LoggingManager.setup_logging()
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        out = getattr(args, "export_output_arg", None)
        output_path = str(out).strip() if out else None
        return run_export(name, output_path=output_path or None)

    if import_arg is not None:
        path = str(import_arg).strip()
        if not path:
            parser.error("-i 需要包路径（例: cli.py -i ./demo-strategy.zip）")
        if args.command or _package_cli_has_other_flags(args):
            parser.error("策略包导入 (-i) 不能与其它命令或模块快捷 flag 合用")
        if getattr(args, "export_output_arg", None):
            parser.error("-o/--output 仅能与 -e 合用")
        from core.modules.strategy.launcher.package_cli import run_strategy_bundle_import

        LoggingManager.setup_logging()
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        return run_strategy_bundle_import(
            path,
            force=bool(getattr(args, "force_flag", False)),
            skip_existing=bool(getattr(args, "import_skip_existing_flag", False)),
            dry_run=bool(getattr(args, "import_dry_run_flag", False)),
        )

    return None


def _resolve_scaffold_cli(args, parser: argparse.ArgumentParser) -> Optional[int]:
    """
    Handle ``-s -new PATH`` / ``-t -new PATH`` before normal command dispatch.

    Returns exit code when handled, else ``None``.
    """
    raw = getattr(args, "scaffold_new_arg", None)
    if raw is None:
        return None

    path = str(raw).strip()
    if not path:
        parser.error("-new 需要目标路径（例: cli.py -s -new my_strategy）")

    tag_selected = bool(args.tag_flag or args.tag_generate_flag)
    strategy_selected = bool(args.strategy_flag)
    strategy_sub = bool(
        args.strategy_scan_flag
        or args.strategy_enum_flag
        or args.strategy_price_flag
        or args.strategy_capital_flag
        or args.strategy_analysis_flag
    )

    if tag_selected and (strategy_selected or strategy_sub):
        parser.error("-new 不能同时用于 -t 与 -s")
    if strategy_sub:
        parser.error("新建策略请使用 cli.py -s -new <路径>，勿与 -sc/-se/-sp/-sa/-sy 合用")
    if not tag_selected and not strategy_selected:
        parser.error("新建须指定 -s -new <路径> 或 -t -new <路径>")
    if args.command:
        parser.error("-new 不能与其它位置命令合用")
    if getattr(args, "export_strategy_arg", None) is not None:
        parser.error("-new 不能与 -e 合用")
    if getattr(args, "import_package_arg", None) is not None:
        parser.error("-new 不能与 -i 合用")
    if getattr(args, "update_flag", False):
        parser.error("-new 不能与 -u 合用")
    if (
        args.data_flag
        or args.data_renew_flag
        or getattr(args, "renew_arg", None) is not None
        or getattr(args, "renew_force_arg", None) is not None
    ):
        parser.error("-new 不能与 -d/-r 等 data renew 命令合用")

    from core.infra.userspace.scaffold import ScaffoldError, scaffold_strategy, scaffold_tag

    LoggingManager.setup_logging()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        if tag_selected:
            result = scaffold_tag(path)
            kind_label = "Tag 场景"
        else:
            result = scaffold_strategy(path)
            kind_label = "策略"
        logger.info("✅ 已新建 %s: %s", kind_label, result.key)
        logger.info("   目录: %s", result.dest)
        logger.info("   请编辑 settings.py 与 worker，然后运行回测或打标。")
        return 0
    except ScaffoldError as exc:
        logger.error("❌ %s", exc)
        return 1


def _package_cli_has_other_flags(args) -> bool:
    """True when argv includes module shortcut flags besides optional -f/-V."""
    flag_names = (
        "data_flag",
        "data_renew_flag",
        "tag_flag",
        "tag_generate_flag",
        "strategy_flag",
        "strategy_scan_flag",
        "strategy_enum_flag",
        "strategy_price_flag",
        "strategy_capital_flag",
        "strategy_analysis_flag",
        "update_flag",
    )
    if any(getattr(args, name, False) for name in flag_names):
        return True
    if getattr(args, "renew_arg", None) is not None:
        return True
    if getattr(args, "renew_force_arg", None) is not None:
        return True
    return False


def _cli_strategy_arg(raw: object) -> Optional[str]:
    """``--strategy``：空串视为未传（``None``）。"""
    if raw is None:
        return None
    t = str(raw).strip()
    return t or None


# ============================================================================
# 命令执行器
# ============================================================================
class CommandExecutor:
    """命令执行器"""
    
    def __init__(self, app: App):
        """
        初始化命令执行器
        
        Args:
            app: 应用实例
        """
        self.app = app
        self.command_handlers = self._build_command_handlers()
    
    def _build_command_handlers(self) -> dict:
        """构建命令处理器映射"""
        return {
            'renew': self._handle_renew,
            'scan': self._handle_scan,
            'simulate': self._handle_simulate,
            'simulate_price': self._handle_simulate_price,
            'simulate_allocation': self._handle_simulate_allocation,
            'analysis': self._handle_analysis,
            'tag': self._handle_tag,
            'enumerate': self._handle_enumerate,
            'price_factor': self._handle_simulate_price,
            'capital_allocation': self._handle_simulate_allocation,
            'export_adj_factor_csv': self._handle_export_adj_factor_csv,
        }
    
    def execute(self, command: str, args):
        """
        执行命令
        
        Args:
            command: 命令名称
            args: 命令行参数
        """
        handler = self.command_handlers.get(command)
        if not handler:
            logger.error(f"❌ 未知命令: {command}")
            sys.exit(1)
        
        handler(args)
    
    def _handle_renew(self, args):
        """处理 renew / -d / -r（单 data source 或全部；``-f`` 为强制 refresh）。"""
        table_name = str(getattr(args, "renew_table_name", "") or "").strip() or None
        force = bool(getattr(args, "renew_force", False))

        if table_name and table_name.lower() == "list":
            from core.modules.data_source.data_source_manager import DataSourceManager

            logger.info("%s", DataSourceManager.format_renew_targets_help())
            return

        if table_name:
            logger.info(
                "🔄 更新数据: %s%s",
                table_name,
                " [force refresh]" if force else "",
            )
        else:
            logger.info("🔄 更新全部已启用数据源%s", " [force]" if force else "")
        try:
            asyncio.run(self.app.renew_data(table_name=table_name, force=force))
        except ValueError as e:
            logger.error("❌ %s", e)
            sys.exit(1)
    
    def _handle_scan(self, args):
        """处理 scan 命令"""
        logger.info("🔍 扫描投资机会...")
        mgr = self.app._ensure_strategy_manager()
        mgr.scan(
            strategy_name=_cli_strategy_arg(getattr(args, "strategy", None)),
            demo=bool(getattr(args, "force_flag", False)),
        )

    def _handle_simulate(self, args):
        """
        处理 simulate 命令（上层模拟链路）：
        - price_factor → capital_allocation
        依赖枚举输出；若枚举输出不存在，底层模拟器会按既有逻辑自行提示/触发枚举。
        """
        print("🎮 模拟链路 · PriceFactor → CapitalAllocation …")
        mgr = self.app._ensure_strategy_manager()
        mgr.simulate(
            "full",
            strategy_name=_cli_strategy_arg(getattr(args, "strategy", None)),
            force_refresh=bool(getattr(args, "force_flag", False)),
        )

    def _handle_analysis(self, args):
        """处理 analysis 命令"""
        logger.info("📊 分析模拟结果...")
        self.app._ensure_strategy_manager().analyze_simulation_outputs(session_id=args.session)

    def _handle_tag(self, args):
        """处理 tag 命令"""
        logger.info("🏷️  执行标签计算...")
        self.app.tag(scenario_name=args.scenario)

    def _handle_enumerate(self, args):
        """处理 enumerate 命令"""
        print("🔢 枚举投资机会…")
        mgr = self.app._ensure_strategy_manager()
        mgr.simulate(
            "enumerate",
            strategy_name=_cli_strategy_arg(getattr(args, "strategy", None)),
            force_refresh=bool(getattr(args, "force_flag", False)),
            stock_count=getattr(args, "stocks", None),
        )

    def _handle_simulate_price(self, args):
        """处理 simulate_price 命令"""
        mgr = self.app._ensure_strategy_manager()
        mgr.simulate(
            "price_factor",
            strategy_name=_cli_strategy_arg(getattr(args, "strategy", None)),
            force_refresh=bool(getattr(args, "force_flag", False)),
        )

    def _handle_simulate_allocation(self, args):
        """处理 simulate_allocation 命令"""
        mgr = self.app._ensure_strategy_manager()
        mgr.simulate(
            "capital_allocation",
            strategy_name=_cli_strategy_arg(getattr(args, "strategy", None)),
            force_refresh=bool(getattr(args, "force_flag", False)),
        )

    def _handle_export_adj_factor_csv(self, args):
        """处理 export_adj_factor_csv 命令"""
        logger.info("📤 手动导出复权因子事件季度 CSV...")
        self.app.export_adj_factor_csv(base_date=args.base_date)


# ============================================================================
# 主函数
# ============================================================================
def main():
    """主函数"""
    # 解析参数
    parser = create_argument_parser()
    args = parser.parse_args()

    # 版本 / 应用升级（尽早返回，避免初始化重资源）
    if getattr(args, "update_flag", False):
        raise SystemExit(_run_app_update())

    if args.version:
        print(f"NTQ Core Version: {system_meta.version}")
        print(f"Release Date: {system_meta.release_date}")
        return

    package_exit = _resolve_package_cli(args, parser)
    if package_exit is not None:
        raise SystemExit(package_exit)

    scaffold_exit = _resolve_scaffold_cli(args, parser)
    if scaffold_exit is not None:
        raise SystemExit(scaffold_exit)

    # 初始化全局日志（基于 logging.json + userspace 覆盖）
    LoggingManager.setup_logging()
    if args.verbose:
        # verbose 模式下，将根 logger 提升到 DEBUG
        logging.getLogger().setLevel(logging.DEBUG)
    
    args.renew_table_name = ''
    _normalize_cli_flags(args)
    # 解析命令
    command = resolve_command(args)
    attach_renew_cli_context(args, command)

    # 创建应用实例
    app = App(is_verbose=args.verbose)
    
    # 执行命令
    try:
        logger.info("=" * 60)
        logger.info(f"▶️  执行命令: {command}")
        logger.info("=" * 60)
        
        executor = CommandExecutor(app)
        executor.execute(command, args)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 命令执行完成")
        logger.info("=" * 60)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  用户中断执行")
        try:
            from core.infra.db.engines.duckdb.process_pool_scope import (
                recover_after_worker_pool_interrupt,
            )

            recover_after_worker_pool_interrupt()
        except Exception as exc:
            logger.warning("DuckDB / worker 中断收尾未完全成功: %s", exc)
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
