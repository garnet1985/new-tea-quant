#!/usr/bin/env python3
"""
股票分析应用主入口

使用示例：
    python start-cli.py                      # 默认: scan
    python start-cli.py scan                 # 扫描投资机会
    python start-cli.py simulate             # 运行模拟链路（price_factor + capital_allocation）
    python start-cli.py renew                # 更新数据
    python start-cli.py analysis             # 分析结果
    python start-cli.py tag                  # 执行所有标签场景
    python start-cli.py tag --scenario xxx   # 执行指定标签场景
    python start-cli.py enumerate            # 枚举投资机会（测试用）
    python start-cli.py price_factor         # 价格因子回放模拟（基于枚举输出结果）
    python start-cli.py capital_allocation   # 资金分配模拟（基于枚举输出结果，真实资金约束）
    
    # 新快捷命令（模块首字母 + 行为命令）：
    python start-cli.py -d                   # DataSource（默认 renew）
    python start-cli.py -dr                  # DataSource renew（等同 -d）
    python start-cli.py -t                   # Tag（默认 generating）
    python start-cli.py -tg                  # Tag generating（等同 -t）
    python start-cli.py -s                   # Strategy（默认 scan，等同 -sc）
    python start-cli.py -sc                  # Strategy scan
    python start-cli.py -se                  # Strategy enumerate
    python start-cli.py -sp                  # Strategy price factor simulate
    python start-cli.py -sa                  # Strategy capital allocation simulate
    python start-cli.py -sy                  # Strategy analysis
    python start-cli.py -u                   # 检查并应用 core 版本更新
    python start-cli.py -update              # 同上
    python start-cli.py -h                   # 查看帮助
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
        os.execv(vpy, [vpy, os.path.join(repo_root, "start-cli.py"), *sys.argv[1:]])


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
    }
    return any(token in skip_flags for token in argv)


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
                "  或：python3 start-cli.py -sp  （将自动尝试 install.py）",
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

    async def renew_data(self):
        """
        一站式更新行情 + 标签数据（由 DataSourceManager 统一调度）
        
        Args:
            latest_completed_trading_date: 最新交易日（可选）
            stock_list: 预先准备好的股票列表（可选，全局共用）
            test_mode: 测试模式，只处理少量股票
            dry_run: 干运行模式，只检查流程，不写入标签
        """
        self.data_source.execute()

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
    
    def export_adj_factor_csv(self, base_date: str = None):
        """
        手动导出复权因子事件季度 CSV
        
        Args:
            base_date: 基准日期（YYYYMMDD 或 YYYY-MM-DD），用于推断"上一个完整季度"
                      如果不提供，则使用当前日期所在季度的上一个季度
        """
        adj_model = self.data_manager.stock.kline._adj_factor_event
        file_name = adj_model.get_current_quarter_csv_name(base_date=base_date)
        file_path = os.path.join(adj_model.csv_dir, file_name)
        logger.info(f"📤 准备导出复权因子事件 CSV: {file_name}")
        exported = adj_model.export_to_csv(file_path=file_path)
        logger.info(f"✅ 手动导出复权因子事件 CSV 完成: {exported} 条记录 -> {file_path}")


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
    
    # 位置参数（主命令）
    parser.add_argument(
        'command',
        nargs='?',
        help='要执行的命令（scan/simulate/simulate_price/simulate_allocation/renew/analysis/tag/enumerate/price_factor/capital_allocation/export_adj_factor_csv）'
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
                       help='DataSource 模块（默认 renew）')
    parser.add_argument('-dr', dest='data_renew_flag', action='store_true',
                       help='DataSource renew（等同 -d）')

    # Tag
    parser.add_argument('-t', dest='tag_flag', action='store_true',
                       help='Tag 模块（默认 generating）')
    parser.add_argument('-tg', dest='tag_generate_flag', action='store_true',
                       help='Tag generating（等同 -t）')

    # Strategy
    parser.add_argument('-s', dest='strategy_flag', action='store_true',
                       help='Strategy 模块（默认 scan，等同 -sc）')
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


def _run_app_update() -> int:
    """``-u`` / ``-update``：探测版本并可选运行 userspace updater 流水线。"""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent
    updater_dir = None
    for candidate in (
        repo_root / "userspace" / "updater",
        repo_root / "setup" / "updater",
    ):
        if (candidate / "upgrade_entry.py").is_file():
            updater_dir = candidate
            break
    if updater_dir is None:
        sys.stderr.write(
            "未找到升级器（userspace/updater 或 setup/updater）。"
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
    parser.add_argument('-f', '--force', dest='force_enumerate', action='store_true',
                       help='强制/放宽模式：scan 时表示 demo；枚举(-se)跳过 DbCache；价格因子(-sp)跳过 Simulator Res DB 读缓存')
    parser.add_argument('--base-date', type=str,
                       help='基准日期（YYYYMMDD 或 YYYY-MM-DD，用于 export_adj_factor_csv）')
    parser.add_argument('-v', '--version', action='store_true',
                       help='显示当前 core 版本信息并退出')
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
  renew                更新数据（更新股票行情、标签等数据）
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
    %(prog)s -d                   DataSource renew
    %(prog)s -t                   Tag generating
    %(prog)s -s                   Strategy scan
    %(prog)s -se                  Strategy enumerate
    %(prog)s -se -f               Strategy enumerate（强制刷新，跳过缓存复用）
    %(prog)s -sp                  Strategy price factor simulation
    %(prog)s -sp -f               Strategy price factor（跳过指纹读缓存，强制重算）
    %(prog)s -sa                  Strategy capital allocation simulation
    %(prog)s -sy                  Strategy analysis
    %(prog)s -u                   检查并应用 core 版本更新

  额外参数:
    %(prog)s simulate --strategy example    只运行指定策略
    %(prog)s analysis --session xxx         分析指定session
    %(prog)s tag --scenario xxx             执行指定标签场景
    %(prog)s price_factor --strategy xx     使用 PriceFactorFlow 对指定策略做因子回放
    %(prog)s -se -V                         详细输出模式

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    '''


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
    valid_commands = {
        'scan', 'simulate', 'simulate_price', 'simulate_allocation',
        'renew', 'analysis', 'tag', 'enumerate', 'price_factor', 'capital_allocation', 'export_adj_factor_csv'
    }
    
    # 从位置参数获取命令
    cmd_from_positional = None
    if args.command:
        aliases = {
            "price_factor": "simulate_price",
            "capital_allocation": "simulate_allocation",
        }
        normalized = aliases.get(args.command, args.command)
        if normalized not in valid_commands:
            logger.error(f"❌ 无效的命令: {args.command}")
            logger.info(f"有效命令: {', '.join(sorted(valid_commands))}")
            sys.exit(1)
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
    
    # 验证命令一致性
    if cmd_from_positional and flags and cmd_from_positional not in flags:
        logger.error("❌ 命令冲突：位置参数和快捷 flag 指定了不同的命令")
        logger.info("请只使用一种方式指定命令，例如：`start-cli.py renew` 或 `start-cli.py -d`")
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
        """处理 renew 命令"""
        logger.info("🔄 更新数据...")
        asyncio.run(self.app.renew_data())
    
    def _handle_scan(self, args):
        """处理 scan 命令"""
        logger.info("🔍 扫描投资机会...")
        mgr = self.app._ensure_strategy_manager()
        mgr.scan(
            strategy_name=_cli_strategy_arg(getattr(args, "strategy", None)),
            demo=bool(getattr(args, "force_enumerate", False)),
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
            force_refresh=bool(getattr(args, "force_enumerate", False)),
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
            force_refresh=bool(getattr(args, "force_enumerate", False)),
            stock_count=getattr(args, "stocks", None),
        )

    def _handle_simulate_price(self, args):
        """处理 simulate_price 命令"""
        mgr = self.app._ensure_strategy_manager()
        mgr.simulate(
            "price_factor",
            strategy_name=_cli_strategy_arg(getattr(args, "strategy", None)),
            force_refresh=bool(getattr(args, "force_enumerate", False)),
        )

    def _handle_simulate_allocation(self, args):
        """处理 simulate_allocation 命令"""
        mgr = self.app._ensure_strategy_manager()
        mgr.simulate(
            "capital_allocation",
            strategy_name=_cli_strategy_arg(getattr(args, "strategy", None)),
            force_refresh=bool(getattr(args, "force_enumerate", False)),
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

    # 初始化全局日志（基于 logging.json + userspace 覆盖）
    LoggingManager.setup_logging()
    if args.verbose:
        # verbose 模式下，将根 logger 提升到 DEBUG
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 解析命令
    command = resolve_command(args)
    
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
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ 执行失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
