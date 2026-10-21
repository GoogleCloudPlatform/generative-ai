#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Dataset quality benchmarks for DiffusionGemma on vLLM."""

import json
import math
import statistics
from typing import Any

import benchmark_load
import diffusiongemma_client

# Top 20 customer support intents from PolyAI/banking77 (fits single-token A-T).
BANKING77_TOP20_INTENTS: dict[str, str] = {
    "card_payment_fee_charged": "Fee charged on a card payment",
    "direct_debit_payment_not_recognised": "Unrecognized direct debit charge",
    "balance_not_updated_after_cheque_or_cash_deposit": (
        "Balance not updated after cheque or cash deposit"
    ),
    "wrong_amount_of_cash_received": "ATM dispensed wrong amount of cash",
    "cash_withdrawal_charge": "Extra fee charged for ATM cash withdrawal",
    "transaction_charged_twice": "Duplicate charge for the same transaction",
    "declined_cash_withdrawal": "ATM cash withdrawal was declined",
    "transfer_fee_charged": "Unexpected fee charged on a bank transfer",
    "transfer_not_received_by_recipient": (
        "Bank transfer has not arrived at recipient account"
    ),
    "balance_not_updated_after_bank_transfer": (
        "Account balance not updated after receiving transfer"
    ),
    "request_refund": "Customer requesting a refund for a payment",
    "card_payment_not_recognised": "Unrecognized card transaction on statement",
    "card_payment_wrong_exchange_rate": (
        "Wrong foreign exchange rate applied to card payment"
    ),
    "extra_charge_on_statement": "Unexpected extra charge on statement",
    "wrong_exchange_rate_for_cash_withdrawal": (
        "Incorrect exchange rate on foreign ATM withdrawal"
    ),
    "beneficiary_not_allowed": "Unable to add or pay a transfer beneficiary",
    "pending_cash_withdrawal": "Cash withdrawal still showing as pending",
    "reverted_card_payment?": "Card payment was reverted or cancelled",
    "cancel_transfer": "Request to cancel an outgoing bank transfer",
    "card_arrival": "Tracking delivery of a new or replacement card",
}

AG_NEWS_CRITERIA: dict[str, str] = {
    "World": "International politics, diplomacy, elections, global news",
    "Sports": "Athletic competitions, teams, tournaments, players, scores",
    "Business": "Markets, companies, economy, finance, corporate trade",
    "Sci/Tech": "Science, software, hardware, space, technology research",
}

SST5_CRITERIA: list[str] = [
    "very negative - terrible, harsh criticism, complete failure",
    "negative - disappointing, flawed, generally unfavorable",
    "neutral - mixed, factual, neither clearly positive nor negative",
    "positive - good, enjoyable, favorable recommendation",
    "very positive - outstanding, masterpiece, enthusiastic praise",
]

DATASET_TASK_DESCRIPTIONS: dict[str, str] = {
    "banking77": "choice (77 intents)",
    "ag_news": "choice (4 topics)",
    "boolq": "boolean (true/false)",
    "sst5": "score (1..5 sentiment)",
}

QUALITY_METRIC_COLUMNS: tuple[str, ...] = (
    "accuracy",
    "macro_f1",
    "mean_confidence",
    "brier_score",
    "mae",
    "rmse",
    "spearman",
    "median_ms",
)


def _select_samples(ds: Any, num_samples: int | None) -> Any:
    """Selects up to num_samples rows, or the full dataset if <= 0 or None."""
    if num_samples is None or num_samples <= 0 or num_samples >= len(ds):
        return ds
    return ds.select(range(num_samples))


def _compute_macro_f1(
    y_true: list[str], y_pred: list[str], labels: list[str]
) -> float:
    """Computes unweighted macro-F1 across all target class labels."""
    if not y_true or not labels:
        return 0.0
    f1_scores: list[float] = []
    for label in labels:
        tp = sum(
            1 for yt, yp in zip(y_true, y_pred) if yt == label and yp == label
        )
        fp = sum(
            1 for yt, yp in zip(y_true, y_pred) if yt != label and yp == label
        )
        fn = sum(
            1 for yt, yp in zip(y_true, y_pred) if yt == label and yp != label
        )
        if tp == 0 and fp == 0 and fn == 0:
            continue
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        f1_scores.append(f1)
    return statistics.mean(f1_scores) if f1_scores else 0.0


def _compute_spearman_correlation(x: list[float], y: list[float]) -> float:
    """Computes Spearman rank correlation with average tie-rank handling."""
    n = len(x)
    if n < 2 or len(y) != n:
        return 0.0

    def _ranks(vals: list[float]) -> list[float]:
        indexed = sorted(enumerate(vals), key=lambda p: p[1])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and indexed[j + 1][1] == indexed[i][1]:
                j += 1
            avg_rank = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[indexed[k][0]] = avg_rank
            i = j + 1
        return ranks

    rx = _ranks(x)
    ry = _ranks(y)
    mx = statistics.mean(rx)
    my = statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den_x = math.sqrt(sum((a - mx) ** 2 for a in rx))
    den_y = math.sqrt(sum((b - my) ** 2 for b in ry))
    if den_x == 0.0 or den_y == 0.0:
        return 0.0
    return num / (den_x * den_y)


def _evaluate_choice_dataset(
    dataset_prefix: str,
    field_name: str,
    instructions: str,
    criteria: dict[str, str],
    samples: list[tuple[str, str]],
    client: diffusiongemma_client.DiffusionGemmaClient,
    url: str,
    token: str,
    concurrency: int,
    model: str,
) -> dict[str, float]:
    """Runs concurrent choice evaluation and returns accuracy, F1, and ms."""
    schema = {
        field_name: {
            "type": "choice",
            "instructions": instructions,
            "criteria": criteria,
        }
    }
    compiled = client.build_canvas(schema)
    payloads = [
        json.dumps(client.build_request(text, compiled, model=model)).encode(
            "utf-8"
        )
        for text, _ in samples
    ]
    raw_list, latencies, _ = benchmark_load._run_async(
        benchmark_load._execute_concurrent_requests_async(
            url, token, payloads, concurrency
        )
    )
    y_true: list[str] = []
    y_pred: list[str] = []
    confs: list[float] = []

    for (_, truth), raw in zip(samples, raw_list):
        if raw is None:
            continue
        parsed = client.parse_response(raw, compiled)
        ans = parsed["answers"][field_name]
        y_true.append(truth)
        y_pred.append(ans["choice"])
        confs.append(ans["confidence"])

    acc = (
        sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp) / len(y_true)
        if y_true
        else 0.0
    )
    f1 = _compute_macro_f1(y_true, y_pred, list(criteria.keys()))
    return {
        f"{dataset_prefix}_accuracy": round(acc, 4),
        f"{dataset_prefix}_macro_f1": round(f1, 4),
        f"{dataset_prefix}_mean_confidence": (
            round(statistics.mean(confs), 4) if confs else 0.0
        ),
        f"{dataset_prefix}_median_ms": (
            round(statistics.median(latencies), 2) if latencies else 0.0
        ),
    }


def evaluate_banking77(
    client: diffusiongemma_client.DiffusionGemmaClient,
    url: str,
    token: str,
    num_samples: int,
    concurrency: int,
    model: str,
) -> dict[str, float]:
    """Evaluates 20-way intent routing on legacy-datasets/banking77."""
    from datasets import load_dataset

    # Shuffle deterministically so all 20 intents are sampled evenly.
    ds = load_dataset("legacy-datasets/banking77", split="test").shuffle(
        seed=42
    )
    label_names = ds.features["label"].names
    allowed = set(BANKING77_TOP20_INTENTS.keys())

    # Filter test rows belonging to the 20 target intents.
    samples: list[tuple[str, str]] = []
    for row in ds:
        intent = label_names[row["label"]]
        if intent in allowed:
            samples.append((row["text"], intent))
            if num_samples and num_samples > 0 and len(samples) >= num_samples:
                break

    return _evaluate_choice_dataset(
        dataset_prefix="banking77",
        field_name="intent",
        instructions=(
            "Which banking support intent best matches the customer query?"
        ),
        criteria=BANKING77_TOP20_INTENTS,
        samples=samples,
        client=client,
        url=url,
        token=token,
        concurrency=concurrency,
        model=model,
    )


def evaluate_ag_news(
    client: diffusiongemma_client.DiffusionGemmaClient,
    url: str,
    token: str,
    num_samples: int,
    concurrency: int,
    model: str,
) -> dict[str, float]:
    """Evaluates 4-way topic classification on fancyzhx/ag_news."""
    from datasets import load_dataset

    # Shuffle deterministically before selecting num_samples.
    ds = load_dataset("fancyzhx/ag_news", split="test").shuffle(seed=42)
    label_map = list(AG_NEWS_CRITERIA.keys())
    samples = [
        (row["text"], label_map[int(row["label"])])
        for row in _select_samples(ds, num_samples)
    ]
    return _evaluate_choice_dataset(
        dataset_prefix="ag_news",
        field_name="topic",
        instructions="Classify the news article into its primary topic.",
        criteria=AG_NEWS_CRITERIA,
        samples=samples,
        client=client,
        url=url,
        token=token,
        concurrency=concurrency,
        model=model,
    )


def evaluate_boolq(
    client: diffusiongemma_client.DiffusionGemmaClient,
    url: str,
    token: str,
    num_samples: int,
    concurrency: int,
    model: str,
) -> dict[str, float]:
    """Evaluates boolean reading comprehension on google/boolq."""
    from datasets import load_dataset

    # Shuffle deterministically before selecting num_samples.
    ds = load_dataset("google/boolq", split="validation").shuffle(seed=42)
    rows = list(_select_samples(ds, num_samples))

    payloads: list[bytes] = []
    compiled_list: list[dict[str, Any]] = []
    truths: list[bool] = []

    for row in rows:
        schema = {
            "answer": {
                "type": "boolean",
                "instructions": f"{row['question']}?",
            }
        }
        compiled = client.build_canvas(schema)
        req = client.build_request(row["passage"], compiled, model=model)
        payloads.append(json.dumps(req).encode("utf-8"))
        compiled_list.append(compiled)
        truths.append(bool(row["answer"]))

    raw_list, latencies, _ = benchmark_load._run_async(
        benchmark_load._execute_concurrent_requests_async(
            url, token, payloads, concurrency
        )
    )
    correct = 0
    brier_terms: list[float] = []
    y_true_str: list[str] = []
    y_pred_str: list[str] = []

    for truth, compiled, raw in zip(truths, compiled_list, raw_list):
        if raw is None:
            continue
        parsed = client.parse_response(raw, compiled)
        prob_true = float(parsed["answers"]["answer"]["boolean"])
        pred_bool = prob_true >= 0.5
        if pred_bool == truth:
            correct += 1
        y_val = 1.0 if truth else 0.0
        brier_terms.append((prob_true - y_val) ** 2)
        y_true_str.append(str(truth))
        y_pred_str.append(str(pred_bool))

    total = len(brier_terms)
    acc = (correct / total) if total else 0.0
    brier = statistics.mean(brier_terms) if brier_terms else 0.0
    f1 = _compute_macro_f1(y_true_str, y_pred_str, ["True", "False"])
    return {
        "boolq_accuracy": round(acc, 4),
        "boolq_macro_f1": round(f1, 4),
        "boolq_brier_score": round(brier, 4),
        "boolq_median_ms": (
            round(statistics.median(latencies), 2) if latencies else 0.0
        ),
    }


def evaluate_sst5(
    client: diffusiongemma_client.DiffusionGemmaClient,
    url: str,
    token: str,
    num_samples: int,
    concurrency: int,
    model: str,
) -> dict[str, float]:
    """Evaluates 5-level ordinal sentiment rating on SetFit/sst5."""
    from datasets import load_dataset

    # Shuffle deterministically before selecting num_samples.
    ds = load_dataset("SetFit/sst5", split="test").shuffle(seed=42)
    samples = [
        (row["text"], float(row["label"]))
        for row in _select_samples(ds, num_samples)
    ]

    schema = {
        "sentiment": {
            "type": "score",
            "instructions": (
                "Rate the sentiment of this review from 0 (very negative)"
                " to 4 (very positive)."
            ),
            "criteria": SST5_CRITERIA,
        }
    }
    compiled = client.build_canvas(schema)
    payloads = [
        json.dumps(client.build_request(text, compiled, model=model)).encode(
            "utf-8"
        )
        for text, _ in samples
    ]

    raw_list, latencies, _ = benchmark_load._run_async(
        benchmark_load._execute_concurrent_requests_async(
            url, token, payloads, concurrency
        )
    )
    y_true: list[float] = []
    y_pred: list[float] = []

    for (_, truth), raw in zip(samples, raw_list):
        if raw is None:
            continue
        parsed = client.parse_response(raw, compiled)
        score = float(parsed["answers"]["sentiment"]["score"])
        y_true.append(truth)
        y_pred.append(score)

    abs_errs = [abs(yt - yp) for yt, yp in zip(y_true, y_pred)]
    sq_errs = [(yt - yp) ** 2 for yt, yp in zip(y_true, y_pred)]
    mae = statistics.mean(abs_errs) if abs_errs else 0.0
    rmse = math.sqrt(statistics.mean(sq_errs)) if sq_errs else 0.0
    spearman = _compute_spearman_correlation(y_true, y_pred)
    return {
        "sst5_mae": round(mae, 4),
        "sst5_rmse": round(rmse, 4),
        "sst5_spearman": round(spearman, 4),
        "sst5_median_ms": (
            round(statistics.median(latencies), 2) if latencies else 0.0
        ),
    }


def build_quality_summary_rows(
    quality_metrics: dict[str, float],
) -> list[dict[str, Any]]:
    """Groups flat '<dataset>_<metric>' keys into one summary row per dataset."""
    by_dataset: dict[str, dict[str, Any]] = {}
    for full_key, val in quality_metrics.items():
        matched_ds: str | None = None
        metric_name = full_key
        for ds in DATASET_TASK_DESCRIPTIONS:
            prefix = f"{ds}_"
            if full_key.startswith(prefix):
                matched_ds = ds
                metric_name = full_key[len(prefix) :]
                break
        if matched_ds is None:
            parts = full_key.split("_", 1)
            matched_ds = parts[0]
            metric_name = parts[1] if len(parts) > 1 else full_key
        row = by_dataset.setdefault(
            matched_ds,
            {
                "dataset": matched_ds,
                "task_type": DATASET_TASK_DESCRIPTIONS.get(
                    matched_ds, "custom"
                ),
                **{col: None for col in QUALITY_METRIC_COLUMNS},
            },
        )
        row[metric_name] = val

    ordered_datasets = [
        ds for ds in DATASET_TASK_DESCRIPTIONS if ds in by_dataset
    ] + [ds for ds in by_dataset if ds not in DATASET_TASK_DESCRIPTIONS]
    return [by_dataset[ds] for ds in ordered_datasets]
