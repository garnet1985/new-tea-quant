from enum import Enum


class RenewMode(Enum):
    """
    Renew Mode enum
    """
    ROLLING = "rolling"
    INCREMENTAL = "incremental"
    REFRESH = "refresh"