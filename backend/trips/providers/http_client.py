"""Shared outbound HTTP client: explicit timeouts, bounded retries, safe error mapping."""
import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import httpx

from config import app_settings as cfg

logger = logging.getLogger(__name__)

_TRANSIENT_STATUS = {429, 500, 502, 503, 504}


def _sleep(seconds):  # indirection so tests can disable real sleeping
    time.sleep(seconds)


def _retry_delay(attempt, response):
    delay = cfg.HTTP_BACKOFF_SECONDS * (2**attempt)
    retry_after = response.headers.get("Retry-After") if response is not None else None
    if retry_after:
        try:
            delay = max(delay, float(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                delay = max(delay, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass
    return min(delay, cfg.HTTP_MAX_RETRY_AFTER_SECONDS)


def request_json(method, url, error_cls, *, params=None, json_body=None, headers=None):
    """Perform a request and return parsed JSON, or raise `error_cls(kind, detail)`.

    Retries only transient failures (timeouts, connection errors, 429, 5xx).
    Ordinary 4xx responses are never retried.
    """
    timeout = httpx.Timeout(cfg.HTTP_READ_TIMEOUT, connect=cfg.HTTP_CONNECT_TIMEOUT)
    request_headers = {"User-Agent": cfg.OUTBOUND_USER_AGENT, "Accept": "application/json", **(headers or {})}
    last_error = None

    for attempt in range(cfg.HTTP_MAX_RETRIES + 1):
        response = None
        try:
            response = httpx.request(
                method, url, params=params, json=json_body, headers=request_headers, timeout=timeout
            )
        except httpx.TimeoutException as exc:
            last_error = error_cls("timeout", f"timeout calling {url}: {exc!r}")
        except httpx.HTTPError as exc:
            last_error = error_cls("unavailable", f"network error calling {url}: {exc!r}")
        else:
            status = response.status_code
            if status < 400:
                return _parse_json(response, url, error_cls)
            kind = "rate_limited" if status == 429 else "unavailable" if status >= 500 else "rejected"
            last_error = error_cls(kind, f"HTTP {status} from {url}")
            if status not in _TRANSIENT_STATUS:
                break

        if attempt < cfg.HTTP_MAX_RETRIES:
            logger.warning("Transient failure (attempt %d): %s", attempt + 1, last_error.detail)
            _sleep(_retry_delay(attempt, response))

    logger.error("Provider call failed: %s", last_error.detail)
    raise last_error


def _parse_json(response, url, error_cls):
    if len(response.content) > cfg.HTTP_MAX_RESPONSE_BYTES:
        raise error_cls("bad_response", f"response from {url} exceeded size limit")
    try:
        return response.json()
    except ValueError as exc:
        raise error_cls("bad_response", f"invalid JSON from {url}: {exc}") from exc
