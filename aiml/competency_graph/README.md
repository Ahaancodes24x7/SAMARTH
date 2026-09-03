# Competency Graph

This package owns the AIML competency graph contract.

The canonical competency registry is the 33-competency PS 26101 vocabulary in
`graph_authoring.py`. Legacy IDs are aliases only and are rejected if they
cannot be migrated to a canonical ID.

Node types:

```text
ROLE
COMPETENCY
SKILL
```

Edge types:

```text
ROLE -> REQUIRES -> COMPETENCY
COMPETENCY -> PREREQUISITE_OF -> COMPETENCY
COMPETENCY -> DECOMPOSES_TO -> SKILL
```

Current role nodes are MVP-authored archetypes, not official PS job titles.
Current prerequisite and skill-decomposition edges are SME-authored MVP facts
with explicit provenance.

Run validation, tests, stats, and deterministic demo:

```bash
python -m pytest aiml/competency_graph/test_graph.py aiml/competency_graph/test_recommender.py -v
python -m aiml.competency_graph.graph_report
```
