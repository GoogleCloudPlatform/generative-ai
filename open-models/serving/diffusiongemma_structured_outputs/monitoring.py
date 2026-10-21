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

"""Cloud Monitoring hardware utilization and Experiments tracking helpers."""

from datetime import datetime, timedelta, timezone
import statistics
from typing import Any

from google.cloud import aiplatform
from google.cloud import monitoring_v3

ENDPOINT_UTILIZATION_METRICS: dict[str, tuple[str, ...]] = {
    "gpu_duty_cycle_pct": (
        "prometheus.googleapis.com/vertex_dcgm_fi_dev_gpu_util/gauge",
        "aiplatform.googleapis.com/prediction/online/accelerator/duty_cycle",
    ),
    "gpu_mem_bw_pct": (
        "prometheus.googleapis.com/vertex_dcgm_fi_dev_mem_copy_util/gauge",
    ),
    "gpu_tensor_active_pct": (
        "prometheus.googleapis.com/vertex_dcgm_fi_prof_pipe_tensor_active/gauge",
    ),
    "gpu_power_w": (
        "prometheus.googleapis.com/vertex_dcgm_fi_dev_power_usage/gauge",
    ),
    "gpu_vram_gib": (
        "prometheus.googleapis.com/vertex_dcgm_fi_dev_fb_used/gauge",
        "aiplatform.googleapis.com/prediction/online/"
        "accelerator/memory/bytes_used",
    ),
    "cpu_utilization_pct": (
        "aiplatform.googleapis.com/prediction/online/cpu/utilization",
    ),
    "ram_used_gib": (
        "aiplatform.googleapis.com/prediction/online/memory/bytes_used",
    ),
}

_LAST_MONITORING_CONTEXT: dict[str, Any] = {}


def _normalize_monitoring_point_value(
    key: str, raw_val: float, unit: str
) -> float:
    """Converts raw Cloud Monitoring values into percentages, Watts, or GiB."""
    if key.endswith("_gib"):
        # DCGM fb_used is reported in MiB (~21032), whereas Online Prediction
        # memory metrics are reported in Bytes.
        if raw_val > 1024.0**2:
            return round(raw_val / (1024.0**3), 3)
        return round(raw_val / 1024.0, 3)
    if key.endswith("_pct"):
        # Scale fractional 0..1 metrics to 0..100% when unit is not '%'.
        if unit != "%" and 0.0 < raw_val <= 1.0:
            return round(raw_val * 100.0, 2)
        return round(raw_val, 2)
    if key.endswith("_w"):
        return round(raw_val, 2)
    return round(raw_val, 4)


def _build_monitoring_filter(endpoint_id: str, metric_type: str) -> str:
    """Builds the Cloud Monitoring filter for Prometheus or endpoint metrics."""
    if metric_type.startswith("prometheus.googleapis.com/"):
        return (
            'resource.type = "prometheus_target"'
            f' AND metric.labels.endpoint_id = "{endpoint_id}"'
            f' AND metric.type = "{metric_type}"'
        )
    return (
        'resource.type = "aiplatform.googleapis.com/Endpoint"'
        f' AND resource.labels.endpoint_id = "{endpoint_id}"'
        f' AND metric.type = "{metric_type}"'
    )


def fetch_endpoint_utilization_metrics(
    project: str,
    endpoint_id: str,
    start_time: datetime,
    end_time: datetime,
    client: monitoring_v3.MetricServiceClient | None = None,
) -> tuple[dict[str, float], list[dict[str, Any]]]:
    """Fetches GPU and CPU utilization from Cloud Monitoring for an endpoint."""
    mon_client = client or monitoring_v3.MetricServiceClient()
    # Look back 10 minutes when querying live Cloud Monitoring so steady metrics
    # (like RAM/VRAM) with a 360s ingest_delay have a recent sample available.
    lookback = (
        timedelta(minutes=2) if client is not None else timedelta(minutes=10)
    )
    window_start = start_time - timedelta(minutes=2)
    window_end = end_time + timedelta(minutes=2)
    interval = monitoring_v3.TimeInterval(
        start_time=start_time - lookback,
        end_time=window_end,
    )
    by_timestamp: dict[str, dict[str, Any]] = {}
    recent_fallbacks: dict[str, float] = {}
    metric_values: dict[str, list[float]] = {
        k: [] for k in ENDPOINT_UTILIZATION_METRICS
    }

    for key, metric_types in ENDPOINT_UTILIZATION_METRICS.items():
        if isinstance(metric_types, str):
            metric_types = (metric_types,)
        for metric_type in metric_types:
            flt = _build_monitoring_filter(endpoint_id, metric_type)
            try:
                series_iter = mon_client.list_time_series(
                    request={
                        "name": f"projects/{project}",
                        "filter": flt,
                        "interval": interval,
                        "view": (
                            monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL
                        ),
                    }
                )
                for ts in series_iter:
                    unit = getattr(ts, "unit", "") or ""
                    for pt in ts.points:
                        end_dt = pt.interval.end_time
                        if isinstance(end_dt, datetime):
                            dt_utc = end_dt.astimezone(timezone.utc)
                        else:
                            dt_utc = datetime.fromtimestamp(
                                end_dt.seconds, tz=timezone.utc
                            )
                        # Align :57 Prometheus scrapes and :00 endpoint points
                        # into the same 60-second minute bucket.
                        aligned_dt = (dt_utc + timedelta(seconds=30)).replace(
                            second=0, microsecond=0
                        )
                        ts_iso = aligned_dt.isoformat()
                        val_pb = pt.value
                        # Extract double_value or int64_value from TypedValue.
                        raw_val = float(
                            getattr(val_pb, "double_value", 0.0)
                            or getattr(val_pb, "int64_value", 0)
                        )
                        norm_val = _normalize_monitoring_point_value(
                            key, raw_val, unit
                        )
                        if key not in recent_fallbacks:
                            recent_fallbacks[key] = norm_val
                        if window_start <= aligned_dt <= window_end:
                            metric_values[key].append(norm_val)
                            bucket = by_timestamp.setdefault(
                                ts_iso, {"timestamp_utc": ts_iso}
                            )
                            bucket[key] = norm_val
            except Exception:
                # Skip metric types not exported by the underlying SKU.
                continue

    summary: dict[str, float] = {}
    for key, vals in metric_values.items():
        if not vals:
            continue
        active_vals = (
            [v for v in vals if v > 0]
            if key
            in (
                "gpu_duty_cycle_pct",
                "gpu_mem_bw_pct",
                "gpu_tensor_active_pct",
            )
            and any(v > 0 for v in vals)
            else vals
        )
        summary[f"{key}_mean"] = round(statistics.mean(active_vals), 2)
        summary[f"{key}_max"] = round(max(vals), 2)

    rows = [by_timestamp[k] for k in sorted(by_timestamp.keys())]
    _LAST_MONITORING_CONTEXT.clear()
    _LAST_MONITORING_CONTEXT.update(
        {
            "project": project,
            "endpoint_id": endpoint_id,
            "client": client,
            "start_time": start_time,
            "end_time": end_time,
            "recent_fallbacks": recent_fallbacks,
        }
    )
    return summary, rows


def attach_utilization_to_sweep(
    sweep_rows: list[dict[str, Any]],
    utilization_rows: list[dict[str, Any]],
) -> None:
    """Aligns 60s Cloud Monitoring hardware metrics with concurrency stages."""
    valid_starts = [
        datetime.fromisoformat(r["start_utc"])
        for r in sweep_rows
        if r.get("start_utc")
    ]
    valid_ends = [
        datetime.fromisoformat(r["end_utc"])
        for r in sweep_rows
        if r.get("end_utc")
    ]
    # If the caller's start_time/end_time window did not cover sweep_rows,
    # automatically re-fetch the exact sweep_rows time range.
    if (
        valid_starts
        and valid_ends
        and _LAST_MONITORING_CONTEXT.get("client") is None
        and _LAST_MONITORING_CONTEXT.get("project")
        and _LAST_MONITORING_CONTEXT.get("endpoint_id")
    ):
        min_start = min(valid_starts)
        max_end = max(valid_ends)
        ctx_start = _LAST_MONITORING_CONTEXT.get("start_time")
        ctx_end = _LAST_MONITORING_CONTEXT.get("end_time")
        if (
            ctx_start is not None
            and ctx_end is not None
            and (
                ctx_start > min_start + timedelta(seconds=5)
                or ctx_end < max_end - timedelta(seconds=5)
            )
        ):
            _, fresh_rows = fetch_endpoint_utilization_metrics(
                project=_LAST_MONITORING_CONTEXT["project"],
                endpoint_id=_LAST_MONITORING_CONTEXT["endpoint_id"],
                start_time=min_start,
                end_time=max_end,
            )
            utilization_rows.clear()
            utilization_rows.extend(fresh_rows)

    recent_fallbacks = _LAST_MONITORING_CONTEXT.get("recent_fallbacks", {})

    for s_row in sweep_rows:
        start_str = s_row.get("start_utc")
        end_str = s_row.get("end_utc")
        if not start_str or not end_str:
            continue
        start_dt = datetime.fromisoformat(start_str)
        end_dt = datetime.fromisoformat(end_str)
        # Prefer 60s buckets whose [T-60s, T] window overlaps >=30s of the stage.
        interior = [
            u
            for u in utilization_rows
            if start_dt + timedelta(seconds=30)
            <= datetime.fromisoformat(u["timestamp_utc"])
            <= end_dt + timedelta(seconds=30)
        ]
        wide = [
            u
            for u in utilization_rows
            if start_dt - timedelta(seconds=30)
            <= datetime.fromisoformat(u["timestamp_utc"])
            <= end_dt + timedelta(seconds=60)
        ]
        for key in (
            "gpu_duty_cycle_pct",
            "gpu_mem_bw_pct",
            "gpu_tensor_active_pct",
            "gpu_power_w",
            "cpu_utilization_pct",
            "gpu_vram_gib",
            "ram_used_gib",
        ):
            vals = [float(u[key]) for u in interior if key in u]
            if not vals:
                vals = [float(u[key]) for u in wide if key in u]
            if (
                key
                in (
                    "gpu_duty_cycle_pct",
                    "gpu_mem_bw_pct",
                    "gpu_tensor_active_pct",
                )
                and any(v > 0 for v in vals)
            ):
                vals = [v for v in vals if v > 0]
            if vals:
                s_row[key] = round(statistics.mean(vals), 2)
            elif (
                key in ("gpu_vram_gib", "ram_used_gib")
                and key in recent_fallbacks
            ):
                s_row[key] = round(float(recent_fallbacks[key]), 2)
            else:
                s_row[key] = None


def log_benchmark_run_to_experiments(
    project: str,
    region: str,
    experiment_name: str,
    run_name: str,
    params: dict[str, str | int | float],
    metrics: dict[str, float],
) -> None:
    """Logs parameters and metrics to Google Cloud Experiments."""
    aiplatform.init(
        project=project,
        location=region,
        experiment=experiment_name,
    )
    aiplatform.start_run(run=run_name)
    try:
        aiplatform.log_params(params)
        aiplatform.log_metrics(metrics)
    finally:
        aiplatform.end_run()
