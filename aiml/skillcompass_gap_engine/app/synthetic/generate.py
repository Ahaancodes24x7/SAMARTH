"""
Synthetic data generator for development/testing ONLY.

*** ALL DATA PRODUCED BY THIS MODULE IS SYNTHETIC / FICTIONAL. ***
It exists to exercise the pipeline end-to-end during development and in
the SIH demo. It must never be presented as real learner data.

The generator emits canonical PS 26101 competency IDs for its curated demo
subset. It keeps a legacy alias map for older synthetic fixtures that used
pre-correction MVP IDs.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List

from app.services.competency.mastery import AssessmentEvent

ROLES = ["district_stat_officer", "senior_stat_officer", "data_analyst"]

COMPETENCIES = {
    # domain: statistical
    "sampling": {"domain": "statistical", "difficulty_mix": ["easy", "medium", "hard"]},
    "survey_design": {"domain": "statistical", "difficulty_mix": ["easy", "medium", "hard"]},
    "sdg_indicators": {"domain": "statistical", "difficulty_mix": ["medium", "hard"]},
    "data_quality_frameworks": {"domain": "statistical", "difficulty_mix": ["easy", "medium"]},
    # domain: technical
    "python": {"domain": "technical", "difficulty_mix": ["easy", "medium", "hard"]},
    "gis": {"domain": "technical", "difficulty_mix": ["easy", "medium"]},
}

LEGACY_COMPETENCY_ID_ALIASES = {
    "sdg_indicator_estimation": "sdg_indicators",
    "data_quality": "data_quality_frameworks",
    "python_basics": "python",
    "gis_fundamentals": "gis",
}

# Prerequisite-like pairs used only to correlate synthetic performance.
CORRELATED_PAIRS = [
    ("sampling", "sdg_indicators"),
    ("survey_design", "sdg_indicators"),
]

ROLE_REQUIREMENTS = {
    "district_stat_officer": {
        "sampling": 4.0,
        "survey_design": 4.0,
        "sdg_indicators": 3.0,
        "data_quality_frameworks": 3.0,
        "python": 2.0,
        "gis": 2.0,
    },
    "senior_stat_officer": {
        "sampling": 4.5,
        "survey_design": 4.5,
        "sdg_indicators": 4.0,
        "data_quality_frameworks": 4.0,
        "python": 3.0,
        "gis": 3.0,
    },
    "data_analyst": {
        "sampling": 3.0,
        "survey_design": 2.5,
        "sdg_indicators": 3.5,
        "data_quality_frameworks": 4.0,
        "python": 4.5,
        "gis": 4.0,
    },
}


def _designation_skill_ceiling(designation_level: str) -> float:
    """Return a synthetic skill tendency for demo data, not a real cap."""
    return {"Junior": 0.45, "Mid": 0.62, "Senior": 0.78}.get(designation_level, 0.55)


def generate_synthetic_learners(n: int = 60, seed: int = 42) -> List[dict]:
    """
    Return fictional learners with identity, role, required_levels, events, and
    synthetic_ground_truth.
    """
    rng = random.Random(seed)
    learners = []

    for i in range(n):
        user_id = f"SYN_{i:03d}"
        role = rng.choice(ROLES)
        designation = rng.choices(["Junior", "Mid", "Senior"], weights=[0.5, 0.35, 0.15])[0]
        experience_years = round(rng.uniform(0.5, 20.0), 1)
        ceiling = _designation_skill_ceiling(designation)

        true_skill: Dict[str, float] = {}
        for comp in COMPETENCIES:
            base = max(0.05, min(0.95, rng.gauss(ceiling, 0.15)))
            true_skill[comp] = base
        for a, b in CORRELATED_PAIRS:
            true_skill[b] = max(0.05, min(0.95, 0.6 * true_skill[b] + 0.4 * true_skill[a]))

        evidence_profile = rng.choices(
            ["sparse", "moderate", "rich"], weights=[0.3, 0.45, 0.25]
        )[0]
        n_events_range = {"sparse": (0, 2), "moderate": (3, 8), "rich": (10, 25)}[
            evidence_profile
        ]

        events: List[AssessmentEvent] = []
        now = datetime.utcnow()
        for comp, meta in COMPETENCIES.items():
            n_events = rng.randint(*n_events_range)
            skill = true_skill[comp]
            for _ in range(n_events):
                difficulty = rng.choice(meta["difficulty_mix"])
                difficulty_penalty = {"easy": 0.0, "medium": 0.12, "hard": 0.25}[difficulty]
                p_correct = max(0.05, min(0.95, skill - difficulty_penalty))
                correct = rng.random() < p_correct
                days_ago = rng.choices(
                    [rng.uniform(0, 14), rng.uniform(15, 60), rng.uniform(61, 200)],
                    weights=[0.4, 0.35, 0.25],
                )[0]
                ts = now - timedelta(days=days_ago)
                events.append(
                    AssessmentEvent(
                        question_id=f"Q_{comp}_{rng.randint(1, 9999)}",
                        competency_id=comp,
                        difficulty=difficulty,
                        correct=correct,
                        timestamp=ts,
                        learning_opportunity=False,
                    )
                )

        learners.append(
            {
                "identity": {
                    "user_id": user_id,
                    "role": role,
                    "department": rng.choice(
                        ["Jharkhand Field Office", "MoSPI HQ", "NSSTA Regional Center"]
                    ),
                    "designation_level": designation,
                    "experience_years": experience_years,
                },
                "role": role,
                "required_levels": ROLE_REQUIREMENTS[role],
                "events": events,
                "synthetic_ground_truth": true_skill,
            }
        )

    return learners


if __name__ == "__main__":
    data = generate_synthetic_learners(n=5, seed=1)
    for learner in data:
        print(learner["identity"]["user_id"], learner["role"], "events:", len(learner["events"]))
