import argparse
import contextlib
import json
import os
from tempfile import NamedTemporaryFile

from gemhall.adapters.mmlu import SUBJECTS_ALL
from gemhall.adapters.mmlu import export_temp_csv as mmlu_export
from gemhall.eval import evaluate


def add_common_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument(
        "--thresholds",
        nargs="+",
        type=float,
        required=True,
        help="Confidence thresholds, e.g., 0.5 0.75 0.9",
    )
    ap.add_argument("--out", default="outputs", help="Output directory")
    ap.add_argument(
        "--model",
        default="gemini-2.5-flash",
        choices=["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-flash-lite"],
        help="Gemini model id",
    )
    ap.add_argument(
        "--temperature", type=float, default=0.0, help="Sampling temperature"
    )
    ap.add_argument(
        "--thinking-budget",
        type=int,
        default=0,
        dest="thinking_budget",
        help="Thinking budget (0 disables) - not supported at the moment",
    )
    ap.add_argument("--seed", type=int, default=1234, help="Sampling seed")
    ap.add_argument(
        "--judge",
        choices=["exact", "llm"],
        default="exact",
        help="Validity judge to use",
    )
    ap.add_argument(
        "--async",
        action="store_true",
        dest="use_async",
        help="Use async client for parallelism",
    )
    ap.add_argument(
        "--concurrency",
        type=int,
        default=8,
        help="Max concurrent requests in async mode",
    )
    ap.add_argument("--progress", action="store_true", help="Show a progress bar")
    ap.add_argument(
        "--rpm-limit",
        type=int,
        default=None,
        help="Optional requests-per-minute cap (client-side)",
    )
    ap.add_argument(
        "--max-retries",
        type=int,
        default=6,
        help="Max retries on 429/RESOURCE_EXHAUSTED",
    )


def main() -> None:
    p = argparse.ArgumentParser(
        prog="gemhall", description="Gemini confidence-targeted hallucination evaluator"
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # CSV mode
    run = sub.add_parser("run", help="Run evaluation from CSV")
    run.add_argument(
        "--data", required=True, help="Path to CSV with id,question,gold,unknown_ok"
    )
    add_common_args(run)

    # MMLU mode (direct from HF)
    mmlu = sub.add_parser(
        "mmlu", help="Run evaluation on MMLU (direct from Hugging Face Datasets)"
    )
    mmlu.add_argument("--split", default="test", help="Dataset split (e.g., test, dev)")
    mmlu.add_argument(
        "--subjects", nargs="+", default=["all"], help="Subjects or 'all'"
    )
    mmlu.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Randomly sample N items after filtering subjects",
    )
    mmlu.add_argument(
        "--idk-frac",
        type=float,
        default=0.0,
        help="Fraction [0..1] of sampled items to convert to IDK-only",
    )
    add_common_args(mmlu)

    args = p.parse_args()

    if args.cmd == "mmlu":
        with NamedTemporaryFile("w+", suffix=".csv", delete=False) as tf:
            tmp_csv = tf.name
        subjects = SUBJECTS_ALL if args.subjects == ["all"] else args.subjects
        csv_path = mmlu_export(
            out_csv=tmp_csv,
            split=args.split,
            subjects=subjects,
            limit=args.limit,
            seed=args.seed,
            idk_frac=args.idk_frac,
        )
        res = evaluate(
            data_csv=csv_path,
            thresholds=args.thresholds,
            out_dir=args.out,
            model=args.model,
            temperature=args.temperature,
            thinking_budget=0,
            seed=args.seed,
            judge=args.judge,
            use_async=args.use_async,
            concurrency=args.concurrency,
            show_progress=args.progress,
            rpm_limit=args.rpm_limit,
            max_retries=args.max_retries,
        )
        print(json.dumps(res, indent=2))
        with contextlib.suppress(Exception):
            os.unlink(csv_path)
        return

    if args.cmd == "run":
        res = evaluate(
            data_csv=args.data,
            thresholds=args.thresholds,
            out_dir=args.out,
            model=args.model,
            temperature=args.temperature,
            thinking_budget=0,
            seed=args.seed,
            judge=args.judge,
            use_async=args.use_async,
            concurrency=args.concurrency,
            show_progress=args.progress,
            rpm_limit=args.rpm_limit,
            max_retries=args.max_retries,
        )
        print(json.dumps(res, indent=2))
        return


if __name__ == "__main__":
    main()
