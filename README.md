# SAMARTH AIML Competency Graph

This repository contains AIML components for SkillCompass/SAMARTH. The
competency graph uses the actual PS 26101 competency vocabulary as its
canonical registry.

The graph separates four concerns:

- Full PS competency vocabulary: all 33 PS-explicit competencies are present
  as canonical competency nodes.
- Curated prerequisite edges: only SME-authored prerequisite relationships
  with rationale are included.
- Role-specific requirements: current role mappings are MVP-authored
  archetypes, not official PS job-title/designation mappings.
- Learner BKT state: the gap engine computes learner mastery, confidence,
  recency, gaps, and PPR seed exports.

Legacy MVP competency IDs are migrated explicitly:

```text
sdg_indicator_estimation -> sdg_indicators
data_quality             -> data_quality_frameworks
python_basics            -> python
gis_fundamentals         -> gis
```

See [AIML_ENGINE_TECHNICAL.md](AIML_ENGINE_TECHNICAL.md) and
[aiml/skillcompass_gap_engine/README.md](aiml/skillcompass_gap_engine/README.md)
for implementation details.

## Measured Graph Report

Generated with:

```bash
python -m aiml.competency_graph.graph_report
```

Actual output from this repository:

```text
total_nodes: 68
total_edges: 49
role_nodes: 3
competency_nodes: 33
skill_nodes: 32
requires_edges: 14
prerequisite_of_edges: 3
decomposes_to_edges: 32
prerequisite_graph_depth: 1
longest_prerequisite_chain: ['survey_design', 'sdg_indicators']
competencies_with_prerequisites: 2
competencies_with_skill_decomposition: 8
graph_density: 0.010755
prerequisite_graph_is_dag: True
weakly_connected_components: 28
```

Deterministic PPR demo ranking:

```text
1. sdg_indicators score=2.872084 source_gap=sdg_indicators distance=0 path=sdg_indicators status=CONFIRMED_GAP
2. sampling score=2.799836 source_gap=sdg_indicators distance=1 path=sdg_indicators <- sampling status=UPSTREAM_PREREQUISITE
3. survey_design score=2.678081 source_gap=sdg_indicators distance=1 path=sdg_indicators <- survey_design status=UPSTREAM_PREREQUISITE
```

## Validation

Actual validation run:

```text
python -m py_compile ...
python -m pytest -v
python -m aiml.competency_graph.graph_loader
python -m aiml.competency_graph.graph_report
API/import smoke: ok
```

Full pytest result:

```text
61 passed, 3 warnings in 1.96s
```
