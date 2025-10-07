from collections import defaultdict
from dataclasses import dataclass
from typing import Any


@dataclass
class Record:
    id: str
    t: float
    question: str
    gold: str
    unknown_ok: bool
    pred: str
    abstained: bool
    correct: bool
    score: float


def score_item(answered: bool, correct: bool, t: float) -> float:
    if not answered:
        return 0.0
    if t >= 1.0:
        return 1.0 if correct else (-1.0) * float("inf")
    return 1.0 if correct else -t / (1.0 - t)


def aggregate(records: list[Record]) -> dict[float, dict[str, Any]]:
    by_t: dict[float, list[Record]] = defaultdict(list)
    for r in records:
        by_t[r.t].append(r)
    out: dict[float, dict[str, Any]] = {}
    for t, recs in by_t.items():
        n = len(recs)
        answered = sum(0 if r.abstained else 1 for r in recs)
        correct_ans = sum(1 for r in recs if (not r.abstained and r.correct))
        incorrect_ans = sum(1 for r in recs if (not r.abstained and not r.correct))
        coverage = answered / n if n else 0.0
        acc_cond = (correct_ans / answered) if answered else 0.0
        halluc_rate = (incorrect_ans / answered) if answered else 0.0
        total_score = sum(r.score for r in recs)
        out[t] = {
            "n": n,
            "coverage": coverage,
            "accuracy_conditioned_on_answering": acc_cond,
            "hallucination_rate_among_answers": halluc_rate,
            "avg_expected_score": total_score / n if n else 0.0,
            "answered": answered,
            "correct_answers": correct_ans,
            "incorrect_answers": incorrect_ans,
            "abstentions": n - answered,
        }
    return out


def behavior_checks(metrics: dict[float, dict[str, Any]]) -> dict[str, Any]:
    ts = sorted(metrics.keys())
    covs = [metrics[t]["coverage"] for t in ts]
    monotone_violations = sum(
        1 for i in range(1, len(covs)) if covs[i] > covs[i - 1] + 1e-6
    )
    return {
        "thresholds": ts,
        "coverage": covs,
        "monotonic_coverage_expected": True,
        "monotonicity_violations": monotone_violations,
    }
