"""Strategy workbench routes (endpoint definitions)."""

from flask import Blueprint, request

from .service import StrategyWorkbenchService

strategy_workbench_api_bp = Blueprint("strategy_workbench_api", __name__)
_strategy_workbench_service = StrategyWorkbenchService()


@strategy_workbench_api_bp.route('/v1/strategies', methods=['GET'])
def get_strategies():
    return _strategy_workbench_service.get_strategies()


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/settings', methods=['GET'])
def get_strategy_settings(strategy_name):
    return _strategy_workbench_service.get_strategy_settings(strategy_name)


@strategy_workbench_api_bp.route('/v1/strategies/<strategy_name>/settings', methods=['PUT'])
def save_strategy_settings(strategy_name):
    payload = request.get_json(silent=True) or {}
    return _strategy_workbench_service.save_strategy_settings(strategy_name, payload)


@strategy_workbench_api_bp.route('/v1/strategies/settings-options/allocation-modes', methods=['GET'])
def get_strategy_settings_options_allocation_modes():
    return _strategy_workbench_service.get_strategy_settings_options_allocation_modes()


@strategy_workbench_api_bp.route('/v1/strategies/settings-options/sampling-strategies', methods=['GET'])
def get_strategy_settings_options_sampling_strategies():
    return _strategy_workbench_service.get_strategy_settings_options_sampling_strategies()
