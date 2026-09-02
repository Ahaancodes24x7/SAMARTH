

CREATE TABLE IF NOT EXISTS roles (
    role_id         VARCHAR(64)  PRIMARY KEY,
    role_name       VARCHAR(200) NOT NULL,
    description     TEXT
);

CREATE TABLE IF NOT EXISTS competencies (
    competency_id   VARCHAR(64)  PRIMARY KEY,
    name            VARCHAR(200) NOT NULL,
    domain          VARCHAR(64)  NOT NULL,  -- e.g. 'statistical', 'technical'
    description     TEXT
);

CREATE TABLE IF NOT EXISTS role_competencies (
    role_id         VARCHAR(64)  NOT NULL REFERENCES roles(role_id) ON DELETE RESTRICT,
    competency_id   VARCHAR(64)  NOT NULL REFERENCES competencies(competency_id) ON DELETE RESTRICT,
    required_level  NUMERIC(2,1) NOT NULL CHECK (required_level BETWEEN 1 AND 5),
    authored_by     VARCHAR(128),            -- admin/SME who set this requirement
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (role_id, competency_id)
);

CREATE TABLE IF NOT EXISTS learners (
    user_id             VARCHAR(64)  PRIMARY KEY,
    role_id             VARCHAR(64)  NOT NULL REFERENCES roles(role_id) ON DELETE RESTRICT,
    department          VARCHAR(200) NOT NULL,
    designation_level   VARCHAR(64),
    experience_years    NUMERIC(4,1),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_learners_role ON learners(role_id);
CREATE INDEX IF NOT EXISTS idx_learners_department ON learners(department);

CREATE TABLE IF NOT EXISTS courses (
    course_id       VARCHAR(64)  PRIMARY KEY,
    title           VARCHAR(300) NOT NULL,
    provider        VARCHAR(200),            -- e.g. 'iGOT-mock', 'NSSTA-mock'
    source          VARCHAR(32) NOT NULL DEFAULT 'mock'  -- 'mock' | 'real'
);

CREATE TABLE IF NOT EXISTS course_competencies (
    course_id       VARCHAR(64) NOT NULL REFERENCES courses(course_id) ON DELETE RESTRICT,
    competency_id   VARCHAR(64) NOT NULL REFERENCES competencies(competency_id) ON DELETE RESTRICT,
    PRIMARY KEY (course_id, competency_id)
);

CREATE TABLE IF NOT EXISTS course_completions (
    id              BIGSERIAL PRIMARY KEY,
    user_id         VARCHAR(64) NOT NULL REFERENCES learners(user_id) ON DELETE CASCADE,
    course_id       VARCHAR(64) NOT NULL REFERENCES courses(course_id) ON DELETE RESTRICT,
    status          VARCHAR(16) NOT NULL CHECK (status IN ('enrolled','in_progress','completed')),
    completion_date TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_course_completions_user ON course_completions(user_id);

CREATE TABLE IF NOT EXISTS questions (
    question_id     VARCHAR(64)  PRIMARY KEY,
    competency_id   VARCHAR(64)  NOT NULL REFERENCES competencies(competency_id) ON DELETE RESTRICT,
    difficulty      VARCHAR(8)   NOT NULL CHECK (difficulty IN ('easy','medium','hard')),
    source_document VARCHAR(300),            -- for MCQ-generation provenance (RAG engine, not this module)
    generated_by    VARCHAR(32)  NOT NULL DEFAULT 'llm_pipeline',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_questions_competency ON questions(competency_id);

CREATE TABLE IF NOT EXISTS assessment_attempts (
    id              BIGSERIAL PRIMARY KEY,
    user_id         VARCHAR(64) NOT NULL REFERENCES learners(user_id) ON DELETE CASCADE,
    question_id     VARCHAR(64) NOT NULL REFERENCES questions(question_id) ON DELETE RESTRICT,
    competency_id   VARCHAR(64) NOT NULL REFERENCES competencies(competency_id) ON DELETE RESTRICT,
    correct         BOOLEAN NOT NULL,
    attempted_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_attempts_user_competency ON assessment_attempts(user_id, competency_id);
CREATE INDEX IF NOT EXISTS idx_attempts_timestamp ON assessment_attempts(attempted_at);


CREATE TABLE IF NOT EXISTS competency_state (
    user_id             VARCHAR(64) NOT NULL REFERENCES learners(user_id) ON DELETE CASCADE,
    competency_id       VARCHAR(64) NOT NULL REFERENCES competencies(competency_id) ON DELETE RESTRICT,
    required_level      NUMERIC(2,1) NOT NULL,
    raw_mastery         NUMERIC(4,3) NOT NULL,
    confidence          NUMERIC(4,3) NOT NULL,
    recency_factor      NUMERIC(4,3) NOT NULL,
    effective_level     NUMERIC(4,3) NOT NULL,
    gap                 NUMERIC(4,3) NOT NULL,
    priority_weight     NUMERIC(4,3) NOT NULL,
    needs_more_evidence BOOLEAN NOT NULL DEFAULT false,
    evidence_count      INTEGER NOT NULL DEFAULT 0,
    last_demonstrated   TIMESTAMPTZ,
    reason              TEXT,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, competency_id)
);
CREATE INDEX IF NOT EXISTS idx_state_priority ON competency_state(user_id, priority_weight DESC);


CREATE TABLE IF NOT EXISTS competency_state_history (
    id                  BIGSERIAL PRIMARY KEY,
    user_id             VARCHAR(64) NOT NULL REFERENCES learners(user_id) ON DELETE CASCADE,
    competency_id       VARCHAR(64) NOT NULL REFERENCES competencies(competency_id) ON DELETE RESTRICT,
    raw_mastery         NUMERIC(4,3) NOT NULL,
    confidence          NUMERIC(4,3) NOT NULL,
    recency_factor      NUMERIC(4,3) NOT NULL,
    effective_level     NUMERIC(4,3) NOT NULL,
    gap                 NUMERIC(4,3) NOT NULL,
    priority_weight     NUMERIC(4,3) NOT NULL,
    triggering_event    VARCHAR(32) NOT NULL,  -- e.g. 'assessment_attempt', 'reassessment', 'manual_recalc'
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_history_user_competency_time
    ON competency_state_history(user_id, competency_id, recorded_at);


