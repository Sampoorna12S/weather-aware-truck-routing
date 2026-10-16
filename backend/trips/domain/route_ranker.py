"""Ranks route analyses and explains the result.

Order (lexicographic, never a weighted sum):
    1. Routes with no "No Travel" segment come first (product interpretation: the
       assessment's list has no exclusion step, so this is documented in the README)
    2. Fewest Severe miles
    3. Fewest High miles
    4. Lowest distance-weighted average risk
    5. Shortest travel time
    6. Provider order (deterministic tie-break)
"""
from .entities import Recommendation

_METRICS = (
    ("severe", "FEWER_SEVERE_MILES", lambda a: round(a.summary.severe_miles, 2), "Severe miles"),
    ("high", "FEWER_HIGH_MILES", lambda a: round(a.summary.high_miles, 2), "High-risk miles"),
    (
        "avg",
        "LOWER_AVERAGE_RISK",
        lambda a: round(a.summary.average_risk_score if a.summary.average_risk_score is not None else 0.0, 4),
        "average risk",
    ),
    ("time", "SHORTEST_TRAVEL_TIME", lambda a: int(a.route.duration_s), "travel time"),
)

_REASON_TEXT = {
    "ONLY_ROUTE_AVAILABLE": "the only route available",
    "AVOIDS_NO_TRAVEL": "avoids No Travel conditions that the alternatives contain",
    "FEWER_SEVERE_MILES": "fewer Severe miles than the alternatives",
    "FEWER_HIGH_MILES": "fewer High-risk miles than the alternatives",
    "LOWER_AVERAGE_RISK": "lowest average risk",
    "SHORTEST_TRAVEL_TIME": "shortest travel time",
    "TIED_ON_ALL_CRITERIA": "tied with the alternatives on every criterion; listed first by provider order",
}


def _sort_key(index, analysis):
    return (
        analysis.summary.has_no_travel,
        *(metric(analysis) for _, _, metric, _ in _METRICS),
        index,
    )


def _winning_reasons(best, others):
    if not others:
        return ["ONLY_ROUTE_AVAILABLE"]
    reasons = []
    if not best.summary.has_no_travel and all(o.summary.has_no_travel for o in others):
        reasons.append("AVOIDS_NO_TRAVEL")
    for _, code, metric, _ in _METRICS:
        if metric(best) < min(metric(o) for o in others):
            reasons.append(code)
    return reasons or ["TIED_ON_ALL_CRITERIA"]


def _explain_loser(analysis, best):
    if analysis.summary.has_no_travel and not best.summary.has_no_travel:
        return "Contains No Travel conditions under the supplied rules."
    for _, _, metric, label in _METRICS:
        diff = metric(analysis) - metric(best)
        if diff > 0:
            if label.endswith("miles"):
                return f"{diff:.0f} more {label.lower()} than {best.route.label}."
            return f"Higher {label} than {best.route.label}."
    return f"Tied with {best.route.label}; ranked lower by provider order."


def rank_routes(analyses):
    """Sorts `analyses` in place into ranked order and returns a Recommendation."""
    if not analyses:
        return Recommendation(None, [], "No routes to rank.")

    # Without any weather data there is nothing to rank on: never call a route safe.
    if all(a.summary.known_miles <= 0 for a in analyses):
        for rank, a in enumerate(analyses, start=1):
            a.rank = rank
            a.explanation = "Weather data was unavailable, so risk could not be evaluated."
        return Recommendation(
            route_id=None,
            reason_codes=["NO_WEATHER_DATA"],
            summary="Weather data was unavailable, so no route can be recommended.",
            incomplete=True,
        )

    order = sorted(range(len(analyses)), key=lambda i: _sort_key(i, analyses[i]))
    ranked = [analyses[i] for i in order]
    analyses[:] = ranked

    best, others = ranked[0], ranked[1:]
    reasons = _winning_reasons(best, others)
    for rank, a in enumerate(ranked, start=1):
        a.rank = rank
        a.is_recommended = a is best
    best.reason_codes = reasons
    best.explanation = "Recommended: " + "; ".join(_REASON_TEXT[r] for r in reasons) + "."
    for a in others:
        a.explanation = _explain_loser(a, best)

    all_unsafe = all(a.summary.has_no_travel for a in ranked)
    incomplete = any(a.summary.unknown_miles > 0 for a in ranked)
    if all_unsafe:
        summary = (
            f"No fully safe route was found: every option contains No Travel conditions. "
            f"{best.route.label} is the least risky comparison, not a safe recommendation."
        )
    else:
        summary = f"{best.route.label} selected using the required priority order."
    if incomplete:
        summary += " Some checkpoints have no forecast data, so this comparison is incomplete."
    return Recommendation(
        route_id=best.route.id,
        reason_codes=reasons,
        summary=summary,
        incomplete=incomplete,
        all_routes_unsafe=all_unsafe,
    )
