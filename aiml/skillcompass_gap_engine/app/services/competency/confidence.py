from dataclasses import dataclass
from typing import List
import math

from .mastery import AssessmentEvent


@dataclass(frozen=True)
class ConfidenceWeights:
    w_volume: float = 0.35
    w_diversity: float = 0.20
    w_consistency: float = 0.25
    w_difficulty_cov: float = 0.20

    def __post_init__(self):
        total = self.w_volume + self.w_diversity + self.w_consistency + self.w_difficulty_cov
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"ConfidenceWeights must sum to 1.0, got {total}")


_DIFFICULTY_LEVELS = {"easy", "medium", "hard"}


def _volume_score(n: int, saturation_point: int = 15) -> float:
    if n <= 0:
        return 0.0
    return 1.0 - math.exp(-n / saturation_point)


def _diversity_score(events: List[AssessmentEvent]) -> float:
    if not events:
        return 0.0
    distinct_questions = len({e.question_id for e in events})
    return distinct_questions / len(events)


def _consistency_score(events: List[AssessmentEvent]) -> float:
    if len(events) < 2:
        return 0.0
    ordered = sorted(events, key=lambda e: e.timestamp)
    signal = [1.0 if e.correct else 0.0 for e in ordered]
    mean = sum(signal) / len(signal)
    variance = sum((x - mean) ** 2 for x in signal) / len(signal)
    normalized_variance = min(variance / 0.25, 1.0)
    flips = sum(1 for a, b in zip(signal, signal[1:]) if a != b)
    flip_rate = flips / (len(signal) - 1)
    # Engineering heuristic for evidence confidence. Not claimed as a
    # literature-derived psychometric measure: sequence stability matters,
    # so 1111100000 is treated differently from 1010101010.
    return max(0.0, min(1.0, 0.5 * (1.0 - normalized_variance) + 0.5 * (1.0 - flip_rate)))


def _difficulty_coverage_score(events: List[AssessmentEvent]) -> float:
    if not events:
        return 0.0
    seen = {e.difficulty for e in events if e.difficulty in _DIFFICULTY_LEVELS}
    return len(seen) / len(_DIFFICULTY_LEVELS)


def compute_confidence(
    events: List[AssessmentEvent],
    competency_id: str,
    weights: ConfidenceWeights = None,
) -> float:
    weights = weights or ConfidenceWeights()
    relevant = [e for e in events if e.competency_id == competency_id]

    confidence = (
        weights.w_volume * _volume_score(len(relevant))
        + weights.w_diversity * _diversity_score(relevant)
        + weights.w_consistency * _consistency_score(relevant)
        + weights.w_difficulty_cov * _difficulty_coverage_score(relevant)
    )
    return round(min(max(confidence, 0.0), 1.0), 4)


def confidence_breakdown(
    events: List[AssessmentEvent],
    competency_id: str,
    weights: ConfidenceWeights = None,
) -> dict:
    weights = weights or ConfidenceWeights()
    relevant = [e for e in events if e.competency_id == competency_id]
    return {
        "evidence_count": len(relevant),
        "volume_score": round(_volume_score(len(relevant)), 4),
        "diversity_score": round(_diversity_score(relevant), 4),
        "consistency_score": round(_consistency_score(relevant), 4),
        "difficulty_coverage_score": round(_difficulty_coverage_score(relevant), 4),
        "weights": weights.__dict__,
        "final_confidence": compute_confidence(events, competency_id, weights),
    }
