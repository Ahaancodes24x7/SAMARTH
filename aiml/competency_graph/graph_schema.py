"""
Competency graph schema for SkillCompass.

This module defines typed nodes and edges for the AIML competency graph.
The canonical competency registry is sourced from the PS 26101 explicit
competency vocabulary. Role profiles and role-to-competency mappings remain
MVP-authored archetypes until a government/SME competency framework provides
authoritative designation mappings.

Prerequisite relationships are intentionally sparse: they are SME-authored
facts with rationale/provenance, not generated between every competency.
Downstream graph algorithms should therefore treat complete node coverage and
complete prerequisite connectivity as separate concerns.
"""

from dataclasses import dataclass
from enum import Enum
from math import isfinite
import re
from typing import Optional


class NodeType(str, Enum):
    ROLE = "role"
    COMPETENCY = "competency"
    SKILL = "skill"


class EdgeType(str, Enum):
    REQUIRES = "requires"
    PREREQUISITE_OF = "prerequisite_of"
    DECOMPOSES_TO = "decomposes_to"


# Uniform default edge weight. This is an explicit unweighted-graph default,
# not a fitted or invented prerequisite-strength score.
DEFAULT_EDGE_WEIGHT: float = 1.0
NODE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    node_type: NodeType
    display_name: str
    domain: Optional[str] = None
    source: str = "sme_authored"
    source_reference: Optional[str] = None
    description: Optional[str] = None
    status: str = "active"

    def __post_init__(self):
        if not self.node_id or not NODE_ID_PATTERN.fullmatch(self.node_id):
            raise ValueError(f"Invalid graph node_id: {self.node_id!r}")
        if not self.display_name or not self.display_name.strip():
            raise ValueError(f"Graph node {self.node_id!r} must have a display_name.")
        if not self.source or not self.source.strip():
            raise ValueError(f"Graph node {self.node_id!r} must have provenance source.")
        if self.node_type in {NodeType.COMPETENCY, NodeType.SKILL} and not self.domain:
            raise ValueError(f"{self.node_type.value} node {self.node_id!r} must have a domain.")
        if self.status not in {"active", "draft", "deprecated"}:
            raise ValueError(f"Graph node {self.node_id!r} has unsupported status {self.status!r}.")


@dataclass(frozen=True)
class GraphEdge:
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = DEFAULT_EDGE_WEIGHT
    authored_by: str = "sme"
    rationale: Optional[str] = None

    def __post_init__(self):
        for field_name, value in {
            "source_id": self.source_id,
            "target_id": self.target_id,
        }.items():
            if not value or not NODE_ID_PATTERN.fullmatch(value):
                raise ValueError(f"Invalid edge {field_name}: {value!r}")
        if self.source_id == self.target_id:
            raise ValueError(f"Self-loop edge {self.source_id}->{self.target_id} is not allowed.")
        if not isfinite(self.weight) or self.weight <= 0:
            raise ValueError(f"Edge {self.source_id}->{self.target_id} has invalid weight {self.weight!r}.")
        if not self.authored_by or not self.authored_by.strip():
            raise ValueError(f"Edge {self.source_id}->{self.target_id} must have provenance.")
        if self.edge_type == EdgeType.PREREQUISITE_OF and not self.rationale:
            raise ValueError(
                f"PREREQUISITE_OF edge {self.source_id}->{self.target_id} "
                "must carry a rationale. Unexplained prerequisite claims are "
                "not allowed in the AIML graph."
            )
