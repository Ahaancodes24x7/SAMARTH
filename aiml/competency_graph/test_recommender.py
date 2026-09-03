from datetime import datetime, timedelta

import pytest

from aiml.competency_graph import graph_authoring
from aiml.competency_graph.graph_loader import GraphValidationError, build_graph
from aiml.competency_graph.graph_schema import EdgeType, GraphEdge
from aiml.competency_graph.recommender import (
    RecommendationInputError,
    recommend_upstream_competencies,
)
from aiml.skillcompass_gap_engine.app.services.competency.mastery import AssessmentEvent
from aiml.skillcompass_gap_engine.app.services.competency.state_engine import CompetencyStateEngine


NOW = datetime(2026, 9, 1, 12, 0, 0)


def gap(
    competency_id,
    gap_value,
    confidence=0.8,
    evidence_count=8,
    status="CONFIRMED_GAP",
    priority_weight=0.4,
):
    return {
        "competency_id": competency_id,
        "gap": gap_value,
        "confidence": confidence,
        "evidence_count": evidence_count,
        "status": status,
        "priority_weight": priority_weight,
    }


def event(qid, competency_id, correct, days_ago=0, difficulty="medium"):
    return AssessmentEvent(
        question_id=qid,
        competency_id=competency_id,
        difficulty=difficulty,
        correct=correct,
        timestamp=NOW - timedelta(days=days_ago),
        learning_opportunity=False,
    )


def ids(recommendations):
    return [item.competency_id for item in recommendations]


def test_direct_prerequisite_discovery():
    g = build_graph()
    ranking = recommend_upstream_competencies(g, [gap("sdg_indicators", 2.5)])
    assert "sampling" in ids(ranking)
    assert "survey_design" in ids(ranking)


def test_no_downstream_leakage():
    g = build_graph()
    ranking = recommend_upstream_competencies(g, [gap("sampling", 2.5)])
    assert "sdg_indicators" not in ids(ranking)


def test_severity_ranking():
    g = build_graph()
    ranking = recommend_upstream_competencies(
        g,
        [
            gap("sampling", 2.5, confidence=0.8),
            gap("survey_design", 0.5, confidence=0.8),
        ],
    )
    assert ids(ranking).index("sampling") < ids(ranking).index("survey_design")


def test_confidence_aware_cold_start_is_diagnostic_not_confirmed():
    g = build_graph()
    ranking = recommend_upstream_competencies(
        g,
        [gap("sdg_indicators", 3.0, confidence=0.0, evidence_count=0, status="UNCERTAIN_MORE_EVIDENCE")],
    )
    assert ranking[0].competency_id == "sdg_indicators"
    assert ranking[0].evidence_status == "DIAGNOSTIC_NEEDED"
    assert "sampling" not in ids(ranking)


def test_canonicalization():
    g = build_graph()
    ranking = recommend_upstream_competencies(g, [gap("python_basics", 2.0)])
    assert ranking[0].competency_id == "python"
    assert "python_basics" not in ids(ranking)
    assert "python_basics" not in g.nodes


def test_unknown_competency_rejection():
    g = build_graph()
    with pytest.raises(RecommendationInputError):
        recommend_upstream_competencies(g, [gap("made_up_competency", 2.0)])


def test_determinism():
    g = build_graph()
    gaps = [gap("sdg_indicators", 2.5), gap("sampling", 1.0)]
    first = recommend_upstream_competencies(g, gaps, role_id="district_stat_officer")
    second = recommend_upstream_competencies(g, gaps, role_id="district_stat_officer")
    assert first == second


def test_role_relevance():
    g = build_graph()
    ranking = recommend_upstream_competencies(g, [gap("sdg_indicators", 2.5)], role_id="data_analyst")
    by_id = {item.competency_id: item for item in ranking}
    assert by_id["sampling"].role_relevant is True
    assert by_id["survey_design"].role_relevant is False


def test_multi_hop_prerequisite_reasoning():
    nodes = [
        node
        for node in graph_authoring.all_nodes()
        if node.node_id in {"sampling", "metadata_standards", "sdg_indicators"}
    ]
    edges = [
        GraphEdge(
            "sampling",
            "metadata_standards",
            EdgeType.PREREQUISITE_OF,
            authored_by="test",
            rationale="Sampling before metadata standards in this test fixture.",
        ),
        GraphEdge(
            "metadata_standards",
            "sdg_indicators",
            EdgeType.PREREQUISITE_OF,
            authored_by="test",
            rationale="Metadata standards before SDG indicators in this test fixture.",
        ),
    ]
    g = build_graph(nodes=nodes, edges=edges)
    ranking = recommend_upstream_competencies(g, [gap("sdg_indicators", 2.5)])
    by_id = {item.competency_id: item for item in ranking}
    assert by_id["metadata_standards"].graph_distance == 1
    assert by_id["sampling"].graph_distance == 2
    assert ids(ranking).index("metadata_standards") < ids(ranking).index("sampling")


def test_cycle_protection():
    nodes = [
        node
        for node in graph_authoring.all_nodes()
        if node.node_id in {"sampling", "sdg_indicators"}
    ]
    edges = [
        GraphEdge("sampling", "sdg_indicators", EdgeType.PREREQUISITE_OF, authored_by="test", rationale="test edge"),
        GraphEdge("sdg_indicators", "sampling", EdgeType.PREREQUISITE_OF, authored_by="test", rationale="cycle edge"),
    ]
    with pytest.raises(GraphValidationError):
        build_graph(nodes=nodes, edges=edges)


def test_gap_engine_to_graph_recommendation_integration():
    required = {"sdg_indicators": 4.5, "sampling": 4.0, "survey_design": 4.0}
    events = [
        *[
            event(f"sdg{i}", "sdg_indicators", False, difficulty=["easy", "medium", "hard"][i % 3])
            for i in range(18)
        ],
        *[event(f"s{i}", "sampling", True) for i in range(8)],
        *[event(f"q{i}", "survey_design", True) for i in range(8)],
    ]
    state = CompetencyStateEngine().compute_state("synthetic_learner", required, events, now=NOW)
    seed_export = state.to_ppr_seed_export()
    ranking = recommend_upstream_competencies(
        build_graph(),
        seed_export["open_gaps"] + seed_export["diagnostic_gaps"],
        role_id="district_stat_officer",
    )
    assert seed_export["open_gaps"]
    assert "sampling" in ids(ranking)
    assert "survey_design" in ids(ranking)
