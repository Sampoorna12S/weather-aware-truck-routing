"""Pure weather-risk classification. No I/O, no Django."""
from . import risk_rules as rules
from .enums import DataStatus, RiskLevel


def _classify(value, t):
    if value is None:
        return RiskLevel.UNKNOWN
    at_no_travel = value >= t.no_travel_at if t.no_travel_inclusive else value > t.no_travel_at
    if at_no_travel:
        return RiskLevel.NO_TRAVEL
    if value >= t.severe_from:
        return RiskLevel.SEVERE
    if value >= t.high_from:
        return RiskLevel.HIGH
    if value >= t.moderate_from:
        return RiskLevel.MODERATE
    return RiskLevel.LOW


def _worst(*levels):
    return max(levels, key=lambda level: level.rank)


def classify_wind(wind_mph, load_weight_lb):
    """Base wind band, then the load overrides (which can only raise the level)."""
    level = _classify(wind_mph, rules.WIND_MPH)
    if wind_mph is None:
        return level
    lo, hi = rules.WIND_HEAVY_LOAD_BAND
    if lo <= wind_mph < hi and load_weight_lb > rules.WIND_HEAVY_LOAD_NO_TRAVEL_LB:
        level = _worst(level, RiskLevel.NO_TRAVEL)
    lo, hi = rules.WIND_VERY_HEAVY_LOAD_BAND
    if lo <= wind_mph < hi and load_weight_lb > rules.WIND_VERY_HEAVY_LOAD_SEVERE_LB:
        level = _worst(level, RiskLevel.SEVERE)
    return level


def classify_rain(rain_in_per_hr):
    return _classify(rain_in_per_hr, rules.RAIN_IN_PER_HR)


def classify_snow(snow_in_per_hr):
    return _classify(snow_in_per_hr, rules.SNOW_IN_PER_HR)


def overall_risk(condition_risks):
    """Worst known condition. If any input is missing and the worst known level is
    Low, the result is UNKNOWN: missing data must never read as safe."""
    levels = list(condition_risks.values())
    known = [lv for lv in levels if lv is not RiskLevel.UNKNOWN]
    if not known:
        return RiskLevel.UNKNOWN
    worst = _worst(*known)
    if len(known) < len(levels) and worst is RiskLevel.LOW:
        return RiskLevel.UNKNOWN
    return worst


def assess_values(wind_mph, rain_in_per_hr, snow_in_per_hr, load_weight_lb):
    """Returns (condition_risks, overall_risk, data_status) for raw weather values."""
    condition_risks = {
        "wind": classify_wind(wind_mph, load_weight_lb),
        "rain": classify_rain(rain_in_per_hr),
        "snow": classify_snow(snow_in_per_hr),
    }
    missing = [v for v in (wind_mph, rain_in_per_hr, snow_in_per_hr) if v is None]
    if len(missing) == 3:
        status = DataStatus.UNAVAILABLE
    elif missing:
        status = DataStatus.PARTIAL
    else:
        status = DataStatus.AVAILABLE
    return condition_risks, overall_risk(condition_risks), status


def assess_sample(sample, load_weight_lb):
    if sample is None:
        return assess_values(None, None, None, load_weight_lb)
    return assess_values(sample.wind_mph, sample.rain_in_per_hr, sample.snow_in_per_hr, load_weight_lb)
