#!/usr/bin/env python3
"""策略顶层编排：CLI / 脚本侧只传参，校验与依赖由本类内部处理。"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.infra.project_context import PathManager
from core.modules.data_contract.cache import ContractCacheManager
from core.modules.data_contract.data_contract_manager import DataContractManager
from core.modules.data_manager import DataManager
from core.modules.strategy.engines.shared.data_classes.discovered_strategy import (
    DiscoveredStrategy,
)
from core.modules.strategy.engines.scanner.scanner import Scanner
from core.modules.strategy.engines.simulator.capital_allocation.capital_allocation_flow import (
    CapitalAllocationFlow,
)
from core.modules.strategy.engines.simulator.price_factor.price_factor_flow import (
    PriceFactorFlow,
)
from core.modules.strategy.services.discovery import StrategyDiscoveryHelper

logger = logging.getLogger(__name__)

_SIM_KINDS = frozenset({"price_factor", "capital_allocation", "full", "enumerate"})
_SIM_KIND_ALIASES = {"enum": "enumerate"}


def _normalize_simulate_kind(kind: str) -> str:
    k = str(kind or "").strip()
    return _SIM_KIND_ALIASES.get(k, k)


class StrategyManager:
    """策略模块入口：scan / simulate(kind) / 分析结果。"""

    def __init__(self, is_verbose: bool = False):
        self.is_verbose = is_verbose
        self._contract_cache = ContractCacheManager()
        self._data_contract_manager = DataContractManager(
            contract_cache=self._contract_cache
        )
        self.data_mgr = DataManager(is_verbose=False)
        self.validated_strategies = StrategyDiscoveryHelper.discover_strategies()

    def lookup_strategy_info(
        self, strategy_name: str
    ) -> Optional[DiscoveredStrategy]:
        info = self.validated_strategies.get(strategy_name)
        if info is not None:
            return info
        folder = PathManager.userspace() / "strategies" / strategy_name
        if not folder.is_dir():
            return None
        return StrategyDiscoveryHelper.load_strategy(folder)

    def list_strategies(self) -> List[str]:
        return list(self.validated_strategies.keys())

    def get_strategy_info(self, strategy_name: str) -> Optional[DiscoveredStrategy]:
        return self.lookup_strategy_info(strategy_name)

    # --- 策略名解析（CLI 未指定 / 显式指定）---

    def _normalize_optional_name(self, strategy_name: Optional[str]) -> Optional[str]:
        if strategy_name is None:
            return None
        t = str(strategy_name).strip()
        return t or None

    def _resolve_default_single_strategy_name(self, strategy_name: Optional[str]) -> Optional[str]:
        """simulate / enumerate：未指定时从启用策略中选默认；显式时校验存在。"""
        explicit = self._normalize_optional_name(strategy_name)
        if explicit is not None:
            if self.get_strategy_info(explicit) is None:
                logger.error("策略不存在: %s", explicit)
                return None
            return explicit

        enabled = sorted(
            name for name, info in self.validated_strategies.items() if info.is_enabled
        )
        if not enabled:
            logger.error(
                "未指定策略名，且当前没有任何 is_enabled=True 的策略。"
                "请在 userspace/strategies/<name>/settings.py 中启用策略，或传入 strategy_name。"
            )
            return None
        if len(enabled) == 1:
            name = enabled[0]
            logger.info("未指定策略名，使用唯一启用策略: %s", name)
            return name
        chosen = enabled[0]
        logger.warning(
            "未指定策略名，当前多个启用策略 %s；默认使用 %s。请显式传入 strategy_name。",
            enabled,
            chosen,
        )
        return chosen

    def _resolve_scan_targets(self, strategy_name: Optional[str]) -> List[DiscoveredStrategy]:
        """scan：显式名 → 单策略（未启用也允许）；未指定 → 全部启用策略。"""
        explicit = self._normalize_optional_name(strategy_name)
        if explicit is not None:
            info = self.get_strategy_info(explicit)
            if info is None:
                logger.error("策略不存在: %s", explicit)
                return []
            if not info.is_enabled:
                logger.warning("策略未启用，仍将扫描: %s", explicit)
            return [info]
        targets = [i for i in self.validated_strategies.values() if i.is_enabled]
        if not targets:
            logger.warning("没有可扫描的策略")
        return sorted(targets, key=lambda x: x.name)

    @staticmethod
    def _present_enumerate(strategy_name: str, summary_results: Any) -> None:
        from core.modules.strategy.engines.simulator.enumerator.data_classes.report import (
            EnumeratorReport,
        )

        EnumeratorReport.present(
            strategy_name=str(strategy_name or ""),
            summary_results=summary_results or [],
        )

    @staticmethod
    def _present_price_summary(
        strategy_name: str,
        summary: dict,
        *,
        used_db_cache: bool = False,
    ) -> None:
        from core.modules.strategy.engines.simulator.price_factor.data_classes.report import (
            PriceReport,
        )

        PriceReport.present_session_summary(
            summary if isinstance(summary, dict) else {},
            strategy_name=str(strategy_name or ""),
            used_db_cache=used_db_cache,
        )

    @staticmethod
    def _present_capital_summary(
        strategy_name: str,
        summary: dict,
        *,
        used_db_cache: bool = False,
    ) -> None:
        from core.modules.strategy.engines.simulator.capital_allocation.data_classes.report import (
            CapitalReport,
        )

        CapitalReport.present_session_summary(
            summary if isinstance(summary, dict) else {},
            strategy_name=str(strategy_name or ""),
            used_db_cache=used_db_cache,
        )

    def _workbench_step_cli(
        self,
        strategy_name: str,
        step: str,
        *,
        force_refresh: bool,
        stock_count: Optional[int] = None,
    ) -> Any:
        from core.modules.strategy.execution_manager.adapters.cli import (
            run_workbench_step_via_cli_contract,
        )

        info = self.get_strategy_info(strategy_name)
        if not info:
            logger.warning("策略不存在: %s", strategy_name)
            return None
        api_settings = dict(info.settings.to_dict())
        try:
            return run_workbench_step_via_cli_contract(
                strategy_name=strategy_name,
                step=step,
                api_settings=api_settings,
                is_force=force_refresh,
                verbose=self.is_verbose,
                engine_verbose=self.is_verbose,
                stock_count=stock_count,
            )
        except ValueError as exc:
            logger.warning("%s", exc)
            return None

    def scan(
        self,
        strategy_name: Optional[str] = None,
        *,
        demo: bool = False,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        机会扫描。未指定 ``strategy_name`` 时扫描全部 **已启用** 策略。

        ``demo=True``：放宽「日历最后交易日 vs K 线最新日」对齐校验（等同原 CLI ``-f`` 用于 scan）。
        """
        _ = date
        targets = self._resolve_scan_targets(strategy_name)
        if not targets:
            return {}

        kline_latest = str(self.data_mgr.stock.kline.load_latest_date("daily") or "").strip()
        if not kline_latest:
            logger.error("无法解析 K 线最新日期（sys_stock_klines 可能为空）")
            return {}

        cal_latest = ""
        if not demo:
            cal_latest = str(
                self.data_mgr.service.calendar.get_latest_completed_trading_date() or ""
            ).strip()
            if not cal_latest:
                logger.error("无法解析最新已完成交易日（日历服务不可用）")
                return {}
            if cal_latest != kline_latest:
                logger.error(
                    "❌ 数据未对齐最新交易日：calendar=%s，kline=%s", cal_latest, kline_latest
                )
                return {}
        else:
            cal_latest = ""

        last_pct = {"v": -1}

        def _on_job_done(payload: dict) -> None:
            try:
                pct = int(payload.get("progress_pct", 0) or 0)
                if pct >= 100 or pct - last_pct["v"] >= 5:
                    last_pct["v"] = pct
                    done = (
                        int(payload.get("completed_jobs", 0) or 0)
                        + int(payload.get("failed_jobs", 0) or 0)
                        + int(payload.get("cancelled_jobs", 0) or 0)
                    )
                    total = int(payload.get("total_jobs", 0) or 0)
                    print(f"  进度：{pct}%（{done}/{total}）", flush=True)
            except Exception:
                pass

        results: Dict[str, Any] = {}
        for info in targets:
            name = info.name
            if len(targets) > 1:
                print(f"--- strategy={name} ---")
            else:
                if demo:
                    print(f"🔍 扫描（DEMO）· strategy={name} · asof(kline_latest)={kline_latest}")
                else:
                    print(
                        f"🔍 扫描（STRICT）· strategy={name} · latest_completed={cal_latest}"
                    )

            scanner = Scanner(
                strategy_name=name,
                data_manager=self.data_mgr,
                is_verbose=self.is_verbose,
                strategy_info=info,
            )
            if demo:
                try:
                    scanner.settings.scanner["use_strict_previous_trading_day"] = False
                except Exception:
                    pass
            results[name] = scanner.scan(on_job_done=_on_job_done)

        print("✅ 扫描完成")
        for name, rep in results.items():
            if len(results) > 1:
                print(f"[{name}]")
            print(rep)
        return results

    def simulate(
        self,
        kind: str,
        strategy_name: Optional[str] = None,
        *,
        force_refresh: bool = False,
        stock_count: Optional[int] = None,
        session_id: Optional[str] = None,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        模拟 / 回测入口（与 CLI 子命令对齐）。

        ``kind``:
        - ``enumerate``（别名 ``enum``）：机会枚举（工作台 ``enum`` 步）
        - ``price_factor``：价格因子模拟
        - ``capital_allocation``：资金分配模拟
        - ``full``：先 price 再 capital

        ``strategy_name`` 未传时：在启用策略中按单策略默认规则解析。
        ``stock_count`` 仅对 ``enumerate`` 生效。
        """
        if session_id or date:
            logger.info(
                "simulate(session_id/date) 暂未接管，当前由引擎内部规则处理"
            )

        k = _normalize_simulate_kind(kind)
        if k not in _SIM_KINDS:
            logger.error(
                "simulate(kind) 的 kind 须为 enumerate|enum / price_factor / "
                "capital_allocation / full，收到 %r",
                kind,
            )
            return {}

        name = self._resolve_default_single_strategy_name(strategy_name)
        if not name:
            return {}

        if k == "enumerate":
            rows = self._run_enumerate_cli(name, force_refresh, stock_count)
            return {"enumerate": rows} if rows is not None else {}

        if k == "full":
            print("🎮 模拟链路 · PriceFactor → CapitalAllocation …")
            out: Dict[str, Any] = {}
            pr = self._run_price_factor_cli(name, force_refresh)
            if pr is not None:
                out["price_factor"] = pr
            cr = self._run_capital_allocation_cli(name, force_refresh)
            if cr is not None:
                out["capital_allocation"] = cr
            return out

        if k == "price_factor":
            r = self._run_price_factor_cli(name, force_refresh)
            return {"price_factor": r} if r is not None else {}

        r = self._run_capital_allocation_cli(name, force_refresh)
        return {"capital_allocation": r} if r is not None else {}

    def _run_enumerate_cli(
        self,
        strategy_name: str,
        force_refresh: bool,
        stock_count: Optional[int],
    ) -> Optional[List[Any]]:
        done = self._workbench_step_cli(
            strategy_name,
            "enum",
            force_refresh=force_refresh,
            stock_count=stock_count,
        )
        if done is None:
            return None

        summary_results = (
            done.last_payload if isinstance(done.last_payload, list) else []
        )
        if self.is_verbose:
            print(f"🏁 枚举完成 · strategy={strategy_name} · snapshot_id={done.snapshot_id}")

        self._present_enumerate(strategy_name, summary_results)
        return summary_results

    def _run_price_factor_cli(self, strategy_name: str, force_refresh: bool) -> Optional[dict]:
        print(f"🎯 PriceFactorFlow · strategy={strategy_name}")
        if force_refresh:
            print("🔁 --force：跳过 price_factor DbCache 读路径，强制重跑模拟")
        done = self._workbench_step_cli(
            strategy_name, "price", force_refresh=force_refresh
        )
        if done is None:
            return None
        summary = done.last_payload
        if not summary or not isinstance(summary, dict):
            logger.warning("PriceFactorFlow 未返回任何结果")
            return None
        self._present_price_summary(
            strategy_name,
            summary,
            used_db_cache=bool(done.last_used_db_cache),
        )
        return summary

    def _run_capital_allocation_cli(self, strategy_name: str, force_refresh: bool) -> Optional[dict]:
        print(f"💰 CapitalAllocationFlow · strategy={strategy_name}")
        if force_refresh:
            print("🔁 --force：跳过 capital_allocation DbCache 读路径，强制重跑模拟")
        done = self._workbench_step_cli(
            strategy_name, "capital", force_refresh=force_refresh
        )
        if done is None:
            return None
        summary = done.last_payload
        if not summary or not isinstance(summary, dict):
            logger.warning(
                "CapitalAllocationFlow 未返回任何结果（常见原因：枚举 0 机会、无 buy 事件，"
                "或 sampling.pool.file 路径须相对策略目录名而非 settings.name）"
            )
            return None
        self._present_capital_summary(
            strategy_name,
            summary,
            used_db_cache=bool(done.last_used_db_cache),
        )
        return summary

    def analyze_simulation_outputs(self, *, session_id: Optional[str] = None) -> None:
        """
        读取各启用策略下 ``results/simulations/price`` / ``results/simulations/capital`` 最新版本摘要并打日志。

        ``session_id`` 预留，当前未使用。
        """
        _ = session_id

        strategy_names = [
            name for name, info in self.validated_strategies.items() if info.is_enabled
        ]
        if not strategy_names:
            logger.warning("没有启用的策略可分析")
            return

        def _read_latest_version(root):
            meta = json.loads((root / "meta.json").read_text(encoding="utf-8"))
            latest_id = int(meta.get("next_version_id", 1)) - 1
            if latest_id <= 0:
                return None
            return root / str(latest_id)

        found = False
        for sn in strategy_names:
            pf_root = PathManager.strategy_simulation_price(sn)
            ca_root = PathManager.strategy_simulation_capital(sn)

            pf_latest = _read_latest_version(pf_root) if (pf_root / "meta.json").is_file() else None
            ca_latest = _read_latest_version(ca_root) if (ca_root / "meta.json").is_file() else None

            if not pf_latest and not ca_latest:
                continue

            found = True
            logger.info("📊 strategy=%s", sn)

            if pf_latest:
                ss = pf_latest / "0_session_summary.json"
                if ss.is_file():
                    data = json.loads(ss.read_text(encoding="utf-8"))
                    logger.info("   price_factor: version=%s keys=%s", pf_latest.name, list(data.keys()))
                else:
                    logger.info(
                        "   price_factor: version=%s (missing 0_session_summary.json)", pf_latest.name
                    )

            if ca_latest:
                summary = ca_latest / "summary_strategy.json"
                if summary.is_file():
                    data = json.loads(summary.read_text(encoding="utf-8"))
                    logger.info(
                        "   capital_allocation: version=%s keys=%s", ca_latest.name, list(data.keys())
                    )
                else:
                    logger.info(
                        "   capital_allocation: version=%s (missing summary_strategy.json)",
                        ca_latest.name,
                    )

        if not found:
            logger.warning("未找到可分析的 simulations 结果（请先运行 -sp/-sa）")

    # --- 旧版「直接 Flow」多策略模拟（不经工作台编排）；供非 CLI 调用方保留 ---

    def run_legacy_flow_simulate(
        self,
        strategy_name: Optional[str] = None,
        *,
        session_id: Optional[str] = None,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """不经 ``execution_manager``，对解析到的策略依次跑 PriceFactor + Capital Flow。"""
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        _ = date

        targets = self._resolve_targets_legacy(strategy_name, enabled_only=True)
        if not targets:
            logger.warning("没有可模拟的策略")
            return {}

        if session_id:
            logger.info(
                "run_legacy_flow_simulate(session_id) 暂未接管，当前由引擎内部规则处理"
            )

        results: Dict[str, Any] = {}
        for info in targets:
            price_result = PriceFactorFlow(is_verbose=self.is_verbose).run(
                info.name, strategy_info=info
            )
            capital_result = CapitalAllocationFlow(is_verbose=self.is_verbose).run(
                info.name, strategy_info=info
            )
            results[info.name] = {
                "price_factor": price_result,
                "capital_allocation": capital_result,
            }
        return results

    @property
    def contract_cache(self) -> ContractCacheManager:
        return self._contract_cache

    def clear_contract_cache(self) -> None:
        self._contract_cache.clear_all()

    def _resolve_targets_legacy(
        self, strategy_name: Optional[str], enabled_only: bool = True
    ) -> List[DiscoveredStrategy]:
        explicit = self._normalize_optional_name(strategy_name)
        if explicit is not None:
            info = self.lookup_strategy_info(explicit)
            if not info:
                return []
            if enabled_only and not info.is_enabled:
                return []
            return [info]
        if enabled_only:
            return [i for i in self.validated_strategies.values() if i.is_enabled]
        return list(self.validated_strategies.values())
