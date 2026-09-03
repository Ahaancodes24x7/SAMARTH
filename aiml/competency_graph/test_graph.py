"""
Tests for aiml/competency_graph/.
"""

import networkx as nx
import pytest

from aiml.competency_graph import graph_authoring
from aiml.competency_graph.graph_loader import (
    GraphValidationError,
    build_graph,
    canonical_competency_id,
    canonicalize_gap_export,
    competency_prerequisites_of,
    competency_skills,
    role_required_competencies,
)
from aiml.competency_graph.graph_schema import EdgeType, GraphEdge, GraphNode, NodeType


PS_26101_COMPETENCY_IDS = {
    "survey_design",
    "sampling",
    "national_accounts",
    "price_statistics",
    "labour_statistics",
    "agricultural_statistics",
    "industrial_statistics",
    "sdg_indicators",
    "metadata_standards",
    "data_quality_frameworks",
    "python",
    "r",
    "sql",
    "stata",
    "spss",
    "sas",
    "gis",
    "data_visualization",
    "ai_ml",
    "cloud_computing",
    "apis",
    "open_data",
    "cybersecurity",
    "data_privacy",
    "digital_signatures",
    "government_cloud",
    "digital_public_infrastructure",
    "leadership",
    "communication",
    "project_management",
    "ethics",
    "decision_making",
    "change_management",
}


class TestSchemaValidation:
    def test_prerequisite_edge_without_rationale_raises(self):
        with pytest.raises(ValueError):
            GraphEdge("a", "b", EdgeType.PREREQUISITE_OF)

    def test_requires_edge_without_rationale_is_fine(self):
        edge = GraphEdge("role_x", "comp_y", EdgeType.REQUIRES)
        assert edge.rationale is None

    def test_default_edge_weight_is_documented_uniform_value(self):
        edge = GraphEdge("a", "b", EdgeType.REQUIRES)
        assert edge.weight == 1.0

    def test_invalid_node_id_raises(self):
        with pytest.raises(ValueError):
            GraphNode("Bad ID", NodeType.COMPETENCY, "Bad", domain="technical")

    def test_invalid_weight_raises(self):
        with pytest.raises(ValueError):
            GraphEdge("a", "b", EdgeType.REQUIRES, weight=0.0)


class TestGraphAuthoring:
    def test_competency_registry_is_complete_ps_26101_vocabulary(self):
        actual = {n.node_id for n in graph_authoring.COMPETENCIES}
        assert actual == PS_26101_COMPETENCY_IDS
        assert len(actual) == 33

    def test_competency_nodes_carry_required_registry_metadata(self):
        for node in graph_authoring.COMPETENCIES:
            assert node.source == graph_authoring.PS_26101_SOURCE
            assert node.source_reference
            assert node.status == "active"
            assert node.display_name
            assert node.domain in {
                "statistical",
                "technical",
                "digital_governance",
                "behavioural_managerial",
            }

    def test_legacy_gap_engine_ids_have_explicit_aliases(self):
        assert graph_authoring.COMPETENCY_ID_ALIASES == {
            "sdg_indicator_estimation": "sdg_indicators",
            "data_quality": "data_quality_frameworks",
            "python_basics": "python",
            "gis_fundamentals": "gis",
        }

    def test_roles_are_labelled_mvp_archetypes(self):
        for role in graph_authoring.ROLES:
            assert role.source == graph_authoring.MVP_ROLE_SOURCE
            assert "not an exhaustive PS 26101 job-title list" in role.source_reference

    def test_role_requirement_edges_are_not_labelled_as_ps_official(self):
        for edge in graph_authoring.ROLE_REQUIRES_EDGES:
            assert edge.authored_by == graph_authoring.MVP_ROLE_MAPPING_SOURCE

    def test_all_authored_prerequisite_edges_have_rationale(self):
        for edge in graph_authoring.PREREQUISITE_EDGES:
            assert edge.rationale and len(edge.rationale) > 20

    def test_no_duplicate_node_ids(self):
        ids = [n.node_id for n in graph_authoring.all_nodes()]
        assert len(ids) == len(set(ids))

    def test_skill_decomposition_has_honest_representative_coverage(self):
        g = build_graph()
        decomposed = {
            "sampling",
            "survey_design",
            "sdg_indicators",
            "data_quality_frameworks",
            "python",
            "gis",
            "data_visualization",
            "ai_ml",
        }
        for competency_id in decomposed:
            skills = competency_skills(g, competency_id)
            assert 2 <= len(skills) <= 4
        assert competency_skills(g, "national_accounts") == []


class TestGraphLoader:
    def test_builds_without_error(self):
        g = build_graph()
        assert g.number_of_nodes() == 68
        assert g.number_of_edges() > 0

    def test_edge_referencing_unknown_node_raises(self):
        nodes = [GraphNode("a", NodeType.COMPETENCY, "A", domain="technical")]
        edges = [GraphEdge("a", "nonexistent", EdgeType.REQUIRES)]
        with pytest.raises(GraphValidationError):
            build_graph(nodes, edges)

    def test_duplicate_edge_raises(self):
        nodes = [
            GraphNode("role_a", NodeType.ROLE, "Role A", source="test"),
            GraphNode("sampling", NodeType.COMPETENCY, "Sampling", domain="statistical", source="test"),
        ]
        edges = [
            GraphEdge("role_a", "sampling", EdgeType.REQUIRES),
            GraphEdge("role_a", "sampling", EdgeType.REQUIRES),
        ]
        with pytest.raises(GraphValidationError):
            build_graph(nodes, edges)

    def test_invalid_edge_endpoint_types_raise(self):
        nodes = [
            GraphNode("role_a", NodeType.ROLE, "Role A", source="test"),
            GraphNode("sampling", NodeType.COMPETENCY, "Sampling", domain="statistical", source="test"),
        ]
        edges = [
            GraphEdge("role_a", "sampling", EdgeType.PREREQUISITE_OF, rationale="invalid type fixture"),
        ]
        with pytest.raises(GraphValidationError):
            build_graph(nodes, edges)

    def test_prerequisite_cycle_is_rejected(self):
        nodes = [
            GraphNode("a", NodeType.COMPETENCY, "A", domain="technical"),
            GraphNode("b", NodeType.COMPETENCY, "B", domain="technical"),
        ]
        edges = [
            GraphEdge("a", "b", EdgeType.PREREQUISITE_OF, rationale="a before b, test fixture"),
            GraphEdge("b", "a", EdgeType.PREREQUISITE_OF, rationale="b before a, test fixture creates a cycle"),
        ]
        with pytest.raises(GraphValidationError):
            build_graph(nodes, edges)

    def test_the_real_authored_graph_is_acyclic(self):
        g = build_graph()
        prereq_edges = [
            (u, v) for u, v, d in g.edges(data=True)
            if d.get("edge_type") == EdgeType.PREREQUISITE_OF.value
        ]
        sub = nx.DiGraph()
        sub.add_nodes_from(g.nodes())
        sub.add_edges_from(prereq_edges)
        assert nx.is_directed_acyclic_graph(sub)

    def test_sdg_indicators_has_expected_curated_prerequisites(self):
        g = build_graph()
        prereqs = set(competency_prerequisites_of(g, "sdg_indicators"))
        assert prereqs == {"sampling", "survey_design"}

    def test_legacy_sdg_indicator_id_resolves_to_same_prerequisites(self):
        g = build_graph()
        prereqs = set(competency_prerequisites_of(g, "sdg_indicator_estimation"))
        assert prereqs == {"sampling", "survey_design"}

    def test_district_stat_officer_required_competencies_are_canonical(self):
        g = build_graph()
        required = set(role_required_competencies(g, "district_stat_officer"))
        assert required == {
            "sampling",
            "survey_design",
            "sdg_indicators",
            "data_quality_frameworks",
            "python",
            "gis",
        }

    def test_competency_with_no_prerequisites_returns_empty_list(self):
        g = build_graph()
        assert competency_prerequisites_of(g, "sampling") == []

    def test_gap_engine_legacy_seed_ids_can_be_canonicalized(self):
        assert canonical_competency_id("python_basics") == "python"
        export = canonicalize_gap_export([
            {"competency_id": "python_basics", "gap": 1.0},
            {"competency_id": "sampling", "gap": 2.0},
        ])
        assert export == [
            {"competency_id": "python", "gap": 1.0, "legacy_competency_id": "python_basics"},
            {"competency_id": "sampling", "gap": 2.0},
        ]

    def test_unknown_competency_id_is_rejected(self):
        g = build_graph()
        with pytest.raises(GraphValidationError):
            competency_prerequisites_of(g, "made_up_competency")
