

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Literal
from datetime import datetime

class LearnerIdentity(BaseModel):
    user_id: str = Field(..., description="USER-provided (assigned at registration). Mandatory for MVP.")
    role: str = Field(..., description="USER-provided (self-declared) or ADMIN-assigned. Mandatory.")
    department: str = Field(..., description="USER-provided. Mandatory.")
    designation_level: Optional[str] = Field(None, description="USER-provided. Optional for MVP.")
    experience_years: Optional[float] = Field(None, ge=0, description="USER-provided. Optional for MVP.")

class RoleCompetencyRequirement(BaseModel):
    competency_id: str = Field(..., description="ADMIN-authored. Mandatory.")
    required_level: float = Field(..., ge=1, le=5, description="ADMIN-authored, 1-5 scale. Mandatory.")

class TrainingEvidence(BaseModel):
    course_id: str = Field(..., description="SYSTEM-recorded. Mandatory.")
    competency_id: str = Field(..., description="SYSTEM-recorded (from course-competency mapping). Mandatory.")
    completion_status: Literal["enrolled", "in_progress", "completed"] = Field(...)
    completion_date: Optional[datetime] = Field(None, description="SYSTEM-recorded. Mandatory if completed.")

class AssessmentEvidence(BaseModel):
    question_id: str = Field(..., description="SYSTEM-recorded. Mandatory.")
    competency_id: str = Field(..., description="SYSTEM-recorded. Mandatory.")
    difficulty: Literal["easy", "medium", "hard"] = Field(..., description="ADMIN/SYSTEM-authored at question creation. Mandatory.")
    correct: bool = Field(..., description="SYSTEM-recorded. Mandatory.")
    timestamp: datetime = Field(..., description="SYSTEM-recorded. Mandatory.")
    learning_opportunity: bool = Field(False, description="True when the event included instruction/practice feedback.")


class DerivedCompetencyState(BaseModel):
    competency: str
    required_level: float
    mastery_probability: float = Field(..., ge=0, le=1, description="SYSTEM-derived standard BKT posterior P(L).")
    display_level: float = Field(..., description="Product display transform = 1 + 4 * mastery_probability.")
    evidence_confidence: float = Field(..., ge=0, le=1, description="SYSTEM-derived evidence confidence, separate from mastery.")
    evidence_freshness: float = Field(..., ge=0, le=1, description="SYSTEM-derived evidence freshness for reassessment.")
    raw_mastery: float = Field(..., description="Backward-compatible alias for display_level.")
    confidence: float = Field(..., ge=0, le=1, description="SYSTEM-derived, 0-1.")
    recency_factor: float = Field(..., ge=0, le=1, description="SYSTEM-derived, 0-1.")
    effective_level: float = Field(..., description="Backward-compatible alias for display_level; recency does not reduce mastery.")
    gap: float = Field(..., description="SYSTEM-derived = required_level - display_level.")
    priority_weight: float = Field(..., ge=0, le=1, description="SYSTEM-derived, gap x confidence, normalized.")
    needs_more_evidence: bool
    needs_reassessment: bool
    evidence_count: int
    last_demonstrated: Optional[datetime]
    status: Literal["CONFIRMED_GAP", "UNCERTAIN_MORE_EVIDENCE", "NO_GAP", "REASSESSMENT_REQUIRED"]
    bkt_parameter_version: str
    reason: str


class LearnerCompetencyStateResponse(BaseModel):
    learner_id: str
    generated_at: datetime
    competencies: List[DerivedCompetencyState]


#
class LearnerProfile(BaseModel):
    identity: LearnerIdentity
    role_requirements: List[RoleCompetencyRequirement]
    training_evidence: List[TrainingEvidence] = []
    assessment_evidence: List[AssessmentEvidence] = []
    derived_state: Optional[List[DerivedCompetencyState]] = None

class OnboardingEvent(BaseModel):
    event_type: Literal["onboarding"] = "onboarding"
    identity: LearnerIdentity


class RoleAssignmentEvent(BaseModel):
    event_type: Literal["role_assignment"] = "role_assignment"
    user_id: str
    role: str
    requirements: List[RoleCompetencyRequirement]


class CourseCompletionEvent(BaseModel):
    event_type: Literal["course_completion"] = "course_completion"
    user_id: str
    course_id: str
    competency_id: str
    completion_date: datetime


class AssessmentAttemptEvent(BaseModel):
    event_type: Literal["assessment_attempt"] = "assessment_attempt"
    user_id: str
    question_id: str
    competency_id: str
    difficulty: Literal["easy", "medium", "hard"]
    correct: bool
    timestamp: datetime
    learning_opportunity: bool = False
