"""Tag catalog routes — T1-01."""

from core.bff.APIs.tag.api_base import tag_api_bp
from core.bff.shared.request import pagination_params
from core.bff.shared.response import ok

from .implementer import impl as catalog_impl


@tag_api_bp.route("/v1/tags/list", methods=["GET"])
def get_tags_list():
    """GET /v1/tags/list — paginated tag scenario catalog."""
    api = catalog_impl.lazy_load()
    page, limit = pagination_params()
    items, total, data_end = api.fetch_page(page, limit)
    return ok(
        {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "data_end": data_end,
        }
    )
