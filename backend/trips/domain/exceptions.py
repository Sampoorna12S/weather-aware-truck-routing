"""Domain exceptions. Each carries the data the API layer needs for the error contract."""


class AppError(Exception):
    http_status = 500
    code = "INTERNAL_ERROR"
    retryable = False
    message = "Something went wrong."

    def __init__(self, message=None, *, code=None, details=None, retryable=None, http_status=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or {}
        if retryable is not None:
            self.retryable = retryable
        if http_status is not None:
            self.http_status = http_status


class ValidationFailed(AppError):
    http_status = 400
    code = "VALIDATION_ERROR"
    message = "Some trip inputs are invalid."

    def __init__(self, fields, message=None):
        super().__init__(message, details={"fields": fields})
        self.fields = fields


class MethodNotAllowed(AppError):
    http_status = 405
    code = "METHOD_NOT_ALLOWED"
    message = "This HTTP method is not allowed for this endpoint."


class NotFound(AppError):
    http_status = 404
    code = "NOT_FOUND"
    message = "The requested resource does not exist."


class RateLimited(AppError):
    http_status = 429
    code = "RATE_LIMITED"
    retryable = True
    message = "Too many requests. Please wait a moment and try again."


class NoRouteFound(AppError):
    http_status = 404
    code = "ROUTE_NOT_FOUND"
    message = "No drivable route was found between these locations. Try different places."


class ProviderError(AppError):
    """Base for failures of an external provider. `kind` picks status and retry policy."""

    provider_label = "provider"
    code_prefix = "PROVIDER"

    _KINDS = {
        "timeout": (504, "TIMEOUT", True, "{} timed out. Please try again."),
        "unavailable": (503, "UNAVAILABLE", True, "{} is temporarily unavailable."),
        "rate_limited": (503, "RATE_LIMITED", True, "{} is rate limiting requests. Try again shortly."),
        "bad_response": (502, "BAD_RESPONSE", False, "{} returned an unexpected response."),
        "rejected": (502, "REJECTED", False, "{} rejected the request."),
    }

    def __init__(self, kind="unavailable", detail=None):
        status, suffix, retryable, template = self._KINDS[kind]
        super().__init__(
            template.format(self.provider_label.capitalize()),
            code=f"{self.code_prefix}_{suffix}",
            retryable=retryable,
            http_status=status,
        )
        self.kind = kind
        self.detail = detail  # logged server-side only, never sent to the client


class RoutingProviderError(ProviderError):
    provider_label = "routing service"
    code_prefix = "ROUTING_PROVIDER"


class WeatherProviderError(ProviderError):
    provider_label = "weather service"
    code_prefix = "WEATHER_PROVIDER"


class GeocodingProviderError(ProviderError):
    provider_label = "location search"
    code_prefix = "GEOCODING_PROVIDER"
