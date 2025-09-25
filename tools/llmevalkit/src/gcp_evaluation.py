# Copyright 2025 Google LLC
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

"""Provides tools for evaluating and visualizing model performance against human ratings.

This module contains functions to process evaluation data, which includes both
human-provided scores and model-generated scores. It prepares the data into a
pandas DataFrame, extracts key metrics like the confusion matrix, and generates
a series of Plotly visualizations to compare the two sets of scores.

The primary functions are:
- prepare_dataframe: Cleans and formats the raw evaluation data.
- extract_completeness_metrics: Pulls confusion matrix data from metrics logs.
- plot_distribution_comparison: Compares the distribution of human vs. model scores.
- plot_confusion_matrix: Creates a heatmap to show agreement and disagreement.
- plot_jitter_scatter: Visualizes the alignment of individual data points.
- run_visual_analysis: An orchestrator function that runs the full analysis and
  returns a summary report along with the generated figures.
"""

import ast
import logging
import os
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv
from plotly.subplots import make_subplots

load_dotenv("src/.env")


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def format_user_content(user_content: str, tokenizer: Any, **kwargs: Any) -> str | None:
    """Applies tokenizer.apply_chat_template to user content string.
    Assumes user_content is the text for the 'user' role.
    """
    message = [
        {"role": "user", "content": user_content},
    ]
    kwargs.setdefault("tokenize", False)
    kwargs.setdefault("add_generation_prompt", True)

    try:
        return tokenizer.apply_chat_template(message, **kwargs)
    except Exception as e:
        print(
            f"Error applying chat template to content: '{user_content[:50]}...'. Error: {e}"
        )
        return None


def prepare_dataframe(
    raw_data: Any,
    human_col_name: str,
    score_col_name: str,
) -> pd.DataFrame:
    """Prepares the DataFrame from raw data, renames columns, and converts types."""
    try:
        if isinstance(raw_data, pd.DataFrame):
            df = raw_data.copy()
            if len(df.columns) >= 2:
                # If it's a DataFrame, check if desired columns exist, else use first two
                if human_col_name not in df.columns or score_col_name not in df.columns:
                    original_cols = df.columns
                    df = df[
                        [original_cols[0], original_cols[1]]
                    ].copy()  # Use first two
                    df.columns = [human_col_name, score_col_name]
                else:
                    # Ensure we only keep the needed columns if more exist
                    pass
                if human_col_name not in df.columns or score_col_name not in df.columns:
                    original_cols = df.columns
                    df = df[[original_cols[0], original_cols[1]]].copy()
                    df.columns = [human_col_name, score_col_name]
                else:
                    df = df[[human_col_name, score_col_name]].copy()
            else:
                print(
                    f"Warning: Input DataFrame has < 2 columns. Expected at least '{human_col_name}' and '{score_col_name}'."
                )
                return pd.DataFrame(columns=[human_col_name, score_col_name])
        else:
            df = pd.DataFrame(raw_data)
            if df.empty:
                print("Warning: Created empty DataFrame from raw_data.")
                return pd.DataFrame(columns=[human_col_name, score_col_name])

            if len(df.columns) >= 2:
                df = df.iloc[:, :2]
                df.columns = [human_col_name, score_col_name]
            else:
                print(
                    f"Warning: DataFrame from raw_data has < 2 columns. Cannot set '{human_col_name}' and '{score_col_name}'."
                )
                return pd.DataFrame(columns=[human_col_name, score_col_name])

        df[human_col_name] = pd.to_numeric(df[human_col_name], errors="coerce")
        df[score_col_name] = pd.to_numeric(df[score_col_name], errors="coerce")
        df.dropna(subset=[human_col_name, score_col_name], inplace=True)
        df[human_col_name] = df[human_col_name].astype(float)
        df[score_col_name] = df[score_col_name].astype(float)
        return df

    except Exception as e:
        print(f"Error preparing DataFrame: {e}")
        return pd.DataFrame(columns=[human_col_name, score_col_name])


def extract_completeness_metrics(
    metrics_data: list[dict[str, Any]] | None,
) -> tuple[list[list[Any]] | None, list[str] | None, list[float] | None]:
    """Extracts confusion matrix info from metrics data (expected at index 0)."""
    if not metrics_data or not isinstance(metrics_data, list) or len(metrics_data) == 0:
        print("Warning: Metrics data is empty or not a list.")
        return None, None, None

    try:
        completeness_metrics = metrics_data[0]
        if (
            "confusion_matrix" not in completeness_metrics
            or "confusion_matrix_labels" not in completeness_metrics
        ):
            print(
                "Warning: 'confusion_matrix' or 'confusion_matrix_labels' not in first metrics item."
            )
            return None, None, None

        cm = completeness_metrics["confusion_matrix"]
        cm_labels = completeness_metrics["confusion_matrix_labels"]
        cm_labels_numeric = [float(cl) for cl in cm_labels]
        return cm, cm_labels, cm_labels_numeric
    except (KeyError, IndexError, ValueError, TypeError) as e:
        print(f"Warning: Could not extract confusion matrix info from metrics: {e}")
        return None, None, None


def plot_distribution_comparison(
    df: pd.DataFrame,
    human_col: str,
    score_col: str,
) -> go.Figure:
    """Generates bar charts comparing distributions of human ratings and model scores."""
    human_counts = df[human_col].value_counts().sort_index()
    score_counts = df[score_col].value_counts().sort_index()

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("Human Rating Distribution", "Model Score Distribution"),
    )

    fig.add_trace(
        go.Bar(
            x=human_counts.index,
            y=human_counts.values,
            name="Human Rating",
            marker_color="indianred",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=score_counts.index,
            y=score_counts.values,
            name="Model Score",
            marker_color="lightsalmon",
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        title_text="Distribution of Human Ratings vs. Model Scores",
        bargap=0.2,
        xaxis1_title="Rating Value",
        yaxis1_title="Count",
        xaxis2_title="Score Value",
        yaxis2_title="Count",
        xaxis1_type="category",
        xaxis2_type="category",
        xaxis1={
            "categoryorder": "array",
            "categoryarray": sorted(human_counts.index.unique()),
        },
        xaxis2={
            "categoryorder": "array",
            "categoryarray": sorted(score_counts.index.unique()),
        },
        height=400,
    )
    return fig


def plot_confusion_matrix(
    cm: list[list[Any]] | None, cm_labels: list[str] | None
) -> go.Figure | None:
    """Generates a heatmap for the confusion matrix."""
    if cm is None or cm_labels is None:
        print("Skipping confusion matrix plot: missing data.")
        return None

    fig = go.Figure(
        data=go.Heatmap(
            z=cm,
            x=cm_labels,
            y=cm_labels,
            hoverongaps=False,
            colorscale="Blues",
            text=cm,
            texttemplate="%{text}",
            zmin=0,
        )
    )

    fig.update_layout(
        title="Confusion Matrix: Human Rating vs. Model Score (Completeness)",
        xaxis_title="Predicted (Model Score)",
        yaxis_title="True (Human Rating)",
        yaxis={
            "type": "category",
            "categoryorder": "array",
            "categoryarray": cm_labels,
        },
        xaxis={
            "type": "category",
            "categoryorder": "array",
            "categoryarray": cm_labels,
        },
        height=600,
        width=600,
    )
    return fig


def plot_jitter_scatter(
    df: pd.DataFrame,
    cm_labels: list[str] | None,
    cm_labels_numeric: list[float] | None,
    human_col: str,
    score_col: str,
) -> go.Figure:
    """Generates a jitter scatter plot comparing individual scores and ratings."""
    df_jitter = df[[human_col, score_col]].copy()

    if cm_labels is None or cm_labels_numeric is None:
        print(
            "Using data range for jitter plot axes due to missing confusion matrix labels."
        )
        min_val: float = (
            min(df_jitter[human_col].min(), df_jitter[score_col].min()) - 0.5
        )
        max_val: float = (
            max(df_jitter[human_col].max(), df_jitter[score_col].max()) + 0.5
        )
        plot_range = [min_val, max_val]
        tick_vals = sorted(
            df_jitter[human_col].unique()
        )  # Use unique human ratings for ticks if available
        tick_text = [str(int(v)) if v == int(v) else str(v) for v in tick_vals]
    else:
        plot_range = [min(cm_labels_numeric) - 0.5, max(cm_labels_numeric) + 0.5]
        tick_vals = cm_labels_numeric
        tick_text = cm_labels

    df_jitter[f"{human_col}_jitter"] = df_jitter[human_col] + np.random.uniform(
        -ast.literal_eval(os.getenv("JITTER_AMOUNT")),
        ast.literal_eval(os.getenv("JITTER_AMOUNT")),
        size=len(df_jitter),
    )
    df_jitter[f"{score_col}_jitter"] = df_jitter[score_col] + np.random.uniform(
        -ast.literal_eval(os.getenv("JITTER_AMOUNT")),
        ast.literal_eval(os.getenv("JITTER_AMOUNT")),
        size=len(df_jitter),
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_jitter[f"{score_col}_jitter"],
            y=df_jitter[f"{human_col}_jitter"],
            mode="markers",
            marker={
                "color": "rgba(0, 100, 200, 0.7)",
                "size": 10,
                "line": {"width": 1, "color": "DarkSlateGrey"},
            },
            text=[
                f"HR: {hr:.1f}, Score: {s:.1f}"
                for hr, s in zip(
                    df_jitter[human_col], df_jitter[score_col], strict=False
                )
            ],
            hoverinfo="text",
            name="Ratings",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=plot_range,
            y=plot_range,
            mode="lines",
            name="Ideal Alignment (Score = Human Rating)",
            line={"color": "red", "dash": "dash"},
        )
    )

    fig.update_layout(
        title="Model Score vs. Human Rating (with Jitter)",
        xaxis_title="Model Score (Jittered)",
        yaxis_title="Human Rating (Jittered)",
        xaxis={"range": plot_range, "tickvals": list(tick_vals), "ticktext": tick_text},
        yaxis={"range": plot_range, "tickvals": list(tick_vals), "ticktext": tick_text},
        width=600,
        height=600,
        showlegend=True,
        hovermode="closest",
    )
    return fig


def run_visual_analysis(
    df_data: Any,
    metrics: list[dict[str, Any]] | None,
    human_col_name: str,
    score_col_name: str,
) -> tuple[str, go.Figure | None, go.Figure | None, go.Figure | None]:
    """Runs the visual analysis comparing model scores and human ratings.
    Returns a markdown string and the three figure objects.
    """
    result_str = ""

    df = prepare_dataframe(
        df_data, human_col_name=human_col_name, score_col_name=score_col_name
    )
    cm, cm_labels, cm_labels_numeric = extract_completeness_metrics(metrics)

    if df.empty:
        result_str = f"Could not create valid DataFrame with columns '{human_col_name}' and '{score_col_name}' from input data. Stopping analysis."
        return result_str, None, None, None

    if human_col_name not in df.columns or score_col_name not in df.columns:
        result_str = f"Expected columns '{human_col_name}' and '{score_col_name}' not found in DataFrame. Stopping analysis."
        return result_str, None, None, None

    result_str += "# Visual Analysis: Model Score vs. Human Rating Alignment \n"

    result_str += "## 1. Distributions Comparison\n"
    fig_dist: go.Figure | None = plot_distribution_comparison(
        df, human_col=human_col_name, score_col=score_col_name
    )
    if fig_dist:
        result_str += "*Shows if the model score distribution mirrors human ratings.*\n"
    else:
        result_str += "*Could not generate distribution comparison plot.*\n"

    result_str += "## 2. Confusion Matrix (Human vs. Model)\n"
    fig_cm: go.Figure | None = plot_confusion_matrix(cm, cm_labels)
    if fig_cm:
        result_str += "*Visualizes agreement and disagreement between discrete human ratings and model scores. Ideal alignment is along the diagonal.*\n"

    else:
        result_str += "*Confusion Matrix could not be generated (check metrics data or ensure it's at index 0).**\n"

    result_str += "## 3. Score vs. Rating Alignment (Jitter Plot)\n"
    fig_scatter: go.Figure | None = plot_jitter_scatter(
        df,
        cm_labels,
        cm_labels_numeric,
        human_col=human_col_name,
        score_col=score_col_name,
    )
    if fig_scatter:
        result_str += "*Shows individual item alignment. Points close to the red dashed line indicate good agreement.*\n"
    else:
        result_str += "*Could not generate jitter scatter plot.*"

    return result_str, fig_dist, fig_cm, fig_scatter
