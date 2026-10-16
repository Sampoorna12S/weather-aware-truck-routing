"""Correlation IDs and the single place where exceptions become the JSON error contract."""
import logging
import uuid

from django.http import JsonResponse

from ..domain.exceptions import AppError

logger = logging.getLogger(__name__)


def error_response(error, request_id):
    body = {
        "error": {
            "code": error.code,
            "message": error.message,
            "retryable": error.retryable,
            "details": error.details,
            "request_id": request_id,
        }
    }
    response = JsonResponse(body, status=error.http_status)
    retry_after = error.details.get("retry_after_seconds") if isinstance(error.details, dict) else None
    if retry_after:
        response["Retry-After"] = str(retry_after)
    return response


class ApiErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response

    def process_exception(self, request, exception):
        request_id = getattr(request, "request_id", "-")
        if isinstance(exception, AppError):
            level = logging.WARNING if exception.http_status < 500 else logging.ERROR
            logger.log(level, "[%s] %s: %s | %s", request_id, exception.code, exception.message,
                       getattr(exception, "detail", ""))
            return error_response(exception, request_id)
        logger.exception("[%s] Unhandled error", request_id)
        return error_response(AppError(), request_id)
