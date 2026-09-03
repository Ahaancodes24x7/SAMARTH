"""Deterministic upstream graph recommendations over the competency graph."""

from dataclasses import dataclass
from math import isfinite
from typing import Dict, Iterable, List, Optional

import networkx as nx

from .graph_loader import (
    GraphValidationError,
    canonicalize_gap_export,
    resolve_competency_id,
    role_required_competencies,
)
from .graph_schema import EdgeType, NodeType


class RecommendationInputError(ValueError):
    pass


@dataclass(frozen=True)
class RecommendationConfig:
    severity_weight: float = 1.0
    graph_weight: float = 1.0
    confidence_weight: float = 1.0
    role_relevance_weight: float = 1.0
    gap_scale: float = 4.0
    damping: float = 0.85
    max_hops: int = 3

    def __post_init__(self):
        for name, value in self.__dict__.items():
            if not isfinite(value):
                raise RecommendationInputError(f"{name} must be finite.")
        if self.gap_scale <= 0:
            raise RecommendationInputError("gap_scale must be positive.")
        if not 0 < self.damping < 1:
            raise RecommendationInputError("damping must be between 0 and 1.")
        if self.max_hops < 0:
            raise RecommendationInputError("max_hops must be non-negative.")


@dataclass(frozen=True)
class Recommendation:
    competency_id: str
    score: float
    source_gap: str
    graph_distance: int
    path: List[str]
    confidence: float
    evidence_count: int
    evidence_status: str
    role_relevant: bool
    reason: str


def recommend_upstream_competencies(
    g: nx.DiGraph,
    gaps: Iterable[Dict],
    role_id: Optional[str] = None,
    config: RecommendationConfig = None,
) -> List[Recommendation]:
    """
    Rank direct gaps and upstream prerequisite candidates.

    PREREQUISITE_OF means A -> B where A is foundational before B. For upstream
    discovery, PageRank runs on the reversed prerequisite graph, so a seed on B
    can flow to A.
    """
    config = config or RecommendationConfig()
    validated_gaps = _validate_gap_inputs(gaps)
    if not validated_gaps:
        return []

    role_required = set()
    if role_id is not None:
        try:
            role_required = set(role_required_competencies(g, role_id))
        except GraphValidationError as exc:
            raise RecommendationInputError(str(exc)) from exc

    prereq_reverse = _reversed_prerequisite_graph(g)
    personalization = _personalization_vector(prereq_reverse, validated_gaps, config)
    pagerank = (
        nx.pagerank(
            prereq_reverse,
            alpha=config.damping,
            personalization=personalization,
            weight="weight",
        )
        if personalization
        else {node: 0.0 for node in prereq_reverse.nodes}
    )

    candidates: Dict[str, Recommendation] = {}
    for gap in validated_gaps:
        source_id = gap["competency_id"]
        direct_status = _evidence_status(gap)
        _upsert_candidate(
            candidates,
            _build_recommendation(
                candidate_id=source_id,
                source_gap=source_id,
                path=[source_id],
                gap=gap,
                pagerank=pagerank.get(source_id, 0.0),
                role_required=role_required,
                config=config,
                evidence_status=direct_status,
                reason=f"Direct learner gap in {source_id}.",
            ),
        )

        if direct_status != "CONFIRMED_GAP":
            continue

        for candidate_id in nx.single_source_shortest_path_length(
            prereq_reverse, source_id, cutoff=config.max_hops
        ):
            if candidate_id == source_id:
                continue
            if g.nodes[candidate_id].get("node_type") != NodeType.COMPETENCY.value:
                continue
            path = nx.shortest_path(prereq_reverse, source_id, candidate_id)
            _upsert_candidate(
                candidates,
                _build_recommendation(
                    candidate_id=candidate_id,
                    source_gap=source_id,
                    path=path,
                    gap=gap,
                    pagerank=pagerank.get(candidate_id, 0.0),
                    role_required=role_required,
                    config=config,
                    evidence_status="UPSTREAM_PREREQUISITE",
                    reason=(
                        f"{candidate_id} is an upstream prerequisite for "
                        f"confirmed gap {source_id} via {' <- '.join(path)}."
                    ),
                ),
            )

    return sorted(
        candidates.values(),
        key=lambda item: (
            -item.score,
            item.graph_distance,
            item.competency_id,
            item.source_gap,
        ),
    )


def _validate_gap_inputs(gaps: Iterable[Dict]) -> List[Dict]:
    try:
        canonicalized = canonicalize_gap_export(gaps)
    except GraphValidationError as exc:
        raise RecommendationInputError(str(exc)) from exc

    validated = []
    for gap in canonicalized:
        competency_id = resolve_competency_id(gap["competency_id"])
        gap_value = _finite_number(gap.get("gap"), "gap")
        confidence = _finite_number(gap.get("confidence", 0.0), "confidence")
        priority_weight = _finite_number(gap.get("priority_weight", 0.0), "priority_weight")
        evidence_count = gap.get("evidence_count", 0)
        if gap_value < 0:
            raise RecommendationInputError("gap must not be negative.")
        if not 0 <= confidence <= 1:
            raise RecommendationInputError("confidence must be between 0 and 1.")
        if priority_weight < 0:
            raise RecommendationInputError("priority_weight must not be negative.")
        if not isinstance(evidence_count, int) or evidence_count < 0:
            raise RecommendationInputError("evidence_count must be a non-negative integer.")
        if gap_value == 0:
            continue
        item = dict(gap)
        item["competency_id"] = competency_id
        item["gap"] = gap_value
        item["confidence"] = confidence
        item["priority_weight"] = priority_weight
        item["evidence_count"] = evidence_count
        validated.append(item)
    return validated


def _finite_number(value, field_name: str) -> float:
    if not isinstance(value, (int, float)) or not isfinite(value):
        raise RecommendationInputError(f"{field_name} must be a finite number.")
    return float(value)


def _reversed_prerequisite_graph(g: nx.DiGraph) -> nx.DiGraph:
    reverse = nx.DiGraph()
    for node_id, data in g.nodes(data=True):
        if data.get("node_type") == NodeType.COMPETENCY.value:
            reverse.add_node(node_id)
    for source, target, data in g.edges(data=True):
        if data.get("edge_type") == EdgeType.PREREQUISITE_OF.value:
            reverse.add_edge(target, source, weight=data.get("weight", 1.0))
    return reverse


def _personalization_vector(
    graph: nx.DiGraph,
    gaps: List[Dict],
    config: RecommendationConfig,
) -> Dict[str, float]:
    seeds = {}
    for gap in gaps:
        if _evidence_status(gap) != "CONFIRMED_GAP":
            continue
        severity = min(gap["gap"] / config.gap_scale, 1.0)
        seed_weight = severity * max(gap["confidence"], 0.0)
        if seed_weight > 0:
            seeds[gap["competency_id"]] = seed_weight
    total = sum(seeds.values())
    if total <= 0:
        return {}
    return {node: seeds.get(node, 0.0) / total for node in graph.nodes}


def _evidence_status(gap: Dict) -> str:
    status = gap.get("status")
    if status == "CONFIRMED_GAP":
        return "CONFIRMED_GAP"
    if gap["confidence"] == 0 and gap["evidence_count"] == 0:
        return "DIAGNOSTIC_NEEDED"
    if status:
        return str(status)
    return "CONFIRMED_GAP" if gap["confidence"] > 0 else "UNCERTAIN"


def _build_recommendation(
    candidate_id: str,
    source_gap: str,
    path: List[str],
    gap: Dict,
    pagerank: float,
    role_required: set,
    config: RecommendationConfig,
    evidence_status: str,
    reason: str,
) -> Recommendation:
    severity = min(gap["gap"] / config.gap_scale, 1.0)
    role_relevant = candidate_id in role_required if role_required else False
    role_score = 1.0 if role_relevant else 0.0
    confidence = gap["confidence"]
    if evidence_status == "DIAGNOSTIC_NEEDED":
        confidence_score = 0.0
    elif evidence_status == "UPSTREAM_PREREQUISITE":
        confidence_score = confidence
    else:
        confidence_score = confidence

    raw_score = (
        config.severity_weight * severity
        + config.graph_weight * pagerank
        + config.confidence_weight * confidence_score
        + config.role_relevance_weight * role_score
    )
    return Recommendation(
        competency_id=candidate_id,
        score=round(raw_score, 6),
        source_gap=source_gap,
        graph_distance=len(path) - 1,
        path=path,
        confidence=confidence,
        evidence_count=gap["evidence_count"],
        evidence_status=evidence_status,
        role_relevant=role_relevant,
        reason=reason,
    )


def _upsert_candidate(candidates: Dict[str, Recommendation], candidate: Recommendation) -> None:
    existing = candidates.get(candidate.competency_id)
    if existing is None or (
        candidate.score,
        -candidate.graph_distance,
        candidate.source_gap,
    ) > (
        existing.score,
        -existing.graph_distance,
        existing.source_gap,
    ):
        candidates[candidate.competency_id] = candidate
