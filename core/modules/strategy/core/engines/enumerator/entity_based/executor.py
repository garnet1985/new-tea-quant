"""entity_based job executor（enumerator的回调函数集合）。"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class JobExecutor:
    """entity_based job executor（enumerator的回调函数集合）。

    包含4个回调函数，标注清楚进程归属和对应关系：

    ── 子进程钩子（在子进程内执行）──
    - on_child_process_task_start: 子进程task开始（数据加载、batch load降低IO）
    - execute: 执行函数（调用hooks.scan_opportunity）

    ── 主进程钩子（在主进程内执行）──
    - on_single_task_result: 单task结果回调（进度调度、累积数据）
    - on_after_all_tasks_complete: 全局清理（生成report）
    """

    # ─────────────────────────────────────────────────────────────
    # 子进程钩子（在子进程内执行）
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def on_child_process_task_start(job_context: Any) -> Dict[str, Any]:
        """子进程钩子：初始化per entity的contracts，batch load降低IO。

        对应关系：on_child_process_task_start
        执行位置：子进程内（通过run_job_lifecycle调用）

        Args:
            job_context: JobContext对象（包含job_id、payload等）

        Returns:
            Dict[str, Any]: 包含 entity_contracts 和 global_data 的结构

        功能：
        1. 使用 BatchDataLoader 批量加载所有 entity_ids 的数据（降低IO）
        2. 返回结构化数据（供 execute 使用）
        """
        logger.info("子进程task开始：job_id=%s", job_context.job_id)

        from core.modules.strategy.core.engines.enumerator.entity_based.services.batch_data_loader import (
            BatchDataLoader,
        )

        # 批量加载 bundle 数据（返回Contract实例）
        loaded_data = BatchDataLoader.load_bundle_data(job_context.payload)

        logger.info(
            "子进程task开始完成：entity_contracts_count=%d, global_keys=%d",
            len(loaded_data.get("entity_contracts", {})),
            len(loaded_data.get("global_data", {})),
        )

        return loaded_data

    @staticmethod
    def on_child_process_task_complete(job_context: Any) -> None:
        """子进程钩子：将缓冲的 opportunities 写入 CSV 后清空 buffer。"""
        from core.modules.strategy.core.engines.enumerator.entity_based.services.recorder import (
            EntityBasedEnumeratorRecorder,
        )

        EntityBasedEnumeratorRecorder.resolve(job_context.payload).flush_job_opportunities()

    @staticmethod
    def execute(job_context: Any) -> Dict[str, Any]:
        """执行函数：按calendar时间轴推进，调用hooks.scan_opportunity。

        对应关系：execute_fn
        执行位置：子进程内（通过run_job_lifecycle调用）

        Args:
            job_context: JobContext对象（包含job_id、payload、init等）

        Returns:
            执行结果（包含opportunities列表）

        流程（entity_based核心）：
        1. Calendar是全局共享的时间轴（从start到end）
        2. 遍历calendar（时间轴推进）
        3. 对每个日期调用Contract.until(as_of)获取所有entity的PIT数据
        4. 遍历entity，提取各自的PIT数据
        5. 构建DataContext调用scan_opportunity
        6. Contract内部维护每个entity的独立cursor（累进扫描）
        """
        logger.info("子进程执行开始（entity_based模式）")

        # Step 1: 从job_context提取必要数据
        payload = job_context.payload
        loaded_data = job_context.init  # on_child_process_task_start返回的数据
        entity_contracts = loaded_data.get("entity_contracts", {})  # Contract实例
        global_data = loaded_data.get("global_data", {})
        strategy_info = payload.get("strategy_info", {})
        settings_dict = payload.get("settings", {})
        entity_specified = payload.get("entity_specified", [])

        # Step 2: 动态加载hooks类
        hooks_module_path = strategy_info.get("hooks_module_path")
        hooks_class_name = strategy_info.get("hooks_class_name")

        if not hooks_module_path or not hooks_class_name:
            logger.error("缺少hooks信息：hooks_module_path或hooks_class_name")
            return {"success": False, "opportunities_count": 0, "error": "缺少hooks信息"}

        try:
            import importlib
            hooks_module = importlib.import_module(hooks_module_path)
            hooks_class = getattr(hooks_module, hooks_class_name)
            hooks_instance = hooks_class()
        except Exception as e:
            logger.error(f"加载hooks类失败：{e}", exc_info=True)
            return {"success": False, "opportunities_count": 0, "error": str(e)}

        # Step 3: 准备StrategySettings对象
        from core.modules.strategy.core.engines.shared.services.strategy_settings.strategy_settings import StrategySettings
        try:
            settings_obj = StrategySettings.from_dict(settings_dict)
        except Exception as e:
            logger.error(f"构建StrategySettings失败：{e}", exc_info=True)
            return {"success": False, "opportunities_count": 0, "error": str(e)}

        # Step 4: 构建calendar并获取open_dates
        from core.modules.data_contract import DATA_KEY
        calendar_data = global_data.get(DATA_KEY.TRADE_CALENDAR, [])
        open_dates = [str(item.get("date") or "").strip() for item in calendar_data if item.get("is_open")]

        if not open_dates:
            logger.warning("calendar数据为空，无法遍历日期")
            return {"success": True, "opportunities_count": 0, "warning": "calendar数据为空"}

        # 从entity_shared提取start_date和end_date
        entity_shared = payload.get("entity_shared", {})
        first_data_key_params = list(entity_shared.values())[0] if entity_shared else {}
        start_date = first_data_key_params.get("start", open_dates[0] if open_dates else "")
        end_date = first_data_key_params.get("end", open_dates[-1] if open_dates else "")

        # 构建calendar_dict（供DataContext使用）
        calendar_dict = {
            "period_start": start_date,
            "period_end": end_date,
            "open_dates": open_dates,
        }

        # Step 5: 遍历calendar（时间轴推进）
        from core.modules.strategy.core.hooks.context.data_context import DataContext
        opportunities = []

        for now in open_dates:
            logger.debug(f"处理日期：{now}")

            # Step 6: 对每个日期，调用Contract.until(as_of)获取所有entity的PIT数据
            pit_data_by_entity = {}
            for data_key, contract in entity_contracts.items():
                try:
                    # Contract.until(as_of)返回Dict[entity_id, PIT数据]
                    pit_data_dict = contract.until(as_of=now)

                    # 合并到pit_data_by_entity（按entity组织）
                    for entity_id, pit_rows in pit_data_dict.items():
                        if entity_id not in pit_data_by_entity:
                            pit_data_by_entity[entity_id] = {}
                        pit_data_by_entity[entity_id][data_key] = pit_rows

                except Exception as e:
                    logger.error(f"Contract.until失败：data_key={data_key}, now={now}, error={e}", exc_info=True)
                    continue

            # Step 7: 遍历entity，提取各自的PIT数据
            for entity_item in entity_specified:
                entity_id = entity_item.get("id")
                if not entity_id:
                    continue

                # 获取该entity的PIT数据（截至now的累计数据）
                per_entity_pit_data = pit_data_by_entity.get(entity_id, {})

                # 合并数据：per_entity PIT数据 + global数据
                complete_data = {**per_entity_pit_data, **global_data}

                # 构建assemble context（entity级别，不含当日数据）
                try:
                    ctx_base = DataContext.assemble(
                        strategy_name=strategy_info.get("key", ""),
                        settings=settings_obj,
                        stock_list=[entity_id],  # 单个entity
                        entity_id=entity_id,
                        entity_info={"id": entity_id},
                    )

                    # 构建fill context（填入当日PIT数据）
                    ctx = DataContext.fill(
                        ctx_base,
                        now=now,
                        data=complete_data,
                        calendar=calendar_dict,
                    )
                except Exception as e:
                    logger.error(f"构建DataContext失败：entity_id={entity_id}, now={now}, error={e}", exc_info=True)
                    continue

                # Step 8: 调用hooks.scan_opportunity()
                try:
                    opportunity = hooks_instance.scan_opportunity(ctx)
                    if opportunity:
                        opportunities.append({
                            "entity_id": entity_id,
                            "date": now,
                            "opportunity": opportunity.to_dict() if hasattr(opportunity, 'to_dict') else opportunity,
                        })
                except Exception as e:
                    logger.error(f"scan_opportunity失败：entity_id={entity_id}, now={now}, error={e}", exc_info=True)
                    continue

        logger.info(f"子进程执行完成：opportunities_count={len(opportunities)}")

        # 缓冲到 recorder，由 on_child_process_task_complete 写 CSV（避免 pickle 大列表）
        from core.modules.strategy.core.engines.enumerator.entity_based.services.recorder import (
            EntityBasedEnumeratorRecorder,
        )

        recorder = EntityBasedEnumeratorRecorder.resolve(payload)
        recorder.buffer_opportunities(opportunities)

        entities_with_opportunities = len(
            {str(item.get("entity_id") or "").strip() for item in opportunities if item.get("entity_id")}
        )
        return {
            "success": True,
            "opportunities_count": len(opportunities),
            "entities_with_opportunities": entities_with_opportunities,
        }

    # ─────────────────────────────────────────────────────────────
    # 主进程钩子（在主进程内执行）
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def on_single_task_result(report: Any, progress: Any) -> None:
        """主进程钩子：单task结果回调（进度调度、累积数据）。

        对应关系：on_single_task_result（EntityExecutor内部钩子）
        执行位置：主进程内（通过EntityExecutor._finish_future调用）

        Args:
            report: 单个task的执行报告（JobReport）
            progress: 运行进度（RunProgress）

        功能：
        1. 打印进度信息
        2. 累积数据的批量写操作（枚举器的结果）
        3. Catch错误的entity
        """
        logger.info(
            f"Task完成进度：{progress.finished}/{progress.total} "
            f"(成功={progress.ok}, 失败={progress.fail})"
        )

        # 打印单个task的信息
        logger.info(f"Task报告：job_id={report.job_id}, success={report.success}")

        # 轻量 summary（完整 opportunities 已落盘）
        if report.success and report.data:
            count = int(report.data.get("opportunities_count") or 0)
            logger.info("Task opportunities_count=%d", count)

        # Catch错误的entity
        if not report.success:
            error_msg = report.error or "Unknown error"
            logger.error(f"Task失败：job_id={report.job_id}, error={error_msg}")

    @staticmethod
    def on_after_all_tasks_complete(job_reports: List[Any], global_entity_cache: Any = None) -> None:
        """主进程钩子：全局清理（所有tasks完成后）。

        对应关系：on_after_all_tasks_complete
        执行位置：主进程内（通过BacktestEngine调用）

        Args:
            job_reports: 所有task的执行报告列表
            global_entity_cache: 全局entity缓存（可选）

        功能：
        1. 清理缓存、释放全局资源（共享内存）
        2. 打印完整统计信息
        3. 生成最终report（有完整的执行context和结果）
        """
        logger.info(f"所有tasks完成：total={len(job_reports)}")

        # 清理全局缓存（如共享内存）
        if global_entity_cache:
            try:
                global_entity_cache.cleanup()
                logger.info("全局缓存清理完成")
            except Exception as e:
                logger.warning(f"清理全局缓存失败：{e}")

        # 打印完整统计信息
        success_count = sum(1 for report in job_reports if report.success)
        fail_count = len(job_reports) - success_count

        logger.info(
            f"最终统计："
            f"total={len(job_reports)}, "
            f"success={success_count}, "
            f"fail={fail_count}"
        )


__all__ = ["JobExecutor"]