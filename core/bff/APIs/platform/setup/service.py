"""Setup service logic."""

from pathlib import Path

from core.infra.project_context import ProjectContext
from core.infra.setup import Setup

from core.bff.shared.response import ok, from_payload


class SetupService:
    """Setup 业务服务（不包含 route 绑定）。"""

    def __init__(self, setup_runtime):
        self._setup_runtime = setup_runtime

    def get_setup_definition(self):
        """获取 setup 步骤定义（来自 setup/*/meta.json）。"""
        steps = Setup.meta.load_step_meta(ui_only=True)
        userspace_abs_path = str(ProjectContext.path.get_userspace_root().resolve())
        userspace_exists = Path(userspace_abs_path).exists()
        for step in steps:
            if step.get("id") == "init_userspace":
                step["name"] = "初始化 userspace"
                schema = step.get("inputSchema") or step.get("requiredUserInputs") or []
                filtered_schema = []
                for field in schema:
                    if field.get("key") == "userspaceTargetPath":
                        field["label"] = "userspace 路径"
                        field["defaultValue"] = userspace_abs_path
                        field["helperText"] = "默认使用该绝对路径；勾选后可改成你自己的路径。"
                        field["editableByCheckbox"] = True
                        field["editableLabel"] = "我想自定义 userspace 路径"
                        filtered_schema.append(field)
                        continue
                    if field.get("key") == "userspaceConflictPolicy":
                        field["showByDefault"] = bool(userspace_exists)
                        filtered_schema.append(field)
                        continue
                    filtered_schema.append(field)
                step["inputSchema"] = filtered_schema
            elif step.get("id") == "import_data":
                step["name"] = "导入演示数据"
            elif step.get("id") == "resolve_ml_deps":
                step["name"] = "机器学习依赖"
            elif step.get("id") == "resolve_deps":
                step["name"] = "核心依赖"
        return ok({"steps": steps})

    def get_setup_status(self):
        return ok(self._setup_runtime.get_status())

    def start_setup(self):
        return from_payload(self._setup_runtime.start())

    def submit_setup_step(self, step_id: str, inputs: dict):
        return from_payload(self._setup_runtime.submit(step_id, inputs or {}))

    def retry_setup(self):
        return from_payload(self._setup_runtime.retry())

    def reset_setup(self):
        return from_payload(self._setup_runtime.reset())

    def precheck_db_connection(self, inputs: dict):
        return from_payload(self._setup_runtime.precheck_db_connection(inputs or {}))

    def precheck_userspace_path(self, inputs: dict):
        return from_payload(self._setup_runtime.precheck_userspace_path(inputs or {}))

    def get_import_data_progress(self):
        return from_payload(self._setup_runtime.get_import_data_progress())

    def get_ml_extras_status(self):
        return from_payload(self._setup_runtime.get_ml_extras_status())

    def install_ml_extras(self):
        return from_payload(self._setup_runtime.install_ml_extras())
