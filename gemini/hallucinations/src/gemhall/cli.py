import argparse, json
from .eval import evaluate

def main():
    p = argparse.ArgumentParser(prog="gemhall", description="Gemini confidence-targeted hallucination evaluator")
    p.add_argument("--data", required=True, help="Path to CSV with id,question,gold,unknown_ok")
    p.add_argument("--thresholds", nargs="+", type=float, required=True, help="Confidence thresholds: e.g., 0.5 0.75 0.9")
    p.add_argument("--out", default="outputs", help="Output directory")
    p.add_argument("--model", default="gemini-2.5-flash", help="Gemini model id")
    p.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    p.add_argument("--thinking-budget", type=int, default=0, dest="thinking_budget", help="Thinking budget (0 disables)")
    p.add_argument("--seed", type=int, default=1234, help="Sampling seed")
    p.add_argument("--judge", choices=["exact", "llm"], default="exact", help="Validity judge to use")
    p.add_argument("--async", action="store_true", dest="use_async", help="Use async client for parallelism")
    p.add_argument("--concurrency", type=int, default=8, help="Max concurrent requests in async mode")
    args = p.parse_args()

    res = evaluate(
        data_csv=args.data,
        thresholds=args.thresholds,
        out_dir=args.out,
        model=args.model,
        temperature=args.temperature,
        thinking_budget=args.thinking_budget,
        seed=args.seed,
        judge=args.judge,
        use_async=args.use_async,
        concurrency=args.concurrency,
    )
    print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()
