"""分层样本股票池（``devcli.py ssp`` / ``pc``）。"""

from .stock_pool_ops import activate_stratified_pool, deactivate_stratified_pool

__all__ = ["activate_stratified_pool", "deactivate_stratified_pool"]
