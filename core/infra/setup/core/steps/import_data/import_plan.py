"""设置页「导入数据」选包计划（按是否已装载会员凭证）。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.infra.setup.core.steps.import_data.data_packages import describe_data_packages

PACK_LABELS = {
    "demo": "约 300 只股票 × 三年（公开演示包）",
    "member": "全 A 股 × 三年（会员包）",
}


def resolve_import_pack_kind(*, membership_configured: Optional[bool] = None) -> str:
    if membership_configured is None:
        from core.infra.membership import Membership

        membership_configured = bool(Membership.status().get("configured"))
    return "member" if membership_configured else "demo"


def build_import_plan() -> Dict[str, Any]:
    """给设置页的导入说明与确认框文案。"""
    from core.infra.membership import Membership

    membership = Membership.status()
    configured = bool(membership.get("configured"))
    kind = resolve_import_pack_kind(membership_configured=configured)
    packages = describe_data_packages()
    pack = (packages.get("packages") or {}).get(kind) or {}
    local_present = bool(pack.get("present"))
    pack_label = PACK_LABELS.get(kind, kind)
    size = str(pack.get("sizeLabel") or "").strip()

    if local_present:
        local_hint = f"本地已有该数据包{f'（{size}）' if size else ''}，导入时无需重新下载。"
    elif kind == "member":
        local_hint = "本地尚无会员包，导入时将通过任务管道从官网分卷下载。"
    else:
        local_hint = "本地尚无演示包，导入时将从官网下载。"

    warning = None
    if not configured:
        warning = (
            "若您已是会员：请先到「设置 → 会员」装载凭证，再导入。"
            "未装载将按公开演示包（约 300 股 × 三年）处理。"
        )

    return {
        "membershipConfigured": configured,
        "packKind": kind,
        "packLabel": pack_label,
        "localPresent": local_present,
        "localHint": local_hint,
        "warning": warning,
        "usesJobPipeline": kind == "member",
        "confirmTitle": "导入数据？",
        "confirmBody": (
            f"将导入：{pack_label}。"
            "数据包中的表会被清空后重写，可能覆盖已有行情。"
            "请先退出其他正在使用这个数据库的程序，再继续。"
            + (
                " 未检测到会员凭证，这不是全市场会员包。"
                if not configured
                else ""
            )
        ),
        "confirmActionLabel": (
            "仍导入演示包" if not configured else "开始导入"
        ),
        "dataPackages": packages,
    }
