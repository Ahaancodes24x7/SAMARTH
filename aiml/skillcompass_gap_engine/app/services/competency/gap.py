from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from .confidence import ConfidenceWeights, compute_confidence
from .mastery import AssessmentEvent, BKTParams, MasteryEstimator
from .recency import DecayParams, days_since, recency_factor


LOW_CONFIDENCE_THRESHOLD = 0.35  # product-policy default, not psychometric validation.
STALE_EVIDENCE_FRESHNESS_THRESHOLD = 0.35  # product-policy default for reassessment.


@dataclass
class CompetencyGapResult:
    competency_id: str
    required_level: float
    mastery_probability: float
    display_level: float
    evidence_confidence: float
    evidence_freshness: float
    gap: float
    priority_weight: float
    needs_more_evidence: bool
    needs_reassessment: bool
    evidence_count: int
    last_demonstrated: Optional[datetime]
    status: str
    bkt_parameter_version: str
    reason: str
    # Backward-compatible field names for existing API/frontend callers.
    raw_mastery: float
    confidence: float
    recency_factor: float
    effective_mastery: float


def compute_gap_for_competency(
    events: List[AssessmentEvent],
    competency_id: str,
    required_level: float,
    now: datetime = None,
    bkt_params: BKTParams = None,
    confidence_weights: ConfidenceWeights = None,
    decay_params: DecayParams = None,
) -> CompetencyGapResult:
    now = now or datetime.utcnow()
    params = bkt_params or BKTParams()
    relevant = [e for e in events if e.competency_id == competency_id]

    estimator = MasteryEstimator(params)
    mastery_probability = estimator.estimate(events, competency_id)
    # Product display transform only; not a calibrated 1-5 proficiency scale.
    display_level = 1.0 + 4.0 * mastery_probability

    evidence_confidence = compute_confidence(events, competency_id, confidence_weights)

    if relevant:
        last_ts = max(e.timestamp for e in relevant)
        freshness = recency_factor(days_since(last_ts, now), decay_params)
    else:
        last_ts = None
        freshness = 1.0

    gap = required_level - display_level
    needs_reassessment = bool(relevant and freshness < STALE_EVIDENCE_FRESHNESS_THRESHOLD)
    needs_more_evidence = (not relevant) or (
        gap > 0 and evidence_confidence < LOW_CONFIDENCE_THRESHOLD
    )

    if needs_reassessment:
        status = "REASSESSMENT_REQUIRED"
    elif needs_more_evidence:
        status = "UNCERTAIN_MORE_EVIDENCE"
    elif gap > 0:
        status = "CONFIRMED_GAP"
    else:
        status = "NO_GAP"

    normalized_gap = max(gap, 0.0) / 4.0
    if status == "CONFIRMED_GAP":
        priority_weight = round(normalized_gap * evidence_confidence, 4)
    else:
        priority_weight = 0.0

    if not relevant:
        reason = (
            "No assessment evidence yet; mastery uses the configured BKT prior. "
            "Recommend diagnostic assessment before learning remediation."
        )
    elif needs_reassessment:
        reason = (
            f"Evidence is stale (freshness {freshness:.2f}); reassess before "
            "treating this as a current learning gap."
        )
    elif needs_more_evidence:
        reason = (
            f"Estimated display level {display_level:.2f} is below required "
            f"{required_level}, but evidence confidence is low ({evidence_confidence:.2f})."
        )
    elif gap > 0:
        reason = (
            f"Assessment evidence indicates a confirmed gap: display level "
            f"{display_level:.2f} vs required {required_level}."
        )
    else:
        reason = "Evidence indicates the learner meets or exceeds the role-required level."

    return CompetencyGapResult(
        competency_id=competency_id,
        required_level=required_level,
        mastery_probability=round(mastery_probability, 4),
        display_level=round(display_level, 4),
        evidence_confidence=evidence_confidence,
        evidence_freshness=round(freshness, 4),
        gap=round(gap, 4),
        priority_weight=priority_weight,
        needs_more_evidence=needs_more_evidence,
        needs_reassessment=needs_reassessment,
        evidence_count=len(relevant),
        last_demonstrated=last_ts,
        status=status,
        bkt_parameter_version=params.version,
        reason=reason,
        raw_mastery=round(display_level, 4),
        confidence=evidence_confidence,
        recency_factor=round(freshness, 4),
        effective_mastery=round(display_level, 4),
    )
