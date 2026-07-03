# """enumerate 回测参数解析（facade 入口使用）。"""
# from __future__ import annotations

# import json
# import logging
# from pathlib import Path
# from typing import Any, Dict, List

# logger = logging.getLogger(__name__)


# class BacktestParamsResolver:
#     """解析 enumerate 所需的 stock_list / start_date / end_date。"""

#     @staticmethod
#     def resolve_stock_list(strategy_folder: Path, settings: Dict[str, Any]) -> List[str]:
#         metadata_file = strategy_folder / "0_metadata.json"
#         if metadata_file.is_file():
#             try:
#                 with metadata_file.open("r", encoding="utf-8") as handle:
#                     metadata = json.load(handle)
#                 stock_list = metadata.get("stock_ids", [])
#                 if stock_list:
#                     logger.info("Loaded stock list from %s (%d stocks)", metadata_file, len(stock_list))
#                     return stock_list
#             except Exception as exc:
#                 logger.warning("Failed to load stock list from %s: %s", metadata_file, exc)

#         sampling = settings.get("sampling", {})
#         stock_pool = sampling.get("stock_pool", [])
#         if stock_pool:
#             logger.info(
#                 "Loaded stock list from settings.sampling.stock_pool (%d stocks)",
#                 len(stock_pool),
#             )
#             return stock_pool

#         logger.warning("No stock list found for backtest")
#         return []

#     @staticmethod
#     def resolve_backtest_dates(settings: Dict[str, Any]) -> Dict[str, str]:
#         core = settings.get("core", {})
#         start_date = core.get("start_date", "")
#         end_date = core.get("end_date", "")

#         if not start_date or not end_date:
#             logger.warning("Missing start_date or end_date in settings.core")
#             start_date = "2023-01-01"
#             end_date = "2023-12-31"

#         logger.info("Resolved backtest dates: %s ~ %s", start_date, end_date)
#         return {"start_date": start_date, "end_date": end_date}

#     @staticmethod
#     def resolve_all_params(strategy_folder: Path, settings: Dict[str, Any]) -> Dict[str, Any]:
#         stock_list = BacktestParamsResolver.resolve_stock_list(strategy_folder, settings)
#         dates = BacktestParamsResolver.resolve_backtest_dates(settings)
#         return {
#             "stock_list": stock_list,
#             "start_date": dates["start_date"],
#             "end_date": dates["end_date"],
#         }


# __all__ = ["BacktestParamsResolver"]
