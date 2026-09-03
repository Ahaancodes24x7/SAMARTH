"""Loads and validates the authored competency graph."""

from typing import Dict, Iterable, List

import networkx as nx

from . import graph_authoring
from .graph_schema import EdgeType, GraphEdge, GraphNode, NodeType


class GraphValidationError(ValueError):
    pass


def _canonical_competency_ids() -> set:
    return {node.node_id for node in graph_authoring.COMPETENCIES}


def canonical_competency_id(competency_id: str) -> str:
    """Return the canonical PS 26101 competency ID for a current or legacy ID."""
    return graph_authoring.COMPETENCY_ID_ALIASES.get(competency_id, competency_id)


def resolve_competency_id(competency_id: str) -> str:
    """Canonicalize and validate a competency ID against the PS registry."""
    if not isinstance(competency_id, str) or not competency_id.strip():
        raise GraphValidationError("competency_id must be a non-empty string.")
    canonical = canonical_competency_id(competency_id)
    if canonical not in _canonical_competency_ids():
        raise GraphValidationError(f"Unknown competency_id: {competency_id!r}.")
    return canonical


def canonicalize_competency_ids(competency_ids: Iterable[str]) -> List[str]:
    seen = set()
    canonicalized = []
    for competency_id in competency_ids:
        canonical = resolve_competency_id(competency_id)
        if canonical in seen:
            raise GraphValidationError(f"Duplicate competency_id after canonicalization: {canonical!r}.")
        seen.add(canonical)
        canonicalized.append(canonical)
    return canonicalized


def canonicalize_gap_export(open_gaps: Iterable[Dict]) -> List[Dict]:
    """
    Canonicalize competency_id values in a gap-engine PPR seed export.

    When a legacy ID is migrated, the returned row includes
    legacy_competency_id so integrations can audit the change explicitly.
    """
    canonicalized = []
    seen = set()
    for gap in open_gaps:
        if not isinstance(gap, dict):
            raise GraphValidationError("Each gap export item must be a dictionary.")
        item = dict(gap)
        original = item.get("competency_id")
        canonical = resolve_competency_id(original)
        if canonical in seen:
            raise GraphValidationError(f"Duplicate competency_id after canonicalization: {canonical!r}.")
        seen.add(canonical)
        item["competency_id"] = canonical
        if original != canonical:
            item["legacy_competency_id"] = original
        canonicalized.append(item)
    return canonicalized


def build_graph(nodes: List[GraphNode] = None, edges: List[GraphEdge] = None) -> nx.DiGraph:
    """
    Build a networkx.DiGraph from authored nodes/edges.

    The graph contains the complete PS 26101 competency vocabulary as nodes,
    plus MVP role archetype nodes. It validates edge endpoints and rejects
    prerequisite cycles.
    """
    nodes = nodes if nodes is not None else graph_authoring.all_nodes()
    edges = edges if edges is not None else graph_authoring.all_edges()

    _validate_node_list(nodes)
    _validate_edge_list(nodes, edges)

    g = nx.DiGraph()
    for node in nodes:
        g.add_node(
            node.node_id,
            node_type=node.node_type.value,
            display_name=node.display_name,
            domain=node.domain,
            source=node.source,
            source_reference=node.source_reference,
            description=node.description,
            status=node.status,
        )

    for edge in edges:
        g.add_edge(
            edge.source_id,
            edge.target_id,
            edge_type=edge.edge_type.value,
            weight=edge.weight,
            authored_by=edge.authored_by,
            rationale=edge.rationale,
        )

    _validate_prerequisite_acyclicity(g)
    return g


def _validate_node_list(nodes: List[GraphNode]) -> None:
    seen = set()
    for node in nodes:
        if node.node_id in seen:
            raise GraphValidationError(f"Duplicate node_id: {node.node_id!r}.")
        seen.add(node.node_id)


def _validate_edge_list(nodes: List[GraphNode], edges: List[GraphEdge]) -> None:
    node_by_id = {node.node_id: node for node in nodes}
    seen = set()
    for edge in edges:
        if edge.source_id not in node_by_id:
            raise GraphValidationError(f"Edge references unknown source node '{edge.source_id}'.")
        if edge.target_id not in node_by_id:
            raise GraphValidationError(f"Edge references unknown target node '{edge.target_id}'.")

        edge_key = (edge.source_id, edge.target_id, edge.edge_type.value)
        if edge_key in seen:
            raise GraphValidationError(f"Duplicate edge: {edge_key!r}.")
        seen.add(edge_key)

        source_type = node_by_id[edge.source_id].node_type
        target_type = node_by_id[edge.target_id].node_type
        valid = (
            edge.edge_type == EdgeType.REQUIRES
            and source_type == NodeType.ROLE
            and target_type == NodeType.COMPETENCY
        ) or (
            edge.edge_type == EdgeType.PREREQUISITE_OF
            and source_type == NodeType.COMPETENCY
            and target_type == NodeType.COMPETENCY
        ) or (
            edge.edge_type == EdgeType.DECOMPOSES_TO
            and source_type == NodeType.COMPETENCY
            and target_type == NodeType.SKILL
        )
        if not valid:
            raise GraphValidationError(
                "Invalid edge semantics: "
                f"{source_type.value} -[{edge.edge_type.value}]-> {target_type.value} "
                f"for {edge.source_id}->{edge.target_id}."
            )


def _validate_prerequisite_acyclicity(g: nx.DiGraph) -> None:
    """Confirm the PREREQUISITE_OF-only subgraph is acyclic."""
    prereq_edges = [
        (u, v) for u, v, data in g.edges(data=True)
        if data.get("edge_type") == EdgeType.PREREQUISITE_OF.value
    ]
    prereq_subgraph = nx.DiGraph()
    prereq_subgraph.add_nodes_from(g.nodes())
    prereq_subgraph.add_edges_from(prereq_edges)

    if not nx.is_directed_acyclic_graph(prereq_subgraph):
        cycle = nx.find_cycle(prereq_subgraph)
        raise GraphValidationError(
            f"PREREQUISITE_OF edges contain a cycle: {cycle}. "
            "Prerequisite relations must form a DAG."
        )


def competency_prerequisites_of(g: nx.DiGraph, competency_id: str) -> List[str]:
    """Return direct prerequisite competency IDs for a canonical or legacy ID."""
    competency_id = _resolve_graph_competency_id(g, competency_id)
    return [
        u for u, v, data in g.in_edges(competency_id, data=True)
        if data.get("edge_type") == EdgeType.PREREQUISITE_OF.value
    ]


def role_required_competencies(g: nx.DiGraph, role_id: str) -> List[str]:
    """Return competency IDs an MVP role archetype REQUIRES."""
    if not isinstance(role_id, str) or not role_id.strip():
        raise GraphValidationError("role_id must be a non-empty string.")
    if role_id not in g or g.nodes[role_id].get("node_type") != NodeType.ROLE.value:
        raise GraphValidationError(f"Unknown role_id: {role_id!r}.")
    return [
        v for u, v, data in g.out_edges(role_id, data=True)
        if data.get("edge_type") == EdgeType.REQUIRES.value
    ]


def competency_skills(g: nx.DiGraph, competency_id: str) -> List[str]:
    """Return skill IDs a competency DECOMPOSES_TO."""
    competency_id = _resolve_graph_competency_id(g, competency_id)
    return [
        v for u, v, data in g.out_edges(competency_id, data=True)
        if data.get("edge_type") == EdgeType.DECOMPOSES_TO.value
    ]


def _resolve_graph_competency_id(g: nx.DiGraph, competency_id: str) -> str:
    competency_id = resolve_competency_id(competency_id)
    if competency_id not in g or g.nodes[competency_id].get("node_type") != NodeType.COMPETENCY.value:
        raise GraphValidationError(f"Competency {competency_id!r} is not present in this graph.")
    return competency_id


if __name__ == "__main__":
    graph = build_graph()
    print(f"Loaded graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
    print("Prerequisites of 'sdg_indicators':", competency_prerequisites_of(graph, "sdg_indicators"))
    print(
        "Competencies required by 'district_stat_officer':",
        role_required_competencies(graph, "district_stat_officer"),
    )
