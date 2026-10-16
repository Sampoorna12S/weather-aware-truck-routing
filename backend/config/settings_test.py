"""Settings used by pytest: deterministic, no real keys, no retry delays."""
import os

os.environ["DJANGO_DEBUG"] = "true"
os.environ["DJANGO_SECRET_KEY"] = "test-key"
os.environ["HTTP_BACKOFF_SECONDS"] = "0"
os.environ["ROUTING_PROVIDER"] = "osrm"

from .settings import *  # noqa: E402,F401,F403
