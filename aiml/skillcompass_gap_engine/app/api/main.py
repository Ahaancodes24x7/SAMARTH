

from fastapi import FastAPI, HTTPException
from datetime import datetime
from math import isfinite
from typing import Dict, List

from app.schemas.schemas import (
    OnboardingEvent, RoleAssignmentEvent, CourseCompletionEvent,
    AssessmentAttemptEvent, LearnerCompetencyStateResponse,
)
from app.services.competency.mastery import AssessmentEvent
from app.services.competency.state_engine import CompetencyStateEngine, _resolve_graph_competency_id

app = FastAPI(
    title="SkillCompass — Competency State & Gap Engine",
    description="Deterministic, explainable competency-gap computation. "
                 "No LLM calls happen in this module.",
    version="0.1.0",
)

engine = CompetencyStateEngine()


class InMemoryStore:
    

    def __init__(self):
        self.learners: Dict[str, dict] = {}
        self.role_requirements: Dict[str, Dict[str, float]] = {}
        self.events: Dict[str, List[AssessmentEvent]] = {}

    def ensure_learner(self, user_id: str):
        if user_id not in self.events:
            self.events[user_id] = []

    def add_role(self, role: str, requirements: Dict[str, float]):
        self.role_requirements[role] = requirements


store = InMemoryStore()


@app.post("/learners", status_code=201)
def create_learner(event: OnboardingEvent):
    store.learners[event.identity.user_id] = event.identity.model_dump()
    store.ensure_learner(event.identity.user_id)
    return {"status": "created", "user_id": event.identity.user_id}


@app.post("/roles/assign", status_code=200)
def assign_role(event: RoleAssignmentEvent):
    reqs = {}
    for requirement in event.requirements:
        try:
            competency_id = _resolve_graph_competency_id(requirement.competency_id)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not isfinite(requirement.required_level) or not 1.0 <= requirement.required_level <= 5.0:
            raise HTTPException(status_code=400, detail="required_level must be between 1.0 and 5.0")
        if competency_id in reqs:
            raise HTTPException(status_code=400, detail=f"Duplicate competency_id: {competency_id}")
        reqs[competency_id] = requirement.required_level
    store.add_role(event.role, reqs)
    if event.user_id in store.learners:
        store.learners[event.user_id]["role"] = event.role
    return {"status": "role_assigned", "user_id": event.user_id, "role": event.role}


@app.post("/course-completions", status_code=201)
def record_course_completion(event: CourseCompletionEvent):
    
    store.ensure_learner(event.user_id)
    return {"status": "recorded", "note": "Course completion logged as training evidence; does not directly update mastery."}


@app.post("/assessment-attempts", status_code=201)
def record_assessment_attempt(event: AssessmentAttemptEvent):
    store.ensure_learner(event.user_id)
    try:
        competency_id = _resolve_graph_competency_id(event.competency_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    store.events[event.user_id].append(
        AssessmentEvent(
            question_id=event.question_id,
            competency_id=competency_id,
            difficulty=event.difficulty,
            correct=event.correct,
            timestamp=event.timestamp,
            learning_opportunity=event.learning_opportunity,
        )
    )
    return {"status": "recorded", "user_id": event.user_id, "competency_id": competency_id}


@app.get("/learners/{user_id}/competency-state", response_model=LearnerCompetencyStateResponse)
def get_competency_state(user_id: str):
    if user_id not in store.learners:
        raise HTTPException(status_code=404, detail="Learner not found")
    role = store.learners[user_id].get("role")
    requirements = store.role_requirements.get(role, {})
    if not requirements:
        raise HTTPException(status_code=400, detail=f"No role requirements found for role '{role}'")
    state = engine.compute_state(user_id, requirements, store.events.get(user_id, []))
    return state.to_explainable_json()


@app.get("/learners/{user_id}/gaps")
def get_ranked_gaps(user_id: str):
    if user_id not in store.learners:
        raise HTTPException(status_code=404, detail="Learner not found")
    role = store.learners[user_id].get("role")
    requirements = store.role_requirements.get(role, {})
    state = engine.compute_state(user_id, requirements, store.events.get(user_id, []))
    ranked = state.ranked_gaps()
    return {
        "user_id": user_id,
        "ranked_gaps": [
            {"competency": r.competency_id, "gap": r.gap, "priority_weight": r.priority_weight,
             "needs_more_evidence": r.needs_more_evidence, "needs_reassessment": r.needs_reassessment,
             "status": r.status, "reason": r.reason}
            for r in ranked
        ],
    }


@app.get("/learners/{user_id}/ppr-seed-export")
def get_ppr_seed_export(user_id: str):
    """PART 16 — output contract for the future PPR/graph engine. This
    endpoint does NOT run PageRank; it exports seed nodes only."""
    if user_id not in store.learners:
        raise HTTPException(status_code=404, detail="Learner not found")
    role = store.learners[user_id].get("role")
    requirements = store.role_requirements.get(role, {})
    state = engine.compute_state(user_id, requirements, store.events.get(user_id, []))
    return state.to_ppr_seed_export()


@app.post("/learners/{user_id}/recalculate-state")
def recalculate_state(user_id: str):
    
    return get_competency_state(user_id)


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
