"""Request payload extraction helpers for strategy workbench routes."""


class StrategyWorkbenchRequestHelper:
    """Pure request parsing/normalization utilities."""

    @staticmethod
    def normalize_str_value(value, default: str = "") -> str:
        return str(value if value is not None else default).strip()

    @staticmethod
    def invoke_service_method(service_obj, method_name: str, *args, **kwargs):
        method = getattr(service_obj, method_name)
        return method(*args, **kwargs)

    @staticmethod
    def to_stripped_str(payload: dict, prop: str, default: str = "") -> str:
        return str((payload or {}).get(prop) or default).strip()

    @staticmethod
    def to_bool(payload: dict, *props: str, default: bool = False) -> bool:
        payload = payload or {}
        for prop in props:
            if prop in payload:
                return bool(payload.get(prop))
        return bool(default)

    @staticmethod
    def to_dict_or_none(payload: dict, prop: str):
        value = (payload or {}).get(prop)
        return value if isinstance(value, dict) else None
