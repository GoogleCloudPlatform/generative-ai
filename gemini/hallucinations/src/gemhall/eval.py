import csv, json, os, asyncio
from typing import List, Dict, Any, Sequence
from .prompts import build_conf_prompt, is_idk
from .metrics import Record, score_item, aggregate, behavior_checks
from .judge import judge_validity as judge_validity_exact
from .judge_llm import LLMJudge, AsyncLLMJudge
from .runner import GeminiRunner, AsyncGeminiRunner

def load_data_csv(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows

def _write_artifacts(records: List[Record], out_dir: str) -> Dict[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    results_csv = os.path.join(out_dir, "results.csv")
    with open(results_csv, "w", newline='', encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "t", "question", "gold", "unknown_ok", "pred", "abstained", "correct", "score"])
        for r in records:
            w.writerow([r.id, r.t, r.question, r.gold, int(r.unknown_ok), r.pred, int(r.abstained), int(r.correct), r.score])

    metrics = aggregate(records)
    metrics_json = os.path.join(out_dir, "metrics.json")
    with open(metrics_json, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    behavior = behavior_checks(metrics)
    behavior_json = os.path.join(out_dir, "behavior.json")
    with open(behavior_json, "w", encoding="utf-8") as f:
        json.dump(behavior, f, indent=2)

    out_png = ""
    try:
        import matplotlib.pyplot as plt
        ts = sorted(metrics.keys())
        cov = [metrics[t]["coverage"] for t in ts]
        acc = [metrics[t]["accuracy_conditioned_on_answering"] for t in ts]
        plt.figure()
        plt.plot(cov, acc, marker="o")
        plt.xlabel("Coverage (answered fraction)")
        plt.ylabel("Conditional accuracy")
        plt.title("Risk–coverage curve (higher is better)")
        out_png = os.path.join(out_dir, "rc_curve.png")
        plt.savefig(out_png, bbox_inches="tight")
        plt.close()
    except Exception:
        pass

    report_md = os.path.join(out_dir, "report.md")
    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# Hallucination Evaluation Report\n\n")
        f.write("## Summary\n")
        for t in sorted(metrics.keys()):
            m = metrics[t]
            f.write(f"- t={t}: coverage={m['coverage']:.3f}, cond_acc={m['accuracy_conditioned_on_answering']:.3f}, halluc_rate={m['hallucination_rate_among_answers']:.3f}, avg_score={m['avg_expected_score']:.3f}\n")
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
) -> Dict[str, Any]:
    rows = load_data_csv(data_csv)
    runner = GeminiRunner(model=model, temperature=temperature, thinking_budget=thinking_budget, seed=seed)
    llm_judge = LLMJudge() if judge == "llm" else None

    records: List[Record] = []
    for row in rows:
        qid = row.get("id") or ""
        question = row.get("question") or ""
        gold = row.get("gold") or ""
        unknown_ok = str(row.get("unknown_ok") or "0").strip() in {"1", "true", "True"}

        for t in thresholds:
            prompt = build_conf_prompt(question, float(t))
            pred = runner.generate(prompt)
            abstained = is_idk(pred)
            if judge == "llm":
                correct = llm_judge.judge(question, gold, pred, unknown_ok)
            else:
                correct = judge_validity_exact(pred, gold, unknown_ok)
            score = score_item(answered=not abstained, correct=correct, t=float(t))
            records.append(Record(
                id=qid, t=float(t), question=question, gold=gold, unknown_ok=unknown_ok,
                pred=pred, abstained=abstained, correct=correct, score=score
            ))

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
) -> Dict[str, Any]:
    rows = load_data_csv(data_csv)
    runner = AsyncGeminiRunner(model=model, temperature=temperature, thinking_budget=thinking_budget, seed=seed)
    llm_judge = AsyncLLMJudge() if judge == "llm" else None

    import asyncio
    sem = asyncio.Semaphore(concurrency)
    records: List[Record] = []

    async def one_call(qid: str, question: str, gold: str, unknown_ok: bool, t: float):
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
        return Record(id=qid, t=float(t), question=question, gold=gold, unknown_ok=unknown_ok,
                      pred=pred, abstained=abstained, correct=correct, score=score)

    tasks = []
    for row in rows:
        qid = row.get("id") or ""
        question = row.get("question") or ""
        gold = row.get("gold") or ""
        unknown_ok = str(row.get("unknown_ok") or "0").strip() in {"1", "true", "True"}
        for t in thresholds:
            tasks.append(one_call(qid, question, gold, unknown_ok, float(t)))

    for coro in asyncio.as_completed(tasks):
        rec = await coro
        records.append(rec)

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
) -> Dict[str, Any]:
    if use_async:
        return asyncio.run(evaluate_async(
            data_csv=data_csv, thresholds=thresholds, out_dir=out_dir,
            model=model, temperature=temperature, thinking_budget=thinking_budget, seed=seed,
            judge=judge, concurrency=concurrency
        ))
    else:
        return evaluate_sync(
            data_csv=data_csv, thresholds=thresholds, out_dir=out_dir,
            model=model, temperature=temperature, thinking_budget=thinking_budget, seed=seed,
            judge=judge
        )
