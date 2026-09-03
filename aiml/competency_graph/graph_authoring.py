"""
Canonical AIML competency registry and authored graph facts.

The competency registry below contains exactly the 33 competencies explicitly
listed in PS 26101, grouped under the PS domains:

- Statistical
- Technical
- Digital Governance
- Behavioural / Managerial

PS 26101 describes learners through profile fields such as designation,
department, job role, current assignment, education, experience, and previous
training. It does not provide an exhaustive canonical list of government job
titles. The role nodes below are therefore retained as MVP archetypes for demo
compatibility only, with source="mvp_authored_role_profile".

Role requirements and prerequisite edges are deliberately separate from the
canonical competency vocabulary. Do not add prerequisite edges merely because a
competency exists in the registry.
"""

from typing import Dict, List, Optional

from .graph_schema import EdgeType, GraphEdge, GraphNode, NodeType

PS_26101_SOURCE = "ps_26101_explicit_competency_list"
MVP_ROLE_SOURCE = "mvp_authored_role_profile"
MVP_ROLE_MAPPING_SOURCE = "mvp_authored_role_competency_mapping"
SME_PREREQ_SOURCE = "sme_authored_prerequisite"
SME_SKILL_SOURCE = "sme_authored_skill_decomposition"


def _competency(
    node_id: str,
    display_name: str,
    domain: str,
    description: Optional[str] = None,
) -> GraphNode:
    return GraphNode(
        node_id=node_id,
        node_type=NodeType.COMPETENCY,
        display_name=display_name,
        domain=domain,
        source=PS_26101_SOURCE,
        source_reference=f"PS 26101 explicit competency list: {domain}",
        description=description,
        status="active",
    )


def _skill(
    node_id: str,
    display_name: str,
    domain: str,
    description: Optional[str] = None,
) -> GraphNode:
    return GraphNode(
        node_id=node_id,
        node_type=NodeType.SKILL,
        display_name=display_name,
        domain=domain,
        source=SME_SKILL_SOURCE,
        source_reference="MVP curated decomposition of selected PS 26101 competencies",
        description=description,
        status="active",
    )


ROLES: List[GraphNode] = [
    GraphNode(
        "district_stat_officer",
        NodeType.ROLE,
        "District Statistical Officer",
        source=MVP_ROLE_SOURCE,
        source_reference="MVP role archetype; not an exhaustive PS 26101 job-title list",
        description="Illustrative field-statistics role profile retained for MVP compatibility.",
    ),
    GraphNode(
        "senior_stat_officer",
        NodeType.ROLE,
        "Senior Statistical Officer",
        source=MVP_ROLE_SOURCE,
        source_reference="MVP role archetype; not an exhaustive PS 26101 job-title list",
        description="Illustrative senior statistics role profile retained for MVP compatibility.",
    ),
    GraphNode(
        "data_analyst",
        NodeType.ROLE,
        "Data Analyst",
        source=MVP_ROLE_SOURCE,
        source_reference="MVP role archetype; not an exhaustive PS 26101 job-title list",
        description="Illustrative analytical role profile retained for MVP compatibility.",
    ),
]


COMPETENCIES: List[GraphNode] = [
    _competency("survey_design", "Survey Design", "statistical"),
    _competency("sampling", "Sampling", "statistical"),
    _competency("national_accounts", "National Accounts", "statistical"),
    _competency("price_statistics", "Price Statistics", "statistical"),
    _competency("labour_statistics", "Labour Statistics", "statistical"),
    _competency("agricultural_statistics", "Agricultural Statistics", "statistical"),
    _competency("industrial_statistics", "Industrial Statistics", "statistical"),
    _competency("sdg_indicators", "SDG Indicators", "statistical"),
    _competency("metadata_standards", "Metadata Standards", "statistical"),
    _competency("data_quality_frameworks", "Data Quality Frameworks", "statistical"),
    _competency("python", "Python", "technical"),
    _competency("r", "R", "technical"),
    _competency("sql", "SQL", "technical"),
    _competency("stata", "Stata", "technical"),
    _competency("spss", "SPSS", "technical"),
    _competency("sas", "SAS", "technical"),
    _competency("gis", "GIS", "technical"),
    _competency("data_visualization", "Data Visualization", "technical"),
    _competency("ai_ml", "AI/ML", "technical"),
    _competency("cloud_computing", "Cloud Computing", "technical"),
    _competency("apis", "APIs", "technical"),
    _competency("open_data", "Open Data", "technical"),
    _competency("cybersecurity", "Cybersecurity", "digital_governance"),
    _competency("data_privacy", "Data Privacy", "digital_governance"),
    _competency("digital_signatures", "Digital Signatures", "digital_governance"),
    _competency("government_cloud", "Government Cloud", "digital_governance"),
    _competency(
        "digital_public_infrastructure",
        "Digital Public Infrastructure",
        "digital_governance",
    ),
    _competency("leadership", "Leadership", "behavioural_managerial"),
    _competency("communication", "Communication", "behavioural_managerial"),
    _competency("project_management", "Project Management", "behavioural_managerial"),
    _competency("ethics", "Ethics", "behavioural_managerial"),
    _competency("decision_making", "Decision Making", "behavioural_managerial"),
    _competency("change_management", "Change Management", "behavioural_managerial"),
]


SKILLS: List[GraphNode] = [
    _skill("sampling_frames", "Sampling Frames", "statistical"),
    _skill("probability_sampling", "Probability Sampling", "statistical"),
    _skill("sample_weights", "Sample Weights", "statistical"),
    _skill("sampling_error", "Sampling Error", "statistical"),
    _skill("questionnaire_design", "Questionnaire Design", "statistical"),
    _skill("target_population_definition", "Target Population Definition", "statistical"),
    _skill("survey_instrumentation", "Survey Instrumentation", "statistical"),
    _skill("non_response_design", "Non-response Design", "statistical"),
    _skill("indicator_metadata", "Indicator Metadata", "statistical"),
    _skill("indicator_computation", "Indicator Computation", "statistical"),
    _skill("disaggregation_methods", "Disaggregation Methods", "statistical"),
    _skill("sdg_reporting_workflow", "SDG Reporting Workflow", "statistical"),
    _skill("quality_dimensions", "Quality Dimensions", "statistical"),
    _skill("validation_rules", "Validation Rules", "statistical"),
    _skill("outlier_detection", "Outlier Detection", "statistical"),
    _skill("quality_reporting", "Quality Reporting", "statistical"),
    _skill("python_control_flow", "Data Types and Control Flow", "technical"),
    _skill("python_data_manipulation", "Python Data Manipulation", "technical"),
    _skill("python_statistical_analysis", "Python for Statistics", "technical"),
    _skill("python_reproducible_notebooks", "Reproducible Notebooks", "technical"),
    _skill("spatial_data_models", "Spatial Data Models", "technical"),
    _skill("coordinate_reference_systems", "Coordinate Reference Systems", "technical"),
    _skill("geospatial_analysis", "Geospatial Analysis", "technical"),
    _skill("thematic_mapping", "Thematic Mapping", "technical"),
    _skill("chart_selection", "Chart Selection", "technical"),
    _skill("dashboard_design", "Dashboard Design", "technical"),
    _skill("visual_encoding", "Visual Encoding", "technical"),
    _skill("accessibility_in_visuals", "Accessibility in Visuals", "technical"),
    _skill("model_evaluation", "Model Evaluation", "technical"),
    _skill("feature_engineering", "Feature Engineering", "technical"),
    _skill("classification_regression", "Classification and Regression", "technical"),
    _skill("responsible_ai", "Responsible AI", "technical"),
]


COMPETENCY_ID_ALIASES: Dict[str, str] = {
    # Legacy MVP/gap-engine IDs retained as explicit migration aliases.
    "sdg_indicator_estimation": "sdg_indicators",
    "data_quality": "data_quality_frameworks",
    "python_basics": "python",
    "gis_fundamentals": "gis",
}


ROLE_REQUIRES_EDGES: List[GraphEdge] = [
    GraphEdge("district_stat_officer", "sampling", EdgeType.REQUIRES, authored_by=MVP_ROLE_MAPPING_SOURCE),
    GraphEdge("district_stat_officer", "survey_design", EdgeType.REQUIRES, authored_by=MVP_ROLE_MAPPING_SOURCE),
    GraphEdge("district_stat_officer", "sdg_indicators", EdgeType.REQUIRES, authored_by=MVP_ROLE_MAPPING_SOURCE),
    GraphEdge("district_stat_officer", "data_quality_frameworks", EdgeType.REQUIRES, authored_by=MVP_ROLE_MAPPING_SOURCE),
    GraphEdge("district_stat_officer", "python", EdgeType.REQUIRES, authored_by=MVP_ROLE_MAPPING_SOURCE),
    GraphEdge("district_stat_officer", "gis", EdgeType.REQUIRES, authored_by=MVP_ROLE_MAPPING_SOURCE),
    GraphEdge("senior_stat_officer", "sampling", EdgeType.REQUIRES, authored_by=MVP_ROLE_MAPPING_SOURCE),
    GraphEdge("senior_stat_officer", "survey_design", EdgeType.REQUIRES, authored_by=MVP_ROLE_MAPPING_SOURCE),
    GraphEdge("senior_stat_officer", "sdg_indicators", EdgeType.REQUIRES, authored_by=MVP_ROLE_MAPPING_SOURCE),
    GraphEdge("senior_stat_officer", "data_quality_frameworks", EdgeType.REQUIRES, authored_by=MVP_ROLE_MAPPING_SOURCE),
    GraphEdge("data_analyst", "sampling", EdgeType.REQUIRES, authored_by=MVP_ROLE_MAPPING_SOURCE),
    GraphEdge("data_analyst", "data_quality_frameworks", EdgeType.REQUIRES, authored_by=MVP_ROLE_MAPPING_SOURCE),
    GraphEdge("data_analyst", "python", EdgeType.REQUIRES, authored_by=MVP_ROLE_MAPPING_SOURCE),
    GraphEdge("data_analyst", "gis", EdgeType.REQUIRES, authored_by=MVP_ROLE_MAPPING_SOURCE),
]


DECOMPOSES_TO_EDGES: List[GraphEdge] = [
    GraphEdge("sampling", "sampling_frames", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("sampling", "probability_sampling", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("sampling", "sample_weights", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("sampling", "sampling_error", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("survey_design", "questionnaire_design", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("survey_design", "target_population_definition", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("survey_design", "survey_instrumentation", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("survey_design", "non_response_design", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("sdg_indicators", "indicator_metadata", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("sdg_indicators", "indicator_computation", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("sdg_indicators", "disaggregation_methods", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("sdg_indicators", "sdg_reporting_workflow", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("data_quality_frameworks", "quality_dimensions", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("data_quality_frameworks", "validation_rules", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("data_quality_frameworks", "outlier_detection", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("data_quality_frameworks", "quality_reporting", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("python", "python_control_flow", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("python", "python_data_manipulation", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("python", "python_statistical_analysis", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("python", "python_reproducible_notebooks", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("gis", "spatial_data_models", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("gis", "coordinate_reference_systems", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("gis", "geospatial_analysis", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("gis", "thematic_mapping", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("data_visualization", "chart_selection", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("data_visualization", "dashboard_design", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("data_visualization", "visual_encoding", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("data_visualization", "accessibility_in_visuals", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("ai_ml", "model_evaluation", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("ai_ml", "feature_engineering", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("ai_ml", "classification_regression", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
    GraphEdge("ai_ml", "responsible_ai", EdgeType.DECOMPOSES_TO, authored_by=SME_SKILL_SOURCE),
]


PREREQUISITE_EDGES: List[GraphEdge] = [
    GraphEdge(
        "sampling",
        "sdg_indicators",
        EdgeType.PREREQUISITE_OF,
        authored_by=SME_PREREQ_SOURCE,
        rationale=(
            "Estimating SDG indicators from official survey data requires "
            "understanding sampling frames, weights, and design effects."
        ),
    ),
    GraphEdge(
        "survey_design",
        "sdg_indicators",
        EdgeType.PREREQUISITE_OF,
        authored_by=SME_PREREQ_SOURCE,
        rationale=(
            "Interpreting SDG indicators depends on knowing how the source "
            "survey defines the target population, instrument, and frame."
        ),
    ),
    GraphEdge(
        "sampling",
        "data_quality_frameworks",
        EdgeType.PREREQUISITE_OF,
        authored_by=SME_PREREQ_SOURCE,
        rationale=(
            "Survey data-quality review includes coverage, non-response, and "
            "sampling-error concepts that require sampling knowledge."
        ),
    ),
]


def all_nodes() -> List[GraphNode]:
    return ROLES + COMPETENCIES + SKILLS


def all_edges() -> List[GraphEdge]:
    return ROLE_REQUIRES_EDGES + PREREQUISITE_EDGES + DECOMPOSES_TO_EDGES
