import asyncio
import csv
import json
import os
from collections.abc import Sequence
from typing import Any

from tqdm.auto import tqdm

from gemhall.judge import judge_validity as judge_validity_exact
from gemhall.judge_llm import AsyncLLMJudge, LLMJudge
from gemhall.metrics import Record, aggregate, behavior_checks, score_item
from gemhall.prompts import build_conf_prompt, is_idk
from gemhall.runner import AsyncGeminiRunner, GeminiRunner


def load_data_csv(path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def _write_artifacts(records: list[Record], out_dir: str) -> dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    # results.csv
    results_csv = os.path.join(out_dir, "results.csv")
    with open(results_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "id",
                "t",
                "question",
                "gold",
                "unknown_ok",
                "pred",
                "abstained",
                "correct",
                "score",
            ]
        )
        for r in records:
            w.writerow(
                [
                    r.id,
                    r.t,
                    r.question,
                    r.gold,
                    int(r.unknown_ok),
                    r.pred,
                    int(r.abstained),
                    int(r.correct),
                    r.score,
                ]
            )

    # metrics/behavior
    metrics = aggregate(records)
    metrics_json = os.path.join(out_dir, "metrics.json")
    with open(metrics_json, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    behavior = behavior_checks(metrics)
    behavior_json = os.path.join(out_dir, "behavior.json")
    with open(behavior_json, "w", encoding="utf-8") as f:
        json.dump(behavior, f, indent=2)

    # plot with labels
    out_png = ""
    try:
        import matplotlib.pyplot as plt

        ts = sorted(metrics.keys())
        cov = [metrics[t]["coverage"] for t in ts]
        acc = [metrics[t]["accuracy_conditioned_on_answering"] for t in ts]
        plt.figure()
        plt.plot(cov, acc, marker="o")
        for x, y, tval in zip(cov, acc, ts, strict=False):
            try:
                label = f"t={tval:g}"
            except Exception:
                label = f"t={tval}"
            plt.annotate(
                label, (x, y), textcoords="offset points", xytext=(6, 6), ha="left"
            )
        plt.xlabel("Coverage (answered fraction)")
        plt.ylabel("Conditional accuracy")
        plt.title("Risk–coverage curve (higher is better)")
        out_png = os.path.join(out_dir, "rc_curve.png")
        plt.savefig(out_png, bbox_inches="tight")
        plt.close()
    except Exception:
        pass

    # report.md
    report_md = os.path.join(out_dir, "report.md")
    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# Hallucination Evaluation Report\n\n")
        f.write("## Summary\n")
        for t in sorted(metrics.keys()):
            m = metrics[t]
            f.write(
                f"- t={t}: coverage={m['coverage']:.3f}, cond_acc={m['accuracy_conditioned_on_answering']:.3f}, halluc_rate={m['hallucination_rate_among_answers']:.3f}, avg_score={m['avg_expected_score']:.3f}\n"
            )
        f.write("\n## Behavioral Check\n")
        f.write(json.dumps(behavior, indent=2))
        if out_png:
            f.write("\n\n## Risk–Coverage Curve\n\n")
            f.write(f"![Risk–coverage curve]({os.path.basename(out_png)})\n")

    return {
        "results_csv": results_csv,
        "metrics_json": metrics_json,
        "behavior_json": behavior_json,
        "report_md": report_md,
        "rc_curve_png": out_png or "",
    }


def evaluate_sync(
    data_csv: str,
    thresholds: Sequence[float],
    out_dir: str,
    model: str,
    temperature: float,
    thinking_budget: int,
    seed: int,
    judge: str = "exact",
    show_progress: bool = False,
    rpm_limit: int | None = None,
    max_retries: int = 6,
) -> dict[str, Any]:
    rows = load_data_csv(data_csv)
    runner = GeminiRunner(
        model=model,
        temperature=temperature,
        thinking_budget=thinking_budget,
        seed=seed,
        rpm_limit=rpm_limit,
        max_retries=max_retries,
    )
    llm_judge = LLMJudge() if judge == "llm" else None

    total = len(rows) * len(thresholds)
    pbar = tqdm(total=total, disable=not show_progress, desc="Evaluating (sync)")

    records: list[Record] = []
    for row in rows:
        qid = row.get("id") or ""
        question = row.get("question") or ""
        gold = row.get("gold") or ""
        unknown_ok = str(row.get("unknown_ok") or "0").strip() in {"1", "true", "True"}
        for t in thresholds:
            prompt = build_conf_prompt(question, float(t))
            pred = runner.generate(prompt)
            abstained = is_idk(pred)
            correct = (
                llm_judge.judge(question, gold, pred, unknown_ok)
                if judge == "llm"
                else judge_validity_exact(pred, gold, unknown_ok)
            )
            score = score_item(answered=not abstained, correct=correct, t=float(t))
            records.append(
                Record(
                    id=qid,
                    t=float(t),
                    question=question,
                    gold=gold,
                    unknown_ok=unknown_ok,
                    pred=pred,
                    abstained=abstained,
                    correct=correct,
                    score=score,
                )
            )
            pbar.update(1)
    pbar.close()
    return _write_artifacts(records, out_dir)


async def evaluate_async(
    data_csv: str,
    thresholds: Sequence[float],
    out_dir: str,
    model: str,
    temperature: float,
    thinking_budget: int,
    seed: int,
    judge: str = "exact",
    concurrency: int = 8,
    show_progress: bool = False,
    rpm_limit: int | None = None,
    max_retries: int = 6,
) -> dict[str, Any]:
    rows = load_data_csv(data_csv)
    runner = AsyncGeminiRunner(
        model=model,
        temperature=temperature,
        thinking_budget=thinking_budget,
        seed=seed,
        rpm_limit=rpm_limit,
        max_retries=max_retries,
    )
    llm_judge = AsyncLLMJudge() if judge == "llm" else None

    import asyncio

    sem = asyncio.Semaphore(concurrency)
    total = len(rows) * len(thresholds)
    pbar = tqdm(total=total, disable=not show_progress, desc="Evaluating (async)")
    records: list[Record] = []

    async def one(qid, question, gold, unknown_ok, t):
        prompt = build_conf_prompt(question, float(t))
        async with sem:
            pred = await runner.generate(prompt)
        abstained = is_idk(pred)
        if judge == "llm":
            async with sem:
                correct = await llm_judge.judge(question, gold, pred, unknown_ok)
        else:
            correct = judge_validity_exact(pred, gold, unknown_ok)
        score = score_item(answered=not abstained, correct=correct, t=float(t))
        return Record(
            id=qid,
            t=float(t),
            question=question,
            gold=gold,
            unknown_ok=unknown_ok,
            pred=pred,
            abstained=abstained,
            correct=correct,
            score=score,
        )

    tasks = []
    for row in rows:
        qid = row.get("id") or ""
        question = row.get("question") or ""
        gold = row.get("gold") or ""
        unknown_ok = str(row.get("unknown_ok") or "0").strip() in {"1", "true", "True"}
        for t in thresholds:
            tasks.append(one(qid, question, gold, unknown_ok, float(t)))

    for coro in asyncio.as_completed(tasks):
        records.append(await coro)
        pbar.update(1)
    pbar.close()
    return _write_artifacts(records, out_dir)


def evaluate(
    data_csv: str,
    thresholds: Sequence[float],
    out_dir: str,
    model: str = "gemini-2.5-flash",
    temperature: float = 0.0,
    thinking_budget: int = 0,
    seed: int = 1234,
    judge: str = "exact",
    use_async: bool = False,
    concurrency: int = 8,
    show_progress: bool = False,
    rpm_limit: int | None = None,
    max_retries: int = 6,
) -> dict[str, Any]:
    if use_async:
        return asyncio.run(
            evaluate_async(
                data_csv,
                thresholds,
                out_dir,
                model,
                temperature,
                thinking_budget,
                seed,
                judge,
                concurrency,
                show_progress,
                rpm_limit,
                max_retries,
            )
        )
    return evaluate_sync(
        data_csv,
        thresholds,
        out_dir,
        model,
        temperature,
        thinking_budget,
        seed,
        judge,
        show_progress,
        rpm_limit,
        max_retries,
    )
