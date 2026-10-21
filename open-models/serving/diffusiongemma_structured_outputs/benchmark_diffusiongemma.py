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

"""CLI runner for DiffusionGemma quality, load, and utilization benchmarks."""

import argparse
from datetime import datetime, timezone
import json
import time
from typing import Any

from google.cloud import aiplatform
import pandas as pd

import benchmark_load
import benchmark_quality
import config
import diffusiongemma_client
import monitoring


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--project", default=config.resolve_default_project())
    ap.add_argument("--region", default=config.REGION)
    ap.add_argument("--endpoint", default=config.ENDPOINT_ID)
    ap.add_argument("--tokenizer", default=config.HF_MODEL_ID)
    ap.add_argument("--served-model-name", default=config.SERVED_MODEL_NAME)
    ap.add_argument(
        "--tasks",
        default="banking77,ag_news,boolq,sst5",
        help="Comma-separated quality benchmarks to run",
    )
    ap.add_argument(
        "--num-samples",
        type=int,
        default=50,
        help="Samples per quality dataset (set 0 to run all dataset examples)",
    )
    ap.add_argument(
        "--eval-concurrency",
        type=int,
        default=4,
        help="Worker concurrency during dataset quality evaluation",
    )
    ap.add_argument(
        "--concurrency",
        default="1,2,4,8,16",
        help="Comma-separated concurrency levels for load testing",
    )
    ap.add_argument(
        "--requests-per-level",
        type=int,
        default=32,
        help="Minimum requests per concurrency level during load test",
    )
    ap.add_argument(
        "--fetch-utilization",
        action="store_true",
        help="Query Cloud Monitoring for GPU and CPU utilization after the run",
    )
    ap.add_argument(
        "--metrics-wait-seconds",
        type=int,
        default=65,
        help="Seconds to wait before querying Cloud Monitoring (60s sample lag)",
    )
    ap.add_argument(
        "--experiment",
        default="diffusiongemma-benchmarks",
        help="Google Cloud Experiment name for historical run tracking",
    )
    ap.add_argument(
        "--output",
        default="benchmark_results.json",
        help="Path to write JSON benchmark report",
    )
    args = ap.parse_args()

    aiplatform.init(project=args.project, location=args.region)
    endpoint = diffusiongemma_client.resolve_endpoint(args.endpoint)
    url = benchmark_load.build_dedicated_raw_predict_url(endpoint)

    print(f"Loading tokenizer '{args.tokenizer}'...")
    client = diffusiongemma_client.DiffusionGemmaClient(args.tokenizer)

    tasks = [t.strip() for t in args.tasks.split(",") if t.strip()]
    concurrencies = [
        int(c.strip()) for c in args.concurrency.split(",") if c.strip()
    ]

    run_start_utc = datetime.now(timezone.utc)
    all_metrics: dict[str, float] = {}
    quality_metrics: dict[str, float] = {}
    task_runners = {
        "banking77": benchmark_quality.evaluate_banking77,
        "ag_news": benchmark_quality.evaluate_ag_news,
        "boolq": benchmark_quality.evaluate_boolq,
        "sst5": benchmark_quality.evaluate_sst5,
    }

    for task in tasks:
        if task not in task_runners:
            raise ValueError(f"Unknown benchmark task: {task!r}")
        sample_label = "all" if args.num_samples <= 0 else str(args.num_samples)
        print(
            f"\n--- Running Quality Benchmark: {task}"
            f" (n={sample_label}, concurrency={args.eval_concurrency}) ---"
        )
        token = benchmark_load.fetch_gcloud_bearer_token()
        t_metrics = task_runners[task](
            client=client,
            url=url,
            token=token,
            num_samples=args.num_samples,
            concurrency=args.eval_concurrency,
            model=args.served_model_name,
        )
        quality_metrics.update(t_metrics)
        all_metrics.update(t_metrics)

    if quality_metrics:
        quality_df = pd.DataFrame(
            benchmark_quality.build_quality_summary_rows(quality_metrics)
        )
        print("\n--- Quality Benchmark Summary ---")
        print(quality_df.to_string(index=False))

    load_rows: list[dict[str, Any]] = []
    if concurrencies:
        print(
            f"\n--- Running Load Test Concurrency Sweep: {concurrencies}"
            f" (requests_per_level={args.requests_per_level}) ---"
        )
        token = benchmark_load.fetch_gcloud_bearer_token()
        load_metrics, load_rows = benchmark_load.run_concurrency_sweep(
            client=client,
            url=url,
            token=token,
            concurrencies=concurrencies,
            requests_per_level=args.requests_per_level,
            model=args.served_model_name,
        )
        all_metrics.update(load_metrics)

    run_end_utc = datetime.now(timezone.utc)
    utilization_rows: list[dict[str, Any]] = []
    if args.fetch_utilization and args.project:
        if args.metrics_wait_seconds > 0:
            print(
                f"\nWaiting {args.metrics_wait_seconds}s for Cloud Monitoring"
                " 60s hardware metrics ingestion..."
            )
            time.sleep(args.metrics_wait_seconds)
        util_summary, utilization_rows = (
            monitoring.fetch_endpoint_utilization_metrics(
                project=args.project,
                endpoint_id=endpoint.name,
                start_time=run_start_utc,
                end_time=run_end_utc,
            )
        )
        all_metrics.update(util_summary)
        monitoring.attach_utilization_to_sweep(load_rows, utilization_rows)
        print("\n--- Endpoint Hardware Utilization Summary ---")
        for k, v in util_summary.items():
            print(f"  {k}: {v}")

    if load_rows:
        print("\n--- Concurrency Sweep Summary ---")
        print(pd.DataFrame(load_rows).to_string(index=False))

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_name = f"run-{ts}"
    params: dict[str, str | int | float] = {
        "hf_model_id": args.tokenizer,
        "served_model_name": args.served_model_name,
        "num_samples": args.num_samples,
        "concurrencies": args.concurrency,
        "requests_per_level": args.requests_per_level,
    }

    report = {
        "run_name": run_name,
        "experiment": args.experiment,
        "parameters": params,
        "metrics": all_metrics,
        "concurrency_sweep": load_rows,
        "hardware_utilization_timeseries": utilization_rows,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved benchmark report to {args.output}")

    if args.experiment and args.project:
        print(
            f"Logging run '{run_name}' to Google Cloud Experiment"
            f" '{args.experiment}'..."
        )
        monitoring.log_benchmark_run_to_experiments(
            project=args.project,
            region=args.region,
            experiment_name=args.experiment,
            run_name=run_name,
            params=params,
            metrics=all_metrics,
        )
        df = aiplatform.get_experiment_df(args.experiment)
        print(f"\nExperiment History ({len(df)} total runs):")
        print(df.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
