import re

import matplotlib.pyplot as plt
import pandas as pd
from rich.console import Console
from rich.table import Table
import seaborn as sns


def render_model_comparison(all_results, console=None):
    """
    Compare models and their impact on response quality.

    Args:
        all_results: List of evaluation result dictionaries
        console: Optional Rich console instance. If None, a new one will be created.
    """
    # Use provided console or create a new one if not provided
    if console is None:
        console = Console()

    # Create a function to extract the base model name (ignoring parentheses)
    def get_base_model_name(full_name):
        # Remove anything in parentheses and trim whitespace
        base_name = re.sub(r"\s*\([^)]*\)", "", full_name).strip()
        return base_name

    # Prepare response data
    response_data = []

    for result in all_results:
        config = result["config"]
        detailed_metrics = result["detailed_metrics"]

        # Get base model name
        base_model = get_base_model_name(config["name"])

        # Find response quality column
        response_col = next(
            (
                col
                for col in detailed_metrics.columns
                if "response" in col.lower() and "score" in col.lower()
            ),
            None,
        )

        if response_col and not detailed_metrics.empty:
            # Add model info to each row
            model_data = detailed_metrics.copy()
            model_data["Base Model"] = base_model
            model_data["Temperature"] = config["temperature"]

            # Select only needed columns
            model_data = model_data[["Base Model", "Temperature", response_col]].rename(
                columns={response_col: "Response Quality"}
            )
            response_data.append(model_data)

    # Combine all data
    if response_data:
        combined_data = pd.concat(response_data, ignore_index=True)

        # Create a simple, clean figure
        plt.figure(figsize=(10, 6))

        # Create a basic boxplot
        ax = sns.boxplot(
            x="Base Model",
            y="Response Quality",
            data=combined_data,
            palette="pastel",
            width=0.6,
        )

        # Simple, clean styling
        plt.title("Response Quality by Model Type", fontsize=16)
        plt.xlabel("Model", fontsize=14)
        plt.ylabel("Response Quality Score", fontsize=14)

        # Add the overall average line
        overall_mean = combined_data["Response Quality"].mean()
        plt.axhline(y=overall_mean, color="red", linestyle="--", linewidth=1.5)
        plt.text(
            len(combined_data["Base Model"].unique()) - 0.5,
            overall_mean + 0.05,
            f"Overall Mean: {overall_mean:.2f}",
            ha="right",
            color="red",
            fontweight="bold",
        )

        # Add mean values as annotations - now below the boxes
        for i, model in enumerate(combined_data["Base Model"].unique()):
            model_data = combined_data[combined_data["Base Model"] == model]
            mean_score = model_data["Response Quality"].mean()

            # Calculate the bottom of the box
            q1 = model_data["Response Quality"].quantile(0.25)
            q3 = model_data["Response Quality"].quantile(0.75)
            iqr = q3 - q1
            bottom = max(model_data["Response Quality"].min(), q1 - 1.5 * iqr)

            # Place text below the box
            plt.text(
                i,
                bottom - 0.2,
                f"Mean: {mean_score:.2f}",
                ha="center",
                va="top",
                fontweight="bold",
                fontsize=11,
            )

        # Save and show
        plt.tight_layout()
        plt.savefig("model_response_quality.png", dpi=300)
        plt.show()

        # Create a comprehensive summary table with all metrics by model
        console.rule("[bold magenta]Model Performance Summary")

        # Get all metrics from all results
        all_metrics = {}
        for result in all_results:
            config = result["config"]
            metrics = result["summary_metrics"]
            base_model = get_base_model_name(config["name"])

            if base_model not in all_metrics:
                all_metrics[base_model] = {}

            # Add all mean metrics
            for metric_key, value in metrics.items():
                if "/Mean" in metric_key:
                    # Clean up metric name for display
                    clean_metric = (
                        metric_key.replace("/Mean", "")
                        .replace("_score", "")
                        .replace("_", " ")
                        .title()
                    )

                    if clean_metric not in all_metrics[base_model]:
                        all_metrics[base_model][clean_metric] = []

                    all_metrics[base_model][clean_metric].append(value)

        # Create a table with all metrics
        summary_table = Table(title="All Metrics by Model Type")

        # Add model column
        summary_table.add_column("Model", style="cyan")

        # Find all unique metrics
        all_metric_names = set()
        for model_metrics in all_metrics.values():
            all_metric_names.update(model_metrics.keys())

        # Add columns for each metric
        for metric in sorted(all_metric_names):
            summary_table.add_column(metric, style="green")

        # Add rows for each model
        for model, metrics in all_metrics.items():
            row_values = [model]

            for metric in sorted(all_metric_names):
                if metric in metrics:
                    # Calculate average if there are multiple values (from different temperatures)
                    avg_value = sum(metrics[metric]) / len(metrics[metric])
                    row_values.append(f"{avg_value:.2f}")
                else:
                    row_values.append("N/A")

            summary_table.add_row(*row_values)

        console.print(summary_table)
    else:
        console.print(
            "[yellow]Warning: No response quality data available for visualization[/yellow]"
        )


def render_difficulty_analysis(all_results, console=None):
    """
    Analyze performance by query difficulty.

    Args:
        all_results: List of evaluation result dictionaries
        console: Optional Rich console instance. If None, a new one will be created.
    """
    # Use provided console or create a new one if not provided
    if console is None:
        console = Console()

    # Create a function to extract the base model name (ignoring parentheses)
    def get_base_model_name(full_name):
        # Remove anything in parentheses and trim whitespace
        base_name = re.sub(r"\s*\([^)]*\)", "", full_name).strip()
        return base_name

    # Create a dataframe with all detailed metrics and model info
    all_detailed_metrics = []

    for result in all_results:
        config = result["config"]
        detailed_metrics = result["detailed_metrics"].copy()

        # Skip if detailed_metrics is empty
        if detailed_metrics.empty:
            continue

        # Get base model name and temperature
        base_model = get_base_model_name(config["name"])
        temperature = config["temperature"]

        # Add model info to detailed metrics
        detailed_metrics["Base Model"] = base_model
        detailed_metrics["Temperature"] = temperature
        detailed_metrics["Model Config"] = f"{base_model} (T={temperature})"

        all_detailed_metrics.append(detailed_metrics)

    # Only proceed if we have data
    if all_detailed_metrics:
        all_metrics_df = pd.concat(all_detailed_metrics, ignore_index=True)

        # Check if difficulty column exists
        difficulty_col = next(
            (col for col in all_metrics_df.columns if col.lower() == "difficulty"), None
        )

        # Find response correctness column
        response_col = next(
            (
                col
                for col in all_metrics_df.columns
                if "response" in col.lower() and "score" in col.lower()
            ),
            None,
        )

        if difficulty_col and response_col:
            # Convert difficulty to string to ensure proper categorical plotting
            all_metrics_df[difficulty_col] = all_metrics_df[difficulty_col].astype(str)

            # Create a simple, clean figure
            plt.figure(figsize=(12, 7))

            # Plot performance by difficulty
            ax = sns.boxplot(
                x=difficulty_col,
                y=response_col,
                data=all_metrics_df,
                palette="pastel",
                width=0.6,
            )

            # Simple, clean styling
            plt.title("Response Quality by Query Difficulty", fontsize=16)
            plt.xlabel("Query Difficulty", fontsize=14)
            plt.ylabel("Response Quality Score", fontsize=14)

            # Add the overall average line
            overall_mean = all_metrics_df[response_col].mean()
            plt.axhline(y=overall_mean, color="red", linestyle="--", linewidth=1.5)
            plt.text(
                len(all_metrics_df[difficulty_col].unique()) - 0.5,
                overall_mean + 0.05,
                f"Overall Mean: {overall_mean:.2f}",
                ha="right",
                color="red",
                fontweight="bold",
            )

            # Add mean values as annotations below the boxes
            for i, difficulty in enumerate(
                sorted(all_metrics_df[difficulty_col].unique())
            ):
                difficulty_data = all_metrics_df[
                    all_metrics_df[difficulty_col] == difficulty
                ]
                mean_score = difficulty_data[response_col].mean()

                # Calculate the bottom of the box
                q1 = difficulty_data[response_col].quantile(0.25)
                q3 = difficulty_data[response_col].quantile(0.75)
                iqr = q3 - q1
                bottom = max(difficulty_data[response_col].min(), q1 - 1.5 * iqr)

                # Place text below the box
                plt.text(
                    i,
                    bottom - 0.2,
                    f"Mean: {mean_score:.2f}",
                    ha="center",
                    va="top",
                    fontweight="bold",
                    fontsize=11,
                )

            # Save and show
            plt.tight_layout()
            plt.savefig("response_quality_by_difficulty.png", dpi=300)
            plt.show()

            # Create a detailed table showing best model for each difficulty level
            console.rule("[bold magenta]Best Model Configuration by Difficulty")

            detailed_table = Table(
                title="Best Model Configuration for Each Difficulty Level"
            )
            detailed_table.add_column("Difficulty", style="cyan")
            detailed_table.add_column("Best Model", style="green")
            detailed_table.add_column("Temperature", style="yellow")
            detailed_table.add_column("Score", style="magenta")
            detailed_table.add_column("Improvement Over Avg", style="blue")

            # Add rows for each difficulty level
            for difficulty in sorted(all_metrics_df[difficulty_col].unique()):
                difficulty_data = all_metrics_df[
                    all_metrics_df[difficulty_col] == difficulty
                ]
                avg_score = difficulty_data[response_col].mean()

                # Group by model and temperature to find the best configuration
                grouped = (
                    difficulty_data.groupby(["Base Model", "Temperature"])[response_col]
                    .mean()
                    .reset_index()
                )
                best_idx = grouped[response_col].idxmax()
                best_model = grouped.loc[best_idx, "Base Model"]
                best_temp = grouped.loc[best_idx, "Temperature"]
                best_score = grouped.loc[best_idx, response_col]

                # Calculate improvement over average
                improvement = best_score - avg_score
                improvement_pct = (
                    (improvement / avg_score) * 100 if avg_score > 0 else 0
                )

                detailed_table.add_row(
                    difficulty,
                    best_model,
                    f"{best_temp}",
                    f"{best_score:.2f}",
                    f"+{improvement:.2f} ({improvement_pct:.1f}%)",
                )

            console.print(detailed_table)

            # Create a table showing all metrics by difficulty
            console.rule("[bold magenta]All Metrics by Difficulty")

            # Find all score columns
            score_columns = [
                col
                for col in all_metrics_df.columns
                if "score" in col.lower() and col != response_col
            ]

            # Add response column to the list if not already included
            if response_col and response_col not in score_columns:
                score_columns.append(response_col)

            # Create the table
            metrics_by_difficulty_table = Table(title="All Metrics by Difficulty Level")
            metrics_by_difficulty_table.add_column("Difficulty", style="cyan")

            # Add columns for each metric
            for col in sorted(score_columns):
                # Clean up column name for display
                clean_name = col.replace("_score", "").replace("_", " ").title()
                metrics_by_difficulty_table.add_column(clean_name, style="green")

            # Add rows for each difficulty level
            for difficulty in sorted(all_metrics_df[difficulty_col].unique()):
                difficulty_data = all_metrics_df[
                    all_metrics_df[difficulty_col] == difficulty
                ]

                row_values = [difficulty]

                for col in sorted(score_columns):
                    if col in difficulty_data.columns:
                        avg_score = difficulty_data[col].mean()
                        row_values.append(f"{avg_score:.2f}")
                    else:
                        row_values.append("N/A")

                metrics_by_difficulty_table.add_row(*row_values)

            console.print(metrics_by_difficulty_table)
        else:
            console.print(
                "[yellow]Warning: Missing difficulty or response correctness columns in metrics data[/yellow]"
            )
    else:
        console.print(
            "[yellow]Warning: No detailed metrics available for difficulty analysis[/yellow]"
        )


def render_temperature_analysis(all_results, console=None):
    """
    Analyze performance by temperature.

    Args:
        all_results: List of evaluation result dictionaries
        console: Optional Rich console instance. If None, a new one will be created.
    """
    # Use provided console or create a new one if not provided
    if console is None:
        console = Console()

    # Create a function to extract the base model name (ignoring parentheses)
    def get_base_model_name(full_name):
        # Remove anything in parentheses and trim whitespace
        base_name = re.sub(r"\s*\([^)]*\)", "", full_name).strip()
        return base_name

    # Create a dataframe with all detailed metrics and model info
    all_detailed_metrics = []

    for result in all_results:
        config = result["config"]
        detailed_metrics = result["detailed_metrics"].copy()

        # Skip if detailed_metrics is empty
        if detailed_metrics.empty:
            continue

        # Get base model name and temperature
        base_model = get_base_model_name(config["name"])
        temperature = config["temperature"]

        # Add model info to detailed metrics
        detailed_metrics["Base Model"] = base_model
        detailed_metrics["Temperature"] = temperature
        detailed_metrics["Model Config"] = f"{base_model} (T={temperature})"

        all_detailed_metrics.append(detailed_metrics)

    # Only proceed if we have data
    if all_detailed_metrics:
        all_metrics_df = pd.concat(all_detailed_metrics, ignore_index=True)

        # Find response correctness column
        response_col = next(
            (
                col
                for col in all_metrics_df.columns
                if "response" in col.lower() and "score" in col.lower()
            ),
            None,
        )

        if "Temperature" in all_metrics_df.columns and response_col:
            # Convert temperature to string to ensure proper categorical plotting
            all_metrics_df["Temperature"] = all_metrics_df["Temperature"].astype(str)

            # Create a simple, clean figure
            plt.figure(figsize=(12, 7))

            # Plot performance by temperature
            ax = sns.boxplot(
                x="Temperature",
                y=response_col,
                data=all_metrics_df,
                palette="pastel",
                width=0.6,
            )

            # Simple, clean styling
            plt.title("Response Quality by Temperature", fontsize=16)
            plt.xlabel("Temperature", fontsize=14)
            plt.ylabel("Response Quality Score", fontsize=14)

            # Add the overall average line
            overall_mean = all_metrics_df[response_col].mean()
            plt.axhline(y=overall_mean, color="red", linestyle="--", linewidth=1.5)
            plt.text(
                len(all_metrics_df["Temperature"].unique()) - 0.5,
                overall_mean + 0.05,
                f"Overall Mean: {overall_mean:.2f}",
                ha="right",
                color="red",
                fontweight="bold",
            )

            # Add mean values as annotations below the boxes
            for i, temp in enumerate(sorted(all_metrics_df["Temperature"].unique())):
                temp_data = all_metrics_df[all_metrics_df["Temperature"] == temp]
                mean_score = temp_data[response_col].mean()

                # Calculate the bottom of the box
                q1 = temp_data[response_col].quantile(0.25)
                q3 = temp_data[response_col].quantile(0.75)
                iqr = q3 - q1
                bottom = max(temp_data[response_col].min(), q1 - 1.5 * iqr)

                # Place text below the box
                plt.text(
                    i,
                    bottom - 0.2,
                    f"Mean: {mean_score:.2f}",
                    ha="center",
                    va="top",
                    fontweight="bold",
                    fontsize=11,
                )

            # Save and show
            plt.tight_layout()
            plt.savefig("response_quality_by_temperature.png", dpi=300)
            plt.show()

            # Create a detailed table showing best model for each temperature
            console.rule("[bold magenta]Best Model Configuration by Temperature")

            detailed_table = Table(
                title="Best Model Configuration for Each Temperature"
            )
            detailed_table.add_column("Temperature", style="cyan")
            detailed_table.add_column("Best Model", style="green")
            detailed_table.add_column("Score", style="magenta")
            detailed_table.add_column("Improvement Over Avg", style="blue")

            # Add rows for each temperature level
            for temp in sorted(all_metrics_df["Temperature"].unique()):
                temp_data = all_metrics_df[all_metrics_df["Temperature"] == temp]
                avg_score = temp_data[response_col].mean()

                # Group by model to find the best configuration
                grouped = (
                    temp_data.groupby(["Base Model"])[response_col].mean().reset_index()
                )
                best_idx = grouped[response_col].idxmax()
                best_model = grouped.loc[best_idx, "Base Model"]
                best_score = grouped.loc[best_idx, response_col]

                # Calculate improvement over average
                improvement = best_score - avg_score
                improvement_pct = (
                    (improvement / avg_score) * 100 if avg_score > 0 else 0
                )

                detailed_table.add_row(
                    temp,
                    best_model,
                    f"{best_score:.2f}",
                    f"+{improvement:.2f} ({improvement_pct:.1f}%)",
                )

            console.print(detailed_table)

            # Create a table showing all metrics by temperature
            console.rule("[bold magenta]All Metrics by Temperature")

            # Find all score columns
            score_columns = [
                col
                for col in all_metrics_df.columns
                if "score" in col.lower() and col != response_col
            ]

            # Add response column to the list if not already included
            if response_col and response_col not in score_columns:
                score_columns.append(response_col)

            # Create the table
            metrics_by_temp_table = Table(title="All Metrics by Temperature")
            metrics_by_temp_table.add_column("Temperature", style="cyan")

            # Add columns for each metric
            for col in sorted(score_columns):
                # Clean up column name for display
                clean_name = col.replace("_score", "").replace("_", " ").title()
                metrics_by_temp_table.add_column(clean_name, style="green")

            # Add rows for each temperature level
            for temp in sorted(all_metrics_df["Temperature"].unique()):
                temp_data = all_metrics_df[all_metrics_df["Temperature"] == temp]

                row_values = [temp]

                for col in sorted(score_columns):
                    if col in temp_data.columns:
                        avg_score = temp_data[col].mean()
                        row_values.append(f"{avg_score:.2f}")
                    else:
                        row_values.append("N/A")

                metrics_by_temp_table.add_row(*row_values)

            console.print(metrics_by_temp_table)
        else:
            console.print(
                "[yellow]Warning: Missing temperature or response correctness columns in metrics data[/yellow]"
            )
    else:
        console.print(
            "[yellow]Warning: No detailed metrics available for temperature analysis[/yellow]"
        )


def render_conclusion(all_results, console=None):
    """
    Generate a comprehensive conclusion with key findings from the evaluation results.

    Args:
        all_results: List of evaluation result dictionaries
        console: Optional Rich console instance. If None, a new one will be created.
    """
    # Use provided console or create a new one if not provided
    if console is None:
        console = Console()

    console.rule("[bold magenta]Evaluation Summary")

    # First create the comparison dataframe if it doesn't exist
    comparison_data = []
    for result in all_results:
        config = result["config"]
        metrics = result["summary_metrics"]

        row = {
            "Model": config["name"],
            "Model ID": config["model_id"],
            "Temperature": config["temperature"],
        }

        # Add only mean values of metrics for cleaner comparison
        for metric_key, value in metrics.items():
            if "/Mean" in metric_key:
                # Clean up metric name for display
                clean_metric = (
                    metric_key.replace("/Mean", "")
                    .replace("_score", "")
                    .replace("_", " ")
                    .title()
                )
                row[clean_metric] = value

        comparison_data.append(row)

    comparison_df = pd.DataFrame(comparison_data)

    # Get metric columns (excluding metadata columns)
    metric_columns = [
        col
        for col in comparison_df.columns
        if col not in ["Model", "Model ID", "Temperature"]
    ]

    # Calculate best model for each metric
    best_models = {}
    worst_models = {}
    for metric in metric_columns:
        best_idx = comparison_df[metric].idxmax()
        worst_idx = comparison_df[metric].idxmin()
        best_models[metric] = {
            "model": comparison_df.loc[best_idx, "Model"],
            "score": comparison_df.loc[best_idx, metric],
            "temperature": comparison_df.loc[best_idx, "Temperature"],
        }
        worst_models[metric] = {
            "model": comparison_df.loc[worst_idx, "Model"],
            "score": comparison_df.loc[worst_idx, metric],
        }

    # Create summary table
    summary_table = Table(title="Evaluation Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Best Model", style="green")
    summary_table.add_column("Score", style="yellow")
    summary_table.add_column("Temperature", style="magenta")

    for metric, data in best_models.items():
        summary_table.add_row(
            metric, data["model"], f"{data['score']:.2f}", f"{data['temperature']}"
        )

    console.print(summary_table)

    # Calculate average scores by model
    model_avg_scores = {}
    for _, row in comparison_df.iterrows():
        model = row["Model"]
        scores = [row[m] for m in metric_columns]
        avg_score = sum(scores) / len(scores)
        model_avg_scores[model] = avg_score

    # Find overall best model
    overall_best_model = max(model_avg_scores.items(), key=lambda x: x[1])

    # Find best temperature if we have temperature data
    temp_analysis = {}
    if "Temperature" in comparison_df.columns:
        for temp in comparison_df["Temperature"].unique():
            temp_df = comparison_df[comparison_df["Temperature"] == temp]
            if not temp_df.empty:
                avg_scores = [temp_df[m].mean() for m in metric_columns]
                temp_analysis[temp] = sum(avg_scores) / len(avg_scores)

        if temp_analysis:  # Check if we have any temperature data
            best_temp = max(temp_analysis.items(), key=lambda x: x[1])
            worst_temp = min(temp_analysis.items(), key=lambda x: x[1])

    # Find strongest and weakest metrics
    metric_avgs = {metric: comparison_df[metric].mean() for metric in metric_columns}
    strongest_metric = max(metric_avgs.items(), key=lambda x: x[1])
    weakest_metric = min(metric_avgs.items(), key=lambda x: x[1])

    # Generate dynamic key findings
    key_findings = f"""
[bold]Key Findings:[/bold]

1. [bold cyan]Overall Performance:[/bold cyan] {overall_best_model[0]} is the best performing model with an average score of {overall_best_model[1]:.2f} across all metrics.

2. [bold cyan]Metric-Specific Performance:[/bold cyan]
   - Best metric: {strongest_metric[0]} (avg: {strongest_metric[1]:.2f})
   - Most challenging metric: {weakest_metric[0]} (avg: {weakest_metric[1]:.2f})
"""

    # Add temperature findings if available
    if "Temperature" in comparison_df.columns and temp_analysis:
        key_findings += f"""
3. [bold cyan]Temperature Impact:[/bold cyan] Temperature {best_temp[0]} yielded the best overall performance (avg: {best_temp[1]:.2f}), while temperature {worst_temp[0]} performed worst (avg: {worst_temp[1]:.2f}).
"""

    # Add model-specific insights
    key_findings += """
4. [bold cyan]Model-Specific Insights:[/bold cyan]
"""

    for metric in metric_columns:
        best = best_models[metric]
        worst = worst_models[metric]
        key_findings += f"   - {metric}: {best['model']} excels ({best['score']:.2f}), while {worst['model']} struggles ({worst['score']:.2f}).\n"

    # Add next steps
    key_findings += """
[bold]Next Steps:[/bold]

1. Deploy the best-performing model configuration ({}) for production use
2. Focus on improving performance in the weakest metric area: {}
3. {}
4. Expand the evaluation dataset with more diverse scenarios
5. Implement continuous evaluation to monitor agent performance over time
""".format(
        overall_best_model[0],
        weakest_metric[0],
        (
            f"Conduct further temperature tuning around the optimal value of {best_temp[0]}"
            if "Temperature" in comparison_df.columns and temp_analysis
            else "Experiment with different temperature settings to optimize performance"
        ),
    )

    console.print(key_findings)

    return {
        "best_model": overall_best_model[0],
        "best_model_score": overall_best_model[1],
        "best_temperature": (
            best_temp[0]
            if "Temperature" in comparison_df.columns and temp_analysis
            else None
        ),
        "strongest_metric": strongest_metric[0],
        "weakest_metric": weakest_metric[0],
        "metric_details": best_models,
    }
