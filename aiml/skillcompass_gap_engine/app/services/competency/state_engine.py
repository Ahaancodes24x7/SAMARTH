"""
Competency State Engine — the orchestrator for this module.

RESPONSIBILITY BOUNDARY (see PART 1 of the design doc):
  This module IS responsible for: turning raw evidence (role requirements +
  assessment history) into a per-competency state (mastery, confidence,
  recency, gap, priority) and exposing it as explainable JSON.

  This module is NOT responsible for: generating recommendations (that's
  the future PPR/graph engine — this module only EXPORTS gap nodes in the
  shape that engine will consume), generating MCQs (RAG/LLM engine, not
  here), rendering any UI, or deciding WHICH courses exist.

INPUT:  a learner_id, their role's required_levels dict, and their full
        AssessmentEvent history.
OUTPUT: a CompetencyState object per competency, an explainable JSON
        payload, and a PPR-seed-node export.
"""

from dataclasses import dataclass, asdict
from typing import Dict, List
from datetime import datetime

from .mastery import AssessmentEvent, BKTParams
from .gap import compute_gap_for_competency, CompetencyGapResult
from .confidence import ConfidenceWeights
from .recency import DecayParams


@dataclass
class LearnerCompetencyState:
    learner_id: str
    generated_at: str
    competencies: List[CompetencyGapResult]

    def to_explainable_json(self) -> dict:
        """
        Matches (and extends) the explanation object shape requested in
        PART 15 of the design brief. Every field here is DETERMINISTIC —
        derived from the formulas in mastery.py / confidence.py /
        recency.py / gap.py. Nothing here is an LLM output. This is the
        object the frontend's "Why is this my highest-priority gap?"
        panel renders directly.
        """
        return {
            "learner_id": self.learner_id,
            "generated_at": self.generated_at,
            "competencies": [
                {
                    "competency": c.competency_id,
                    "required_level": c.required_level,
                    "mastery_probability": c.mastery_probability,
                    "display_level": c.display_level,
                    "evidence_confidence": c.evidence_confidence,
                    "evidence_freshness": c.evidence_freshness,
                    "raw_mastery": c.raw_mastery,
                    "confidence": c.confidence,
                    "recency_factor": c.recency_factor,
                    "effective_level": c.effective_mastery,
                    "gap": c.gap,
                    "priority_weight": c.priority_weight,
                    "needs_more_evidence": c.needs_more_evidence,
                    "needs_reassessment": c.needs_reassessment,
                    "evidence_count": c.evidence_count,
                    "last_demonstrated": c.last_demonstrated.isoformat() if c.last_demonstrated else None,
                    "status": c.status,
                    "bkt_parameter_version": c.bkt_parameter_version,
                    "reason": c.reason,
                }
                for c in self.competencies
            ],
        }

    def to_ppr_seed_export(self) -> dict:
        """
        PART 16 — output contract for the (not-yet-built) PPR/graph
        recommendation engine. This module does NOT run PageRank. It only
        exports open-gap nodes with a normalized seed weight; the future
        graph engine consumes this dict as its `personalization` input to
        networkx.pagerank(...). Only competencies with a positive gap and
        sufficient confidence to act on are included as seeds — a gap
        flagged `needs_more_evidence` is deliberately excluded from the
        seed set until more evidence exists, so the recommender doesn't
        propagate priority from a shaky signal.
        """
        seeds = [
            {
                "competency_id": c.competency_id,
                "gap": c.gap,
                "confidence": c.confidence,
                "priority_weight": c.priority_weight,
            }
            for c in self.competencies
            if c.status == "CONFIRMED_GAP" and c.priority_weight > 0
        ]
        return {"learner_id": self.learner_id, "open_gaps": seeds}

    def ranked_gaps(self) -> List[CompetencyGapResult]:
        """Highest priority_weight first — this IS the ranking shown as
        'your highest-priority gap' in the demo, computed deterministically,
        no LLM involved."""
        return sorted(self.competencies, key=lambda c: c.priority_weight, reverse=True)


class CompetencyStateEngine:
    def __init__(
        self,
        bkt_params: BKTParams = None,
        confidence_weights: ConfidenceWeights = None,
        decay_params: DecayParams = None,
    ):
        self.bkt_params = bkt_params or BKTParams()
        self.confidence_weights = confidence_weights or ConfidenceWeights()
        self.decay_params = decay_params or DecayParams()

    def compute_state(
        self,
        learner_id: str,
        required_levels: Dict[str, float],
        events: List[AssessmentEvent],
        now: datetime = None,
    ) -> LearnerCompetencyState:
        now = now or datetime.utcnow()
        results = [
            compute_gap_for_competency(
                events=events,
                competency_id=comp_id,
                required_level=required_level,
                now=now,
                bkt_params=self.bkt_params,
                confidence_weights=self.confidence_weights,
                decay_params=self.decay_params,
            )
            for comp_id, required_level in required_levels.items()
        ]
        return LearnerCompetencyState(
            learner_id=learner_id,
            generated_at=now.isoformat(),
            competencies=results,
        )
