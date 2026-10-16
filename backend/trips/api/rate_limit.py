"""Tiny in-memory sliding-window limiter (per process, per client IP)."""
import threading
import time
from collections import defaultdict, deque

from ..domain.exceptions import RateLimited

_WINDOW_SECONDS = 60
_lock = threading.Lock()
_hits = defaultdict(deque)


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR", "unknown")


def enforce(request, bucket, limit):
    now = time.monotonic()
    key = (bucket, client_ip(request))
    with _lock:
        hits = _hits[key]
        while hits and now - hits[0] > _WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= limit:
            retry_after = max(1, int(_WINDOW_SECONDS - (now - hits[0])))
            raise RateLimited(details={"retry_after_seconds": retry_after})
        hits.append(now)


def reset():
    with _lock:
        _hits.clear()
