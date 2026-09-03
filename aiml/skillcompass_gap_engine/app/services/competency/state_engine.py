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
from pathlib import Path
import sys
from typing import Dict, List
from datetime import datetime

from .mastery import AssessmentEvent, BKTParams
from .gap import compute_gap_for_competency, CompetencyGapResult
from .confidence import ConfidenceWeights
from .recency import DecayParams


def _resolve_graph_competency_id(competency_id: str) -> str:
    try:
        from aiml.competency_graph.graph_loader import resolve_competency_id
    except ModuleNotFoundError:
        repo_root = Path(__file__).resolve().parents[5]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from aiml.competency_graph.graph_loader import resolve_competency_id

    return resolve_competency_id(competency_id)


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
        seeds = []
        diagnostic_gaps = []
        seen = set()
        for c in self.competencies:
            canonical_id = _resolve_graph_competency_id(c.competency_id)
            if canonical_id in seen:
                raise ValueError(f"Duplicate competency_id in PPR seed export: {canonical_id!r}")
            seen.add(canonical_id)
            item = {
                "competency_id": canonical_id,
                "gap": c.gap,
                "confidence": c.confidence,
                "priority_weight": c.priority_weight,
                "evidence_count": c.evidence_count,
                "status": c.status,
            }
            if canonical_id != c.competency_id:
                item["legacy_competency_id"] = c.competency_id
            if c.gap > 0 and c.status == "CONFIRMED_GAP" and c.priority_weight > 0:
                seeds.append(item)
            elif c.gap > 0 and (c.evidence_count == 0 or c.needs_more_evidence):
                diagnostic_gaps.append(item)
        return {
            "learner_id": self.learner_id,
            "open_gaps": seeds,
            "diagnostic_gaps": diagnostic_gaps,
        }

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
