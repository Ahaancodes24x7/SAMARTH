"""
Evidence freshness for the Competency State & Gap Engine.

Ebbinghaus-style forgetting research supports the general idea that
memory/performance changes over time, but it does not give this product a
universal mastery-decay constant. We therefore use a configurable
freshness curve to flag stale evidence for reassessment, not to directly
collapse mastery_probability toward incompetence.
"""

import math
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DecayParams:
    """
    half_life_days is the number of days after which evidence_freshness
    drops to 0.5. This is a product-policy default awaiting calibration,
    not a research-backed universal value for these competencies.
    """

    half_life_days: float = 60.0

    def __post_init__(self):
        if self.half_life_days <= 0:
            raise ValueError("half_life_days must be positive")

    @property
    def lambda_(self) -> float:
        return math.log(2.0) / self.half_life_days


def recency_factor(days_since_last_evidence: float, params: DecayParams = None) -> float:
    """
    evidence_freshness = exp(-lambda * days_since_last_evidence)

    Engineering freshness heuristic inspired by exponential forgetting
    curves. It informs confidence/reassessment, not mastery inference.
    """

    params = params or DecayParams()
    if days_since_last_evidence < 0:
        raise ValueError("days_since_last_evidence cannot be negative")
    return math.exp(-params.lambda_ * days_since_last_evidence)


def days_since(last_evidence_ts: datetime, now: datetime = None) -> float:
    now = now or datetime.utcnow()
    delta = now - last_evidence_ts
    return max(delta.total_seconds() / 86400.0, 0.0)


if __name__ == "__main__":
    params = DecayParams(half_life_days=60.0)
    for days in [1, 30, 60, 90, 180]:
        print(f"{days:>4} days since evidence -> evidence_freshness = {recency_factor(days, params):.3f}")
