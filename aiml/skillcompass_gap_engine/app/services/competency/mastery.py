from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class BKTParameters:
    """Standard BKT parameters with lightweight provenance.

    Defaults are configurable, uncalibrated engineering starting values.
    They are not claimed as real-world SAMARTH learner parameters until fit
    and validated on real learner-response sequences.
    """

    p_l0: float = 0.30
    p_t: float = 0.10
    p_g: float = 0.20
    p_s: float = 0.10
    version: str = "default-uncalibrated-v1"
    source: str = "configured"

    def __post_init__(self):
        for name, val in [
            ("p_l0", self.p_l0),
            ("p_t", self.p_t),
            ("p_g", self.p_g),
            ("p_s", self.p_s),
        ]:
            if not (0.0 <= val <= 1.0):
                raise ValueError(f"{name}={val} must be in [0,1]")


BKTParams = BKTParameters


@dataclass
class AssessmentEvent:
    question_id: str
    competency_id: str
    difficulty: str  # retained as item metadata; standard BKT has no difficulty multiplier.
    correct: bool
    timestamp: datetime
    # False by default because a diagnostic assessment attempt does not
    # necessarily include instruction/feedback. Set True for practice or
    # tutoring events that are actual learning opportunities.
    learning_opportunity: bool = False


def bkt_observation_update(
    p_l_prev: float,
    correct: bool,
    params: BKTParameters,
) -> float:
    # Standard BKT observation update:
    # Corbett & Anderson (1994/1995), Knowledge Tracing; guess/slip posterior.
    if correct:
        numerator = p_l_prev * (1.0 - params.p_s)
        denominator = numerator + (1.0 - p_l_prev) * params.p_g
    else:
        numerator = p_l_prev * params.p_s
        denominator = numerator + (1.0 - p_l_prev) * (1.0 - params.p_g)

    if denominator <= 1e-12:
        return min(max(p_l_prev, 0.0), 1.0)
    return min(max(numerator / denominator, 0.0), 1.0)


def apply_learning_transition(p_l_observed: float, params: BKTParameters) -> float:
    # Standard BKT learning transition P(T) from unlearned to learned.
    # Apply only when event semantics indicate instruction/practice.
    p_l_next = p_l_observed + (1.0 - p_l_observed) * params.p_t
    return min(max(p_l_next, 0.0), 1.0)


def bkt_update(
    p_l_prev: float,
    correct: bool,
    params: BKTParameters,
    learning_opportunity: bool = False,
) -> float:
    posterior = bkt_observation_update(p_l_prev, correct, params)
    if learning_opportunity:
        return apply_learning_transition(posterior, params)
    return posterior


class MasteryEstimator:
    def __init__(self, params: Optional[BKTParameters] = None):
        self.params = params or BKTParameters()

    def estimate(self, events: List[AssessmentEvent], competency_id: str) -> float:
        relevant = sorted(
            [e for e in events if e.competency_id == competency_id],
            key=lambda e: e.timestamp,
        )
        mastery = self.params.p_l0
        for event in relevant:
            mastery = bkt_update(
                mastery,
                event.correct,
                self.params,
                learning_opportunity=event.learning_opportunity,
            )
        return mastery

    def estimate_on_5_point_scale(
        self,
        events: List[AssessmentEvent],
        competency_id: str,
    ) -> float:
        """Product display transform, not a calibrated psychometric scale."""
        return 1.0 + 4.0 * self.estimate(events, competency_id)
