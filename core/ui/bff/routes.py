"""
BFF API 路由定义
"""

from flask import Blueprint, request
from .api import BFFApi

# 创建蓝图
api_bp = Blueprint('api', __name__)
# 延迟初始化，避免在模块导入时创建实例
bff_api = None

def get_bff_api():
    """获取BFF API实例，延迟初始化"""
    global bff_api
    if bff_api is None:
        bff_api = BFFApi()
    return bff_api

@api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return get_bff_api().health_check()

# ==================== v1 - 新版 API（当前仅保留 setup + strategies） ====================

@api_bp.route('/v1/setup/definition', methods=['GET'])
def get_setup_definition():
    """获取 setup 步骤定义"""
    return get_bff_api().get_setup_definition()


@api_bp.route('/v1/setup/status', methods=['GET'])
def get_setup_status():
    """获取 setup 运行状态"""
    return get_bff_api().get_setup_status()


@api_bp.route('/v1/setup/start', methods=['POST'])
def start_setup():
    """启动 setup 流程"""
    return get_bff_api().start_setup()


@api_bp.route('/v1/setup/steps/<step_id>/submit', methods=['POST'])
def submit_setup_step(step_id):
    """提交互动步骤输入"""
    payload = request.get_json(silent=True) or {}
    inputs = payload.get("inputs", {}) if isinstance(payload, dict) else {}
    return get_bff_api().submit_setup_step(step_id, inputs)


@api_bp.route('/v1/setup/retry', methods=['POST'])
def retry_setup():
    """重试失败步骤"""
    return get_bff_api().retry_setup()


@api_bp.route('/v1/setup/reset', methods=['POST'])
def reset_setup():
    """重置 setup 运行状态"""
    return get_bff_api().reset_setup()


@api_bp.route('/v1/setup/steps/db_connection/precheck', methods=['POST'])
def precheck_db_connection():
    """预检查数据库是否已存在（用于前端风险确认弹窗）"""
    payload = request.get_json(silent=True) or {}
    inputs = payload.get("inputs", {}) if isinstance(payload, dict) else {}
    return get_bff_api().precheck_db_connection(inputs)


@api_bp.route('/v1/setup/steps/init_userspace/precheck-path', methods=['POST'])
def precheck_userspace_path():
    """预检查 userspace 目标路径是否已存在（用于动态展示覆盖/跳过选项）"""
    payload = request.get_json(silent=True) or {}
    inputs = payload.get("inputs", {}) if isinstance(payload, dict) else {}
    return get_bff_api().precheck_userspace_path(inputs)


@api_bp.route('/v1/setup/steps/import_data/progress', methods=['GET'])
def get_import_data_progress():
    """读取 import_data 步骤进度（表级）"""
    return get_bff_api().get_import_data_progress()

@api_bp.route('/v1/strategies', methods=['GET'])
def get_strategies():
    """获取已发现策略列表（策略工作台 list 页使用）"""
    return get_bff_api().get_strategies()
