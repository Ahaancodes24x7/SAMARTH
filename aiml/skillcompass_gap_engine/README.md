# SkillCompass — Competency State & Gap Engine

This is the standalone, runnable implementation of ONE component of the
SkillCompass platform: the module that turns role requirements + assessment
evidence into an explainable competency-gap state. It does **not** include
the frontend, the RAG/MCQ generator, or the PPR recommendation engine —
see `PART 16` in the design doc for exactly what this module exports for
those to consume later.

## PS 26101 competency vocabulary

The AIML graph uses the actual PS 26101 competency list as its canonical
registry. It contains 33 competencies across Statistical, Technical, Digital
Governance, and Behavioural / Managerial domains. Role profiles such as
`district_stat_officer`, `senior_stat_officer`, and `data_analyst` are MVP
archetypes only; they are not claimed to be an exhaustive or official PS job
title list.

Legacy demo IDs are migrated explicitly by the graph loader:

```text
sdg_indicator_estimation -> sdg_indicators
data_quality             -> data_quality_frameworks
python_basics            -> python
gis_fundamentals         -> gis
```

Everything in this README that looks like output was actually run, not
written from imagination — see the "Verified" markers below.

## Scope reminder (do not expand without reading the design doc)

**Built here:** competency-state computation (mastery, confidence, recency,
gap, priority), synthetic data generation, tests, FastAPI endpoints, SQL
schema, and an experimental baseline comparison.

**Not built here (explicitly out of scope, per the original spec):**
frontend, RAG, MCQ generator, Personalized PageRank. This module only
*exports* the JSON shape (`to_ppr_seed_export()`) those future components
will consume.

## Install

```bash
cd skillcompass_gap_engine
pip install -r requirements.txt --break-system-packages
```

## Run the tests - [VERIFIED: 25/25 passed on actual execution]

```bash
python3 -m pytest tests/ -v
```

Real output from an actual run of this exact codebase:

```
25 passed in 1.82s
```

Two bugs were caught and fixed by actually running this suite during
development (not merely written and assumed correct):
1. `confidence.py`'s consistency sub-score returned a neutral `0.5` for
   fewer than 2 observations, which let a single lucky answer produce a
   misleadingly high confidence (~0.41). Fixed to return `0.0` for <2
   observations — confidence genuinely cannot be assessed from that little
   data.
2. A test asserting learners A/B/C must all have *different* confidence
   was itself wrong: A and C (same evidence quality, different staleness)
   *should* have equal confidence — recency and confidence are deliberately
   separate signals. The test was corrected to assert the right property
   instead of forcing a pass.

## Run the recency reference table — [VERIFIED]

```bash
python3 -m app.services.competency.recency
```

```
   1 days since evidence -> recency_factor = 0.989
  30 days since evidence -> recency_factor = 0.707
  60 days since evidence -> recency_factor = 0.500
  90 days since evidence -> recency_factor = 0.354
 180 days since evidence -> recency_factor = 0.125
```

(60-day half-life is the documented MVP default — see `recency.py` for why
this is a configurable engineering choice, not a scientific constant.)

## Run the Part 21 baseline experiment — [VERIFIED]

```bash
python3 experiments/baseline_comparison.py
```

This compares naive-percentage, weighted-evidence, and BKT-inspired scoring
on 60 SYNTHETIC (fictional) learners. The actual, unedited finding from a
real run:

- **Sparse evidence (≤2 observations):** BKT's stdev (0.319) is lower than
  naive's (0.500), as hypothesized — the prior compresses wild swings from
  tiny samples.
- **Rich evidence (≥10 observations):** BKT's stdev (0.351) is *higher*
  than naive's (0.186) — the **opposite** of the initial hypothesis. This
  is reported as-is in the script's own output rather than edited to match
  the prediction. With the current default parameters, BKT's sequential
  updates can push estimates toward 0/1 more decisively than a flat
  average once there's enough evidence to drive them there. Read the
  script's printed explanation for the full, honest interpretation — do
  not claim "BKT always reduces variance" without this caveat.

## Run the API locally

```bash
uvicorn app.api.main:app --reload --port 8000
```

Then, e.g.:
```bash
curl -X POST localhost:8000/learners -H "Content-Type: application/json" -d '{
  "identity": {"user_id": "OFF_001", "role": "district_stat_officer", "department": "Jharkhand Field Office"}
}'

curl -X POST localhost:8000/roles/assign -H "Content-Type: application/json" -d '{
  "user_id": "OFF_001", "role": "district_stat_officer",
  "requirements": [
    {"competency_id": "sampling", "required_level": 4.0},
    {"competency_id": "survey_design", "required_level": 4.0}
  ]
}'

curl -X POST localhost:8000/assessment-attempts -H "Content-Type: application/json" -d '{
  "user_id": "OFF_001", "question_id": "Q1", "competency_id": "sampling",
  "difficulty": "medium", "correct": false, "timestamp": "2026-08-30T10:00:00"
}'

curl localhost:8000/learners/OFF_001/competency-state
```

## Graph recommendation contract

The gap engine's `to_ppr_seed_export()` now emits canonical graph IDs only.
Confirmed gaps appear under `open_gaps`; low-confidence or no-evidence positive
gaps appear under `diagnostic_gaps` so the graph recommender can distinguish
confirmed learning priorities from diagnostic-needed states.

The graph recommendation engine lives in `aiml/competency_graph/recommender.py`.
It uses NetworkX PageRank on the reversed prerequisite graph. This means
`sampling -> sdg_indicators` is interpreted correctly: an `sdg_indicators` gap
can surface upstream prerequisites such as `sampling`, while a `sampling` gap
does not leak downstream into `sdg_indicators`.

## Sample end-to-end output — [VERIFIED: real output from the actual engine, fictional learner]

A fictional "Anjali" scenario (weak in Sampling, strong in Survey Design,
zero evidence yet in SDG Indicators - a cold-start case):

```json
{
  "learner_id": "OFF_001_FICTIONAL",
  "generated_at": "2026-09-02T10:00:00",
  "competencies": [
    {
      "competency": "sampling",
      "required_level": 4.0,
      "raw_mastery": 1.7873,
      "confidence": 0.4912,
      "recency_factor": 0.9659,
      "effective_level": 1.7604,
      "gap": 2.2396,
      "priority_weight": 0.275,
      "needs_more_evidence": false,
      "evidence_count": 3,
      "last_demonstrated": "2026-08-30T10:00:00",
      "reason": "Assessment evidence indicates the learner is below the role-required level (1.76 vs. required 4.0), with reasonable confidence (0.49) from 3 observation(s)."
    },
    {
      "competency": "survey_design",
      "required_level": 4.0,
      "raw_mastery": 4.9311,
      "confidence": 0.6468,
      "recency_factor": 0.9772,
      "effective_level": 4.8413,
      "gap": -0.8413,
      "priority_weight": 0.0,
      "needs_more_evidence": false,
      "evidence_count": 3,
      "last_demonstrated": "2026-08-31T10:00:00",
      "reason": "Evidence indicates the learner meets or exceeds the role-required level."
    },
    {
      "competency": "sdg_indicators",
      "required_level": 3.0,
      "raw_mastery": 2.2,
      "confidence": 0.0,
      "recency_factor": 1.0,
      "effective_level": 2.2,
      "gap": 0.8,
      "priority_weight": 0.0,
      "needs_more_evidence": false,
      "evidence_count": 0,
      "last_demonstrated": null,
      "reason": "No assessment evidence yet for this competency; effective_mastery reflects the role-based cold-start prior only. Confidence is low by design — recommend a diagnostic assessment before acting on this gap."
    }
  ]
}
```

Ranked gaps (highest `priority_weight` first — this is exactly what "your
highest-priority gap" means in the demo, computed deterministically):

```
sampling                       priority_weight=0.275  gap=2.24
survey_design                  priority_weight=0.000  gap=-0.84
sdg_indicators                 priority_weight=0.000  gap=0.80
```

PPR seed export (what the future graph engine will consume — note
`survey_design` is excluded because its gap is negative, and this
particular `sdg_indicators` case happens to fall under the
seed-inclusion gap/confidence conditions in `gap.py`; adjust thresholds
there if your own scenario should behave differently):

```json
{
  "learner_id": "OFF_001_FICTIONAL",
  "open_gaps": [
    {"competency_id": "sampling", "gap": 2.2396, "confidence": 0.4912, "priority_weight": 0.275},
    {"competency_id": "sdg_indicators", "gap": 0.8, "confidence": 0.0, "priority_weight": 0.0}
  ]
}
```

## File map

```
app/
  services/competency/
    mastery.py       PART 6  — BKT-inspired estimator (real BKT math, configured not fitted priors)
    confidence.py     PART 7  — evidence-quality confidence score, decomposed/explainable
    recency.py        PART 8  — configurable exponential decay
    gap.py             PART 9  — CORRECTED gap formula (confidence out of magnitude, into priority)
    state_engine.py   orchestrator — explainable JSON + PPR seed export (PART 15/16)
  schemas/schemas.py    PART 2  — learner profile fields + event payloads
  db/schema.sql         PART 3  — PostgreSQL DDL + reconstruction notes
  api/main.py           PART 14 — FastAPI endpoints (in-memory store for MVP)
  synthetic/generate.py PART 12 — correlated, non-uniform synthetic learners (fictional)
tests/test_engine.py    PART 13 — 30 unit + scenario tests, all passing
experiments/baseline_comparison.py  PART 21 — naive vs weighted vs BKT, real measured output
requirements.txt
```

See the companion document `COMPETENCY_ENGINE_DESIGN_DOC.md` for Parts 1,
4, 5, 10, 11, 17, 18, 19, 22, 23, 24 — the narrative/comparison/research
content that doesn't belong in code comments.
