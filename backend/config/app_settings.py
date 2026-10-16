"""Application-level tunables: provider endpoints, timeouts, limits and cache TTLs.

Everything here can be overridden through environment variables so the same
code runs locally, in tests and in production without edits.
"""
import os


def _env_int(name, default):
    return int(os.getenv(name, default))


def _env_float(name, default):
    return float(os.getenv(name, default))


# --- Providers -------------------------------------------------------------
ROUTING_PROVIDER = os.getenv("ROUTING_PROVIDER", "osrm")  # "osrm" | "ors"
OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")
ORS_BASE_URL = os.getenv("ORS_BASE_URL", "https://api.openrouteservice.org")
ORS_API_KEY = os.getenv("ORS_API_KEY", "")
ORS_PROFILE = os.getenv("ORS_PROFILE", "driving-hgv")
WEATHER_BASE_URL = os.getenv("WEATHER_BASE_URL", "https://api.open-meteo.com")
PHOTON_BASE_URL = os.getenv("PHOTON_BASE_URL", "https://photon.komoot.io")
OUTBOUND_USER_AGENT = os.getenv(
    "OUTBOUND_USER_AGENT", "weather-aware-truck-routing/1.0 (assessment project)"
)

# --- HTTP resilience -------------------------------------------------------
HTTP_CONNECT_TIMEOUT = _env_float("HTTP_CONNECT_TIMEOUT", 5.0)
HTTP_READ_TIMEOUT = _env_float("HTTP_READ_TIMEOUT", 25.0)
HTTP_MAX_RETRIES = _env_int("HTTP_MAX_RETRIES", 2)
HTTP_BACKOFF_SECONDS = _env_float("HTTP_BACKOFF_SECONDS", 0.5)
HTTP_MAX_RETRY_AFTER_SECONDS = _env_float("HTTP_MAX_RETRY_AFTER_SECONDS", 5.0)
HTTP_MAX_RESPONSE_BYTES = _env_int("HTTP_MAX_RESPONSE_BYTES", 20 * 1024 * 1024)

# --- Trip input limits -----------------------------------------------------
ALLOWED_CHECKPOINT_INTERVALS = (10, 25, 50)
MAX_LOAD_WEIGHT_LB = _env_int("MAX_LOAD_WEIGHT_LB", 200_000)
MAX_REQUEST_BODY_BYTES = 16 * 1024
DEPARTURE_PAST_TOLERANCE_HOURS = 1
DEPARTURE_MAX_FUTURE_DAYS = 7
MIN_TRIP_SEPARATION_METERS = 500
MAX_ROUTES = 3

# --- Weather / corridor ----------------------------------------------------
FORECAST_HORIZON_HOURS = 48
WEATHER_BATCH_SIZE = 40
WEATHER_MAX_WORKERS = 4
WEATHER_CACHE_TTL_SECONDS = _env_int("WEATHER_CACHE_TTL_SECONDS", 30 * 60)
CHECKPOINT_WEATHER_GRID_DEG = 0.1
CORRIDOR_GRID_DEG = 0.25
CORRIDOR_SAMPLE_MILES = 20
CORRIDOR_MAX_POINTS = 150
GEOMETRY_SIMPLIFY_TOLERANCE_DEG = 0.001

# --- Geocoding -------------------------------------------------------------
GEOCODE_MIN_QUERY_LENGTH = 3
GEOCODE_MAX_QUERY_LENGTH = 200
GEOCODE_RESULT_LIMIT = 6
GEOCODE_CACHE_TTL_SECONDS = _env_int("GEOCODE_CACHE_TTL_SECONDS", 10 * 60)

# --- Application rate limits (per client IP, per minute) -------------------
RATE_LIMIT_ANALYZE_PER_MINUTE = _env_int("RATE_LIMIT_ANALYZE_PER_MINUTE", 12)
RATE_LIMIT_GEOCODE_PER_MINUTE = _env_int("RATE_LIMIT_GEOCODE_PER_MINUTE", 90)
