from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np

from .mastery import AssessmentEvent, BKTParameters


@dataclass(frozen=True)
class BKTObservation:
    correct: bool
    learning_opportunity: bool = True


def normalize_bkt_sequences(
    rows: Iterable[Mapping],
    learner_key: str = "learner_id",
    competency_key: str = "competency_id",
) -> Dict[str, List[List[BKTObservation]]]:
    grouped: Dict[Tuple[str, str], List[Mapping]] = {}
    for row in rows:
        grouped.setdefault((row[learner_key], row[competency_key]), []).append(row)

    sequences: Dict[str, List[List[BKTObservation]]] = {}
    for (_, competency_id), items in grouped.items():
        ordered = sorted(items, key=lambda r: r.get("timestamp") or datetime.min)
        sequences.setdefault(competency_id, []).append([
            BKTObservation(
                correct=bool(item["correct"]),
                learning_opportunity=bool(item.get("learning_opportunity", True)),
            )
            for item in ordered
        ])
    return sequences


def events_to_bkt_sequences(events: Sequence[AssessmentEvent]) -> Dict[str, List[List[BKTObservation]]]:
    rows = [
        {
            "learner_id": "single_learner",
            "competency_id": event.competency_id,
            "correct": event.correct,
            "timestamp": event.timestamp,
            "learning_opportunity": event.learning_opportunity,
        }
        for event in events
    ]
    return normalize_bkt_sequences(rows)


def _as_observations(sequence: Sequence[bool | BKTObservation]) -> List[BKTObservation]:
    return [
        item if isinstance(item, BKTObservation) else BKTObservation(correct=bool(item))
        for item in sequence
    ]


def _forward_backward(sequence: List[BKTObservation], params: BKTParameters):
    n = len(sequence)
    alpha = np.zeros((n, 2), dtype=float)
    beta = np.ones((n, 2), dtype=float)
    scales = np.ones(n, dtype=float)

    def emit(obs: BKTObservation) -> np.ndarray:
        if obs.correct:
            return np.array([params.p_g, 1.0 - params.p_s], dtype=float)
        return np.array([1.0 - params.p_g, params.p_s], dtype=float)

    def trans(obs: BKTObservation) -> np.ndarray:
        if obs.learning_opportunity:
            return np.array([[1.0 - params.p_t, params.p_t], [0.0, 1.0]], dtype=float)
        return np.eye(2, dtype=float)

    alpha[0] = np.array([1.0 - params.p_l0, params.p_l0], dtype=float) * emit(sequence[0])
    scales[0] = max(alpha[0].sum(), 1e-12)
    alpha[0] /= scales[0]

    for t in range(1, n):
        alpha[t] = alpha[t - 1].dot(trans(sequence[t - 1])) * emit(sequence[t])
        scales[t] = max(alpha[t].sum(), 1e-12)
        alpha[t] /= scales[t]

    for t in range(n - 2, -1, -1):
        beta[t] = trans(sequence[t]).dot(emit(sequence[t + 1]) * beta[t + 1])
        beta[t] /= scales[t + 1]

    return alpha, beta, emit, trans, float(np.log(scales).sum())


def _em_step(sequences: List[List[BKTObservation]], params: BKTParameters):
    init_learned = 0.0
    learned_correct = learned_total = 0.0
    unlearned_correct = unlearned_total = 0.0
    learned_transitions = unlearned_opportunities = 0.0
    log_likelihood = 0.0

    for sequence in sequences:
        if not sequence:
            continue
        alpha, beta, emit, trans, seq_ll = _forward_backward(sequence, params)
        log_likelihood += seq_ll
        gamma = alpha * beta
        gamma /= np.maximum(gamma.sum(axis=1, keepdims=True), 1e-12)

        init_learned += gamma[0, 1]
        for t, obs in enumerate(sequence):
            learned_total += gamma[t, 1]
            unlearned_total += gamma[t, 0]
            if obs.correct:
                learned_correct += gamma[t, 1]
                unlearned_correct += gamma[t, 0]

        for t in range(len(sequence) - 1):
            if not sequence[t].learning_opportunity:
                continue
            xi = (
                alpha[t][:, None]
                * trans(sequence[t])
                * (emit(sequence[t + 1]) * beta[t + 1])[None, :]
            )
            xi /= max(xi.sum(), 1e-12)
            learned_transitions += xi[0, 1]
            unlearned_opportunities += gamma[t, 0]

    count = max(len([s for s in sequences if s]), 1)
    eps = 1e-5

    # EM/Baum-Welch maximum-likelihood fitting for HMM-style BKT parameters.
    # See pyBKT/standard BKT implementations for this established fitting family.
    fitted = BKTParameters(
        p_l0=float(np.clip(init_learned / count, eps, 1.0 - eps)),
        p_t=float(np.clip(learned_transitions / max(unlearned_opportunities, eps), eps, 1.0 - eps)),
        p_g=float(np.clip(unlearned_correct / max(unlearned_total, eps), eps, 1.0 - eps)),
        p_s=float(np.clip(1.0 - learned_correct / max(learned_total, eps), eps, 1.0 - eps)),
        version="em-fit",
        source="calibrated",
    )
    return fitted, log_likelihood


def fit_bkt(
    response_sequences: Sequence[Sequence[bool | BKTObservation]],
    initial_params: BKTParameters | None = None,
    max_iter: int = 100,
    tol: float = 1e-5,
    version: str = "bkt-em-fit",
    source: str = "pilot_calibrated",
) -> BKTParameters:
    sequences = [_as_observations(sequence) for sequence in response_sequences if sequence]
    if not sequences:
        raise ValueError("fit_bkt requires at least one non-empty response sequence")

    params = initial_params or BKTParameters()
    prev_ll = -float("inf")
    for _ in range(max_iter):
        params, ll = _em_step(sequences, params)
        if abs(ll - prev_ll) < tol:
            break
        prev_ll = ll

    return BKTParameters(
        p_l0=params.p_l0,
        p_t=params.p_t,
        p_g=params.p_g,
        p_s=params.p_s,
        version=version,
        source=source,
    )
