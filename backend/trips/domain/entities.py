"""Typed value objects shared by the domain, services and response builders."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .enums import DataStatus, RiskLevel


@dataclass(frozen=True)
class Location:
    label: str
    latitude: float
    longitude: float


@dataclass(frozen=True)
class TripRequest:
    origin: Location
    destination: Location
    departure_at: datetime  # timezone-aware
    load_weight_lb: float
    checkpoint_interval_miles: int


@dataclass
class Route:
    id: str
    label: str
    coordinates: list  # [(lon, lat), ...]
    distance_m: float
    duration_s: float
    segment_durations_s: Optional[list] = None  # per geometry segment, when the provider supplies it


@dataclass(frozen=True)
class WeatherSample:
    """Normalised hourly weather. Any value may be None when the provider has no data."""

    forecast_time: datetime  # UTC hour used
    wind_mph: Optional[float]
    rain_in_per_hr: Optional[float]
    snow_in_per_hr: Optional[float]

    @property
    def is_complete(self):
        return None not in (self.wind_mph, self.rain_in_per_hr, self.snow_in_per_hr)


@dataclass
class HourlySeries:
    """Hourly forecast for one grid point, indexed by epoch seconds."""

    times: list
    wind_mph: list
    rain_in: list
    snow_in: list
    _index: dict = field(default_factory=dict, repr=False)

    def __post_init__(self):
        self._index = {t: i for i, t in enumerate(self.times)}

    def index_of(self, epoch_seconds):
        return self._index.get(epoch_seconds)

    def values_at(self, epoch_seconds):
        i = self._index.get(epoch_seconds)
        if i is None:
            return None
        return self.wind_mph[i], self.rain_in[i], self.snow_in[i]


@dataclass
class Checkpoint:
    id: str
    index: int
    distance_m: float
    latitude: float
    longitude: float
    eta: datetime
    segment_start_m: float  # route miles this checkpoint is responsible for
    segment_end_m: float
    weather: Optional[WeatherSample] = None
    condition_risks: dict = field(default_factory=dict)
    overall_risk: RiskLevel = RiskLevel.UNKNOWN
    data_status: DataStatus = DataStatus.UNAVAILABLE

    @property
    def segment_length_m(self):
        return self.segment_end_m - self.segment_start_m


@dataclass
class RiskSummary:
    miles_by_level: dict
    total_miles: float
    average_risk_score: Optional[float]

    def miles(self, level):
        return self.miles_by_level.get(level, 0.0)

    @property
    def severe_miles(self):
        return self.miles(RiskLevel.SEVERE)

    @property
    def high_miles(self):
        return self.miles(RiskLevel.HIGH)

    @property
    def no_travel_miles(self):
        return self.miles(RiskLevel.NO_TRAVEL)

    @property
    def unknown_miles(self):
        return self.miles(RiskLevel.UNKNOWN)

    @property
    def known_miles(self):
        return self.total_miles - self.unknown_miles

    @property
    def has_no_travel(self):
        return self.no_travel_miles > 0


@dataclass
class RouteAnalysis:
    route: Route
    checkpoints: list
    summary: RiskSummary
    eta: datetime
    rank: int = 0
    reason_codes: list = field(default_factory=list)
    explanation: str = ""
    is_recommended: bool = False


@dataclass
class Recommendation:
    route_id: Optional[str]
    reason_codes: list
    summary: str
    incomplete: bool = False
    all_routes_unsafe: bool = False


@dataclass
class CorridorPoint:
    latitude: float
    longitude: float
    wind_mph: list  # one value per forecast hour offset (None = unavailable)
    rain_in: list
    snow_in: list
    risk: list  # RiskLevel per hour offset


@dataclass
class Corridor:
    offset_hours: list
    times_utc: list  # ISO timestamps of the forecast hour used for each offset
    points: list


@dataclass
class AnalysisResult:
    status: str  # COMPLETE | PARTIAL
    request: TripRequest
    analyses: list
    recommendation: Recommendation
    corridor: Optional[Corridor]
    warnings: list
