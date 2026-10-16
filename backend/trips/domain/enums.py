from enum import Enum


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"
    NO_TRAVEL = "NO_TRAVEL"
    UNKNOWN = "UNKNOWN"

    @property
    def rank(self):
        """Ordering used to pick the worst condition. UNKNOWN sorts below LOW."""
        return _RANK[self]

    @property
    def score(self):
        """Numeric score used for the distance-weighted average (None = not scored)."""
        return _SCORE.get(self)


_RANK = {
    RiskLevel.UNKNOWN: -1,
    RiskLevel.LOW: 0,
    RiskLevel.MODERATE: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.SEVERE: 3,
    RiskLevel.NO_TRAVEL: 4,
}

# Low=0, Moderate=1, High=2, Severe=3 per the plan; No Travel is scored 4 and
# additionally surfaced as a separate hard-stop flag. Unknown is never scored.
_SCORE = {
    RiskLevel.LOW: 0,
    RiskLevel.MODERATE: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.SEVERE: 3,
    RiskLevel.NO_TRAVEL: 4,
}


class DataStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"
