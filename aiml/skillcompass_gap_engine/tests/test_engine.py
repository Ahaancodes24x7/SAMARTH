import random
from datetime import datetime, timedelta

import pytest

from app.services.competency.bkt_calibration import BKTObservation, fit_bkt, normalize_bkt_sequences
from app.services.competency.confidence import ConfidenceWeights, compute_confidence
from app.services.competency.gap import compute_gap_for_competency
from app.services.competency.mastery import (
    AssessmentEvent,
    BKTParams,
    MasteryEstimator,
    apply_learning_transition,
    bkt_observation_update,
    bkt_update,
)
from app.services.competency.recency import DecayParams, recency_factor
from app.services.competency.state_engine import CompetencyStateEngine
from app.synthetic.generate import generate_synthetic_learners

NOW = datetime(2026, 9, 1, 12, 0, 0)


def ev(qid, comp, correct, days_ago=0, difficulty="medium", learning_opportunity=False):
    return AssessmentEvent(
        question_id=qid,
        competency_id=comp,
        difficulty=difficulty,
        correct=correct,
        timestamp=NOW - timedelta(days=days_ago),
        learning_opportunity=learning_opportunity,
    )


class TestMasteryUpdate:
    def test_canonical_bkt_correct_update_without_transition(self):
        params = BKTParams(p_l0=0.3, p_t=0.1, p_g=0.2, p_s=0.1)
        expected = (0.3 * 0.9) / ((0.3 * 0.9) + (0.7 * 0.2))
        assert bkt_observation_update(0.3, True, params) == pytest.approx(expected)
        assert bkt_update(0.3, True, params, learning_opportunity=False) == pytest.approx(expected)

    def test_canonical_bkt_incorrect_update_without_transition(self):
        params = BKTParams(p_l0=0.3, p_t=0.1, p_g=0.2, p_s=0.1)
        expected = (0.3 * 0.1) / ((0.3 * 0.1) + (0.7 * 0.8))
        assert bkt_observation_update(0.3, False, params) == pytest.approx(expected)

    def test_learning_transition_semantics(self):
        params = BKTParams(p_t=0.25)
        observed = bkt_observation_update(0.3, True, params)
        expected = observed + (1.0 - observed) * 0.25
        assert bkt_update(0.3, True, params, learning_opportunity=True) == pytest.approx(expected)
        assert apply_learning_transition(observed, params) == pytest.approx(expected)

    def test_pure_assessment_does_not_apply_transition(self):
        params = BKTParams(p_t=0.99)
        pure = bkt_update(0.3, True, params, learning_opportunity=False)
        practice = bkt_update(0.3, True, params, learning_opportunity=True)
        assert practice > pure

    def test_parameter_object_version_is_exposed(self):
        params = BKTParams(p_l0=0.4, version="pilot-v2", source="pilot_calibrated")
        estimator = MasteryEstimator(params)
        assert estimator.params.version == "pilot-v2"
        assert estimator.estimate([], "sampling") == pytest.approx(0.4)

    def test_repeated_correct_answers_converge_upward(self):
        estimator = MasteryEstimator()
        events = [ev(f"q{i}", "sampling", True, days_ago=i) for i in range(10)]
        mastery = estimator.estimate(events, "sampling")
        assert mastery > 0.95

    def test_repeated_incorrect_answers_converge_downward(self):
        estimator = MasteryEstimator()
        events = [ev(f"q{i}", "sampling", False, days_ago=i) for i in range(10)]
        mastery = estimator.estimate(events, "sampling")
        assert mastery < 0.01

    def test_deterministic_same_input_same_output(self):
        params = BKTParams()
        assert bkt_update(0.5, True, params) == bkt_update(0.5, True, params)

    def test_invalid_params_raise(self):
        with pytest.raises(ValueError):
            BKTParams(p_g=1.5)


class TestCalibration:
    def _simulate(self, params, n_sequences=500, length=20, seed=11):
        rng = random.Random(seed)
        sequences = []
        for _ in range(n_sequences):
            learned = rng.random() < params.p_l0
            seq = []
            for _ in range(length):
                correct = rng.random() < (1.0 - params.p_s if learned else params.p_g)
                seq.append(BKTObservation(correct=correct, learning_opportunity=True))
                if not learned and rng.random() < params.p_t:
                    learned = True
            sequences.append(seq)
        return sequences

    def test_bkt_calibration_recovers_known_synthetic_params_approximately(self):
        true_params = BKTParams(p_l0=0.25, p_t=0.18, p_g=0.16, p_s=0.08)
        sequences = self._simulate(true_params)
        fitted = fit_bkt(
            sequences,
            initial_params=BKTParams(p_l0=0.35, p_t=0.12, p_g=0.2, p_s=0.1),
            max_iter=80,
            source="synthetic_experiment",
        )
        assert fitted.source == "synthetic_experiment"
        assert fitted.p_l0 == pytest.approx(true_params.p_l0, abs=0.12)
        assert fitted.p_t == pytest.approx(true_params.p_t, abs=0.08)
        assert fitted.p_g == pytest.approx(true_params.p_g, abs=0.08)
        assert fitted.p_s == pytest.approx(true_params.p_s, abs=0.06)

    def test_backend_rows_normalize_to_sequences(self):
        rows = [
            {"learner_id": "u1", "competency_id": "c", "correct": True, "timestamp": NOW},
            {"learner_id": "u1", "competency_id": "c", "correct": False, "timestamp": NOW + timedelta(seconds=1)},
        ]
        sequences = normalize_bkt_sequences(rows)
        assert list(sequences) == ["c"]
        assert [obs.correct for obs in sequences["c"][0]] == [True, False]


class TestConfidence:
    def test_zero_evidence_gives_zero_confidence(self):
        assert compute_confidence([], "sampling") == 0.0

    def test_more_evidence_increases_confidence(self):
        few = [ev(f"q{i}", "s", True) for i in range(2)]
        many = [ev(f"q{i}", "s", True) for i in range(15)]
        assert compute_confidence(many, "s") > compute_confidence(few, "s")

    def test_repeated_same_question_does_not_inflate_confidence_like_distinct_ones(self):
        repeated = [ev("q1", "s", True) for _ in range(10)]
        distinct = [ev(f"q{i}", "s", True) for i in range(10)]
        assert compute_confidence(distinct, "s") > compute_confidence(repeated, "s")

    def test_sequence_stability_distinguishes_same_mean_variance(self):
        blocky = [ev(f"b{i}", "s", i < 5, days_ago=10 - i) for i in range(10)]
        alternating = [ev(f"a{i}", "s", i % 2 == 0, days_ago=10 - i) for i in range(10)]
        assert compute_confidence(blocky, "s") > compute_confidence(alternating, "s")

    def test_weights_must_sum_to_one(self):
        with pytest.raises(ValueError):
            ConfidenceWeights(w_volume=0.9, w_diversity=0.9, w_consistency=0.1, w_difficulty_cov=0.1)


class TestRecency:
    def test_zero_days_gives_factor_1(self):
        assert recency_factor(0) == pytest.approx(1.0)

    def test_factor_at_half_life_is_half(self):
        params = DecayParams(half_life_days=60.0)
        assert recency_factor(60, params) == pytest.approx(0.5, abs=1e-6)

    def test_negative_days_raises(self):
        with pytest.raises(ValueError):
            recency_factor(-5)

    def test_stale_evidence_triggers_reassessment_instead_of_mastery_collapse(self):
        fresh = [ev(f"q{i}", "sampling", True, days_ago=1) for i in range(8)]
        stale = [ev(f"q{i}", "sampling", True, days_ago=180) for i in range(8)]
        fresh_result = compute_gap_for_competency(fresh, "sampling", required_level=4.0, now=NOW)
        stale_result = compute_gap_for_competency(stale, "sampling", required_level=4.0, now=NOW)
        assert stale_result.mastery_probability == pytest.approx(fresh_result.mastery_probability)
        assert stale_result.needs_reassessment is True
        assert stale_result.status == "REASSESSMENT_REQUIRED"


class TestGapCalculation:
    def test_uncertainty_vs_confirmed_gap(self):
        uncertain = compute_gap_for_competency([ev("q1", "sampling", False)], "sampling", 4.5, now=NOW)
        confirmed = compute_gap_for_competency(
            [ev(f"q{i}", "sampling", False, difficulty=["easy", "medium", "hard"][i % 3]) for i in range(18)],
            "sampling",
            4.5,
            now=NOW,
        )
        assert uncertain.status == "UNCERTAIN_MORE_EVIDENCE"
        assert confirmed.status == "CONFIRMED_GAP"
        assert confirmed.priority_weight > uncertain.priority_weight

    def test_no_gap(self):
        events = [ev(f"q{i}", "sampling", True) for i in range(10)]
        result = compute_gap_for_competency(events, "sampling", required_level=2.0, now=NOW)
        assert result.status == "NO_GAP"
        assert result.gap <= 0

    def test_low_confidence_does_not_inflate_gap_magnitude(self):
        repeated_question = [ev("q1", "sampling", True, days_ago=1) for _ in range(5)]
        distinct_questions = [ev(f"q{i}", "sampling", True, days_ago=1) for i in range(5)]
        low_div_result = compute_gap_for_competency(repeated_question, "sampling", 4.0, now=NOW)
        high_div_result = compute_gap_for_competency(distinct_questions, "sampling", 4.0, now=NOW)
        assert low_div_result.confidence < high_div_result.confidence
        assert low_div_result.gap == pytest.approx(high_div_result.gap, abs=1e-9)
        assert low_div_result.effective_mastery == pytest.approx(high_div_result.effective_mastery, abs=1e-9)

    def test_ppr_seed_excludes_uncertain_zero_gap_and_stale(self):
        engine = CompetencyStateEngine()
        required = {"uncertain": 4.5, "zero": 2.0, "stale": 4.0, "confirmed": 4.5}
        events = [
            ev("u1", "uncertain", False),
            *[ev(f"z{i}", "zero", True) for i in range(12)],
            *[ev(f"s{i}", "stale", False, days_ago=180) for i in range(12)],
            *[ev(f"c{i}", "confirmed", False, difficulty=["easy", "medium", "hard"][i % 3]) for i in range(18)],
        ]
        export = engine.compute_state("u", required, events, now=NOW).to_ppr_seed_export()
        assert [item["competency_id"] for item in export["open_gaps"]] == ["confirmed"]


class TestSynthetic:
    def test_synthetic_ground_truth_is_preserved_but_not_on_events(self):
        learner = generate_synthetic_learners(n=1, seed=3)[0]
        assert "synthetic_ground_truth" in learner
        assert learner["synthetic_ground_truth"]
        assert all(not hasattr(event, "synthetic_ground_truth") for event in learner["events"])
