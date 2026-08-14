"""Setup routes (endpoint definitions)."""

from flask import Blueprint, request

from .runtime import SetupRuntimeManager
from .service import SetupService

setup_api_bp = Blueprint("setup_api", __name__)
_setup_service = SetupService(setup_runtime=SetupRuntimeManager())


@setup_api_bp.route('/v1/setup/definition', methods=['GET'])
def get_setup_definition():
    return _setup_service.get_setup_definition()


@setup_api_bp.route('/v1/setup/status', methods=['GET'])
def get_setup_status():
    return _setup_service.get_setup_status()


@setup_api_bp.route('/v1/setup/start', methods=['POST'])
def start_setup():
    return _setup_service.start_setup()


@setup_api_bp.route('/v1/setup/steps/<step_id>/submit', methods=['POST'])
def submit_setup_step(step_id):
    payload = request.get_json(silent=True) or {}
    inputs = payload.get("inputs", {}) if isinstance(payload, dict) else {}
    return _setup_service.submit_setup_step(step_id, inputs)


@setup_api_bp.route('/v1/setup/retry', methods=['POST'])
def retry_setup():
    return _setup_service.retry_setup()


@setup_api_bp.route('/v1/setup/reset', methods=['POST'])
def reset_setup():
    return _setup_service.reset_setup()


@setup_api_bp.route('/v1/setup/steps/db_connection/precheck', methods=['POST'])
def precheck_db_connection():
    payload = request.get_json(silent=True) or {}
    inputs = payload.get("inputs", {}) if isinstance(payload, dict) else {}
    return _setup_service.precheck_db_connection(inputs)


@setup_api_bp.route('/v1/setup/steps/init_userspace/precheck-path', methods=['POST'])
def precheck_userspace_path():
    payload = request.get_json(silent=True) or {}
    inputs = payload.get("inputs", {}) if isinstance(payload, dict) else {}
    return _setup_service.precheck_userspace_path(inputs)


@setup_api_bp.route('/v1/setup/steps/import_data/progress', methods=['GET'])
def get_import_data_progress():
    return _setup_service.get_import_data_progress()
