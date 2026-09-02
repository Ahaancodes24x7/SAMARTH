"""
SYNTHETIC CONTROLLED EXPERIMENT.

Compares naive, weighted, and standard BKT estimates against the
synthetic latent skill generated only for experiment scoring. These
numbers are not real-world validation and must not be presented that way.
"""

import math
import os
import statistics
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.competency.mastery import MasteryEstimator
from app.synthetic.generate import generate_synthetic_learners


def naive_percentage(events, competency_id):
    relevant = [e for e in events if e.competency_id == competency_id]
    if not relevant:
        return 0.0
    return sum(1 for e in relevant if e.correct) / len(relevant)


def weighted_evidence_score(events, competency_id, recency_half_life_events=5):
    relevant = sorted(
        [e for e in events if e.competency_id == competency_id],
        key=lambda e: e.timestamp,
    )
    if not relevant:
        return 0.0
    weights = [2 ** (i / recency_half_life_events) for i in range(len(relevant))]
    total_weight = sum(weights)
    return sum(w * (1.0 if e.correct else 0.0) for w, e in zip(weights, relevant)) / total_weight


def bkt_score(events, competency_id):
    return MasteryEstimator().estimate(events, competency_id)


def _bucket(n_events):
    if n_events <= 2:
        return "1-2 attempts"
    if n_events <= 5:
        return "3-5 attempts"
    if n_events <= 10:
        return "6-10 attempts"
    return "10+ attempts"


def _metrics(rows, estimator_key):
    errors = [row[estimator_key] - row["truth"] for row in rows]
    mae = statistics.mean(abs(e) for e in errors)
    rmse = math.sqrt(statistics.mean(e * e for e in errors))
    brier = statistics.mean((row[estimator_key] - row["truth"]) ** 2 for row in rows)
    return mae, rmse, brier


def run_experiment(n_learners=60, seed=7):
    print(f"SYNTHETIC CONTROLLED EXPERIMENT: n_learners={n_learners}, seed={seed}")
    learners = generate_synthetic_learners(n=n_learners, seed=seed)

    rows = []
    for learner in learners:
        for competency_id, truth in learner["synthetic_ground_truth"].items():
            events = learner["events"]
            n_ev = len([e for e in events if e.competency_id == competency_id])
            if n_ev == 0:
                continue
            rows.append({
                "n_events": n_ev,
                "bucket": _bucket(n_ev),
                "truth": truth,
                "naive": naive_percentage(events, competency_id),
                "weighted": weighted_evidence_score(events, competency_id),
                "bkt": bkt_score(events, competency_id),
            })

    print("Overall metrics vs synthetic_ground_truth")
    print(f"{'model':<10} {'MAE':>8} {'RMSE':>8} {'Brier':>8}")
    for key in ["naive", "weighted", "bkt"]:
        mae, rmse, brier = _metrics(rows, key)
        print(f"{key:<10} {mae:>8.4f} {rmse:>8.4f} {brier:>8.4f}")

    print("\nBy evidence volume")
    print(f"{'bucket':<14} {'model':<10} {'n':>5} {'MAE':>8} {'RMSE':>8} {'Brier':>8}")
    for bucket in ["1-2 attempts", "3-5 attempts", "6-10 attempts", "10+ attempts"]:
        subset = [row for row in rows if row["bucket"] == bucket]
        if not subset:
            continue
        for key in ["naive", "weighted", "bkt"]:
            mae, rmse, brier = _metrics(subset, key)
            print(f"{bucket:<14} {key:<10} {len(subset):>5} {mae:>8.4f} {rmse:>8.4f} {brier:>8.4f}")

    return rows


if __name__ == "__main__":
    run_experiment()
