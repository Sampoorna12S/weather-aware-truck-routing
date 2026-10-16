from config import app_settings as cfg

from .ors_provider import OrsProvider
from .osrm_provider import OsrmProvider

_PROVIDERS = {"osrm": OsrmProvider, "ors": OrsProvider}


def get_routing_provider(name=None):
    key = (name or cfg.ROUTING_PROVIDER).lower()
    try:
        return _PROVIDERS[key]()
    except KeyError:
        raise ValueError(f"Unknown ROUTING_PROVIDER {key!r}; expected one of {sorted(_PROVIDERS)}") from None
