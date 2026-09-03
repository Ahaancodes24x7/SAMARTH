"""Graph statistics and deterministic recommendation demo utilities."""

from dataclasses import asdict
from typing import Dict, List

import networkx as nx

from .graph_loader import build_graph
from .graph_schema import EdgeType, NodeType
from .recommender import recommend_upstream_competencies


def graph_statistics(g: nx.DiGraph = None) -> Dict:
    g = g or build_graph()
    node_counts = {
        node_type.value: sum(1 for _, data in g.nodes(data=True) if data.get("node_type") == node_type.value)
        for node_type in NodeType
    }
    edge_counts = {
        edge_type.value: sum(1 for _, _, data in g.edges(data=True) if data.get("edge_type") == edge_type.value)
        for edge_type in EdgeType
    }
    prereq = nx.DiGraph(
        (u, v)
        for u, v, data in g.edges(data=True)
        if data.get("edge_type") == EdgeType.PREREQUISITE_OF.value
    )
    prereq.add_nodes_from(
        node for node, data in g.nodes(data=True) if data.get("node_type") == NodeType.COMPETENCY.value
    )
    is_dag = nx.is_directed_acyclic_graph(prereq)
    longest_path = nx.dag_longest_path(prereq) if is_dag and prereq.number_of_edges() else []
    return {
        "total_nodes": g.number_of_nodes(),
        "total_edges": g.number_of_edges(),
        "role_nodes": node_counts[NodeType.ROLE.value],
        "competency_nodes": node_counts[NodeType.COMPETENCY.value],
        "skill_nodes": node_counts[NodeType.SKILL.value],
        "requires_edges": edge_counts[EdgeType.REQUIRES.value],
        "prerequisite_of_edges": edge_counts[EdgeType.PREREQUISITE_OF.value],
        "decomposes_to_edges": edge_counts[EdgeType.DECOMPOSES_TO.value],
        "prerequisite_graph_depth": max(len(longest_path) - 1, 0),
        "longest_prerequisite_chain": longest_path,
        "competencies_with_prerequisites": len({v for _, v in prereq.edges()}),
        "competencies_with_skill_decomposition": len(
            {
                u for u, _, data in g.edges(data=True)
                if data.get("edge_type") == EdgeType.DECOMPOSES_TO.value
            }
        ),
        "graph_density": round(nx.density(g), 6),
        "prerequisite_graph_is_dag": is_dag,
        "weakly_connected_components": nx.number_weakly_connected_components(g),
    }


def deterministic_demo() -> Dict:
    g = build_graph()
    gaps = [
        {
            "competency_id": "sdg_indicators",
            "gap": 2.6,
            "confidence": 0.8,
            "priority_weight": 0.52,
            "evidence_count": 12,
            "status": "CONFIRMED_GAP",
        },
        {
            "competency_id": "sampling",
            "gap": 1.2,
            "confidence": 0.7,
            "priority_weight": 0.21,
            "evidence_count": 9,
            "status": "CONFIRMED_GAP",
        },
        {
            "competency_id": "survey_design",
            "gap": 0.4,
            "confidence": 0.6,
            "priority_weight": 0.06,
            "evidence_count": 8,
            "status": "CONFIRMED_GAP",
        },
    ]
    ranking = recommend_upstream_competencies(g, gaps, role_id="district_stat_officer")
    return {
        "input_gaps": gaps,
        "ranking": [asdict(item) for item in ranking],
    }


def _print_report() -> None:
    stats = graph_statistics()
    print("Graph statistics:")
    for key, value in stats.items():
        print(f"{key}: {value}")

    demo = deterministic_demo()
    print("\nInput gaps:")
    for gap in demo["input_gaps"]:
        print(
            f"- {gap['competency_id']}: gap={gap['gap']} confidence={gap['confidence']} "
            f"evidence_count={gap['evidence_count']} status={gap['status']}"
        )

    print("\nPPR / graph ranking:")
    for idx, item in enumerate(demo["ranking"], start=1):
        print(
            f"{idx}. {item['competency_id']} score={item['score']} "
            f"source_gap={item['source_gap']} distance={item['graph_distance']} "
            f"path={' <- '.join(item['path'])} status={item['evidence_status']}"
        )


if __name__ == "__main__":
    _print_report()
