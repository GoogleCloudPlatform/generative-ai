# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utility functions and classes for the VAPO notebook."""
import csv
import io
import json
import re

from IPython.core.display import DisplayHandle
from IPython.display import HTML, display
from google.cloud import aiplatform, storage
import ipywidgets as widgets
import jinja2
import jinja2.meta
import pandas as pd
from tensorflow.io import gfile


def is_target_required_metric(eval_metric: str) -> bool:
    """Check if the metric requires the target label."""
    return eval_metric in [
        "bleu",
        "exact_match",
        "question_answering_correctness",
        "rouge_1",
        "rouge_2",
        "rouge_l",
        "rouge_l_sum",
        "tool_call_valid",
        "tool_name_match",
        "tool_parameter_key_match",
        "tool_parameter_kv_match",
    ]


def is_run_target_required(eval_metric_types: list[str], source_model: str) -> bool:
    """Check if the run requires the target label."""
    if source_model:
        return False

    label_required = False
    for metric in eval_metric_types:
        label_required = label_required or is_target_required_metric(metric)
    return label_required


_TARGET_KEY = "target"


def load_file_from_gcs(dataset: str) -> str:
    """Loads the file from GCS and returns it as a string."""
    if dataset.startswith("gs://"):
        with gfile.GFile(dataset, "r") as f:
            return f.read()
    else:
        raise ValueError(
            "Unsupported file location. Only GCS paths starting with 'gs://' are"
            " supported."
        )


def parse_jsonl(data_str: str) -> list[dict[str, str]]:
    """Parses the content of a JSONL file and returns a list of dictionaries."""
    data = []
    lines = data_str.splitlines()
    for line in lines:
        if line:
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Error decoding JSON on line: {line}. Error: {e}"
                ) from e
    return data


def parse_and_validate_csv(data_str: str) -> list[dict[str, str]]:
    """Parses and validates the content of a CSV file and returns a list of dictionaries."""
    data = []
    csv_reader = csv.reader(io.StringIO(data_str))

    # Extract and validate headers
    try:
        headers = next(csv_reader)
        if not headers:
            raise ValueError("The CSV file has an empty or invalid header row.")
    except StopIteration as e:
        raise ValueError("The CSV file is empty.") from e

    # Validate and process rows
    for row_number, row in enumerate(csv_reader, start=2):
        if len(row) != len(headers):
            raise ValueError(
                f"Row {row_number} has an inconsistent number of fields. "
                f"Expected {len(headers)} fields but found {len(row)}."
            )
        # Create dictionary for each row using headers as keys
        item = dict(zip(headers, row))
        data.append(item)

    return data


def load_dataset(dataset: str) -> list[dict[str, str]]:
    """Loads and parses the dataset based on its file type ('.jsonl' or '.csv')."""
    # Load the file from GCS
    data_str = load_file_from_gcs(dataset)

    # Parse based on file type
    if dataset.endswith(".jsonl"):
        return parse_jsonl(data_str)

    if dataset.endswith(".csv"):
        return parse_and_validate_csv(data_str)

    raise ValueError(
        "Unsupported file type. Please provide a file with '.jsonl' or '.csv'"
        " extension."
    )


def validate_prompt_and_data(
    template: str,
    dataset_path: str,
    placeholder_to_content: str,
    label_enforced: bool,
) -> None:
    """Validates the prompt template and the dataset."""
    data = load_dataset(dataset_path)
    placeholder_to_content_json = json.loads(placeholder_to_content)
    template = re.sub(r"(?<!{){(?!{)(\s*\w+\s*)(?<!})}(?!})", r"{{\1}}", template)
    env = jinja2.Environment()
    try:
        parsed_content = env.parse(template)
    except jinja2.exceptions.TemplateSyntaxError as e:
        raise ValueError(f"Invalid template: {template}") from e

    template_variables = jinja2.meta.find_undeclared_variables(parsed_content)
    extra_keys = set()
    for ex in data:
        ex.update(placeholder_to_content_json)
        missing_keys = [key for key in template_variables if key not in ex]
        extra_keys.update([key for key in ex if key not in template_variables])
        if label_enforced:
            if _TARGET_KEY not in ex:
                raise ValueError(
                    f"The example {ex} doesn't have a key corresponding to the target"
                    f" var: {_TARGET_KEY}"
                )
            if not ex[_TARGET_KEY]:
                raise ValueError(f"The following example has an empty target: {ex}")
        if missing_keys:
            raise ValueError(
                f"The example {ex} doesn't have a key corresponding to following"
                f" template vars: {missing_keys}"
            )
    if extra_keys:
        raise Warning(
            "Warning: extra keys in the examples not used in the prompt template"
            f" template {extra_keys}"
        )


def run_custom_job(
    display_name: str,
    container_uri: str,
    container_args: dict[str, str],
) -> str:
    """A sample to create custom jobs."""
    worker_pool_specs = [
        {
            "replica_count": 1,
            "container_spec": {
                "image_uri": container_uri,
                "args": [f"--{k}={v}" for k, v in container_args.items()],
            },
            "machine_spec": {
                "machine_type": "n1-standard-4",
            },
        }
    ]

    custom_job = aiplatform.CustomJob(
        display_name=display_name,
        worker_pool_specs=worker_pool_specs,
    )
    custom_job.submit()
    return custom_job


def run_apd(config: dict[str, str], bucket_uri: str, display_name: str) -> str:
    """A function to the vertex prompt optimizer."""
    print(f"\n\nJob display name: {display_name}")
    version = "preview_v1_0"
    container_uri = "us-docker.pkg.dev/vertex-ai-restricted/builtin-algorithm/apd"
    config_path = f"{bucket_uri}/{display_name}/input_config.json"

    with gfile.GFile(config_path, "w") as f:
        json.dump(config, f)

    aiplatform.init(
        project=config["project"],
        location=config["target_model_location"],
        staging_bucket=f"{bucket_uri}/{display_name}",
    )

    return run_custom_job(
        display_name=display_name,
        container_uri=f"{container_uri}:{version}",
        container_args={"config": config_path},
    )


def update_best_display(
    df: pd.DataFrame,
    textarea: widgets.Textarea,
    best_score_label: widgets.Label,
    eval_metric: str,
) -> None:
    """Update the best prompt display."""

    df["score"] = df[f"metrics.{eval_metric}/mean"]

    best_template = df.loc[df["score"].argmax(), "prompt"]
    best_score = df.loc[df["score"].argmax(), "score"]
    original_score = df.loc[0, "score"]

    def placeholder_llm() -> str:
        return "{{llm()}}"

    env = jinja2.Environment(loader=jinja2.BaseLoader())
    env.globals["llm"] = placeholder_llm

    best_template = best_template.replace("store('answer', llm())", "llm()")
    textarea.value = best_template
    improvement = best_score - original_score
    no_improvement_str = "\nNo better template is found yet." if not improvement else ""
    best_score_label.value = (
        f"Score: {best_score}" f" Improvement: {improvement: .3f} {no_improvement_str}"
    )


def generate_dataframe(filename: str) -> pd.DataFrame:
    """Generates a pandas dataframe from a json file."""
    if not gfile.exists(filename):
        return pd.DataFrame()

    with gfile.GFile(filename, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            return pd.DataFrame()
    return pd.json_normalize(data)


def left_aligned_df_html(df: pd.DataFrame) -> HTML:
    """Displays a Pandas DataFrame in Colab with left-aligned values."""

    # Convert to HTML table, but keep the HTML in a variable
    html_table = df.to_html(index=False, classes="left-aligned")

    # Add CSS styling to left-align table data cells and override default styles
    styled_html = f"""
    <style>
        .left-aligned td, .left-aligned th {{ text-align: left !important; }}
    </style>
    {html_table}
    """

    # Display the styled HTML table
    return HTML(styled_html)


def extract_top_level_function_name(source_code: str) -> str | None:
    """Extract the top level function name from the source code."""
    match = re.search(r"^def\s+([a-zA-Z_]\w*)\s*\(", source_code, re.MULTILINE)
    if match:
        return match.group(1)
    return None


class ProgressForm:
    """A class to display the progress of the optimization job."""

    # pylint: disable=too-many-instance-attributes

    def __init__(self, params: dict[str, str]) -> None:
        """Initialize the progress form."""
        self.instruction_progress_bar = None
        self.instruction_display = None
        self.instruction_best = None
        self.instruction_score = None
        self.demo_progress_bar = None
        self.demo_display = None
        self.demo_best = None
        self.demo_score = None

        self.job_state_display = display(
            HTML("<span>Job State: Not Started!</span>"), display_id=True
        )
        self.status_display = display(HTML(""), display_id=True)

        if params["optimization_mode"] in ["instruction", "instruction_and_demo"]:
            (
                self.instruction_progress_bar,
                self.instruction_display,
                self.instruction_best,
                self.instruction_score,
            ) = self.create_progress_ui("Instruction", params["num_steps"])

        if params["optimization_mode"] in ["demonstration", "instruction_and_demo"]:
            (
                self.demo_progress_bar,
                self.demo_display,
                self.demo_best,
                self.demo_score,
            ) = self.create_progress_ui(
                "Demonstration", params["num_demo_set_candidates"]
            )

        if len(params["eval_metrics_types"]) == 1:
            self.eval_metric = params["eval_metrics_types"][0]
        else:
            self.eval_metric = "composite_metric"

        self.output_path = params["output_path"]
        self.instruction_df = None
        self.demo_df = None

    # pylint: disable=too-many-arguments
    def update_progress(
        self,
        progress_bar: widgets.IntProgress | None,
        templates_file: str,
        df: pd.DataFrame | None,
        df_display: DisplayHandle,
        best_textarea: widgets.Textarea,
        best_score: widgets.Label,
        eval_metric: str,
    ) -> pd.DataFrame:
        """Update the progress of the optimization job."""

        def get_last_step(df: pd.DataFrame) -> int:
            if df.empty:
                return -1
            return int(df["step"].max())

        if progress_bar is None or df is None:
            return pd.DataFrame()

        new_df = generate_dataframe(templates_file)

        last_step = get_last_step(df)
        new_last_step = get_last_step(new_df)
        if new_last_step > last_step:
            df_display.update(left_aligned_df_html(new_df))
            update_best_display(new_df, best_textarea, best_score, eval_metric)
            progress_bar.value = progress_bar.value + new_last_step - last_step

        return new_df

    def create_progress_ui(
        self, opt_mode: str, num_opt_steps: str
    ) -> tuple[widgets.IntProgress, DisplayHandle, widgets.Textarea, widgets.Label]:
        """Create the progress UI for a specific optimization mode."""
        print(f"\n\n{opt_mode} Optimization")
        progress_bar = widgets.IntProgress(
            value=0, min=0, max=int(num_opt_steps), step=1, description="Progress"
        )
        display(progress_bar)
        print("\nGenerated Templates:")
        templates_display = display("No template is evaluated yet!", display_id=True)

        print("\nBest Template so far:")
        best_textarea = widgets.Textarea(
            value="NA",
            disabled=False,
            layout=widgets.Layout(width="80%", height="150px"),
        )
        display(best_textarea)

        best_score = widgets.Label(value="Score: NA Improvement: NA")
        display(best_score)

        return progress_bar, templates_display, best_textarea, best_score

    def monitor_progress(self, job: aiplatform.CustomJob) -> bool:
        """Monitor the progress of the optimization job."""
        self.job_state_display.update(HTML(f"<span>Job State: {job.state.name}</span>"))

        # Initial display of the templates.
        instruction_templates_file = f"{self.output_path}/instruction/templates.json"
        demo_templates_file = f"{self.output_path}/demonstration/templates.json"

        if not job.done():
            self.instruction_df = self.update_progress(
                self.instruction_progress_bar,
                instruction_templates_file,
                self.instruction_df,
                self.instruction_display,
                self.instruction_best,
                self.instruction_score,
                self.eval_metric,
            )
            self.demo_df = self.update_progress(
                self.demo_progress_bar,
                demo_templates_file,
                self.demo_df,
                self.demo_display,
                self.demo_best,
                self.demo_score,
                self.eval_metric,
            )
            return True

        if job.state.name != "JOB_STATE_SUCCEEDED":
            errors = [f"Error: Job failed with error {job.error}."]
            for err_file in [
                f"{self.output_path}/instruction/error.json",
                f"{self.output_path}/demonstration/error.json",
            ]:
                if gfile.exists(err_file):
                    with gfile.GFile(err_file, "r") as f:
                        error_json = json.load(f)
                    errors.append(f"Detailed error: {error_json}")
                    errors.append(
                        f"Please feel free to send {err_file} to the VAPO team to help"
                        " resolving the issue."
                    )

            errors.append(
                "All the templates found before failure can be found under"
                f" {self.output_path}"
            )
            errors.append(
                "Please consider rerunning to make sure the failure is intransient."
            )
            err = "\n".join(errors)
            self.status_display.update(HTML(f'<span style="color: red;">{err}</span>'))
        else:
            self.status_display.update(
                HTML(
                    '<span style="color: green;">Job succeeded!</span> <span>All the'
                    f" artifacts can be found under {self.output_path}</span>"
                )
            )
        return False


def display_dataframe(df: pd.DataFrame) -> None:
    """Display a pandas dataframe in Colab."""

    # Function to wrap text in a scrollable div
    def wrap_in_scrollable_div(text: str) -> str:
        return f'<div class="scrollable">{text}</div>'

    # Apply the function to every cell using the format method
    styled_html = df.style.format(wrap_in_scrollable_div).to_html(index=False)

    # Display the HTML in the notebook
    display(HTML(styled_html))


def split_gcs_path(gcs_path: str) -> tuple[str, str]:
    """Splits a full GCS path into bucket name and prefix."""
    if gcs_path.startswith("gs://"):
        path_without_scheme = gcs_path[5:]  # Remove the 'gs://' part
        parts = path_without_scheme.split("/", 1)
        bucket_name = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""
        return bucket_name, prefix

    raise ValueError("Invalid GCS path. Must start with 'gs://'")


def list_gcs_objects(full_gcs_path: str) -> list[str]:
    """Lists all the objects in the given GCS path."""
    bucket_name, prefix = split_gcs_path(full_gcs_path)
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(
        prefix=prefix
    )  # List all objects that start with the prefix

    return [blob.name for blob in blobs]


def find_directories_with_files(
    full_gcs_path: str, required_files: list[str]
) -> list[str]:
    """Finds directories containing specific files under the given full GCS path."""
    bucket_name, prefix = split_gcs_path(full_gcs_path)
    all_paths = list_gcs_objects(f"gs://{bucket_name}/{prefix}")
    directories = set()

    # Create a dictionary to track files found in each directory
    file_presence: dict[str, set[str]] = {}
    for path in all_paths:
        directory = "/".join(path.split("/")[:-1])  # Get the directory part of the path
        filename = path.split("/")[-1]  # Get the filename part of the path
        if directory:
            if directory not in file_presence:
                file_presence[directory] = set()
            file_presence[directory].add(filename)

    # Check which directories have all required files
    for directory, files in file_presence.items():
        if all(file in files for file in required_files):
            directories.add(f"gs://{bucket_name}/{directory}")

    return list(directories)


def extract_metric_name(metric_string: str) -> str:
    """Extract the metric name from a string."""
    # Use a regular expression to find the metric name
    match = re.search(r"\.(\w+)/", metric_string)
    # Return the matched group if found
    return match.group(1) if match else metric_string


def read_file_from_gcs(filename: str) -> str:
    """Read a file from GCS."""
    with gfile.GFile(filename, "r") as f:
        return f.read()


def process_results(df: pd.DataFrame) -> pd.DataFrame:
    """Process the results removing columns that could be confusing."""
    columns_to_drop = []
    # Dropping columns that could be confusing.
    for col in df.columns:
        if "confidence" in col:
            columns_to_drop.append(col)
        if "raw_eval_resp" in col:
            columns_to_drop.append(col)
        if col == "instruction":
            columns_to_drop.append(col)
        if col == "context":
            columns_to_drop.append(col)
    return df.drop(columns=columns_to_drop)


class ResultsUI:
    """A UI to display the results of a VAPO run."""

    def __init__(self, path: str) -> None:
        """Initialize the UI."""
        required_files = ["eval_results.json", "templates.json"]
        runs = find_directories_with_files(path, required_files)

        self.run_label = widgets.Label("Select Run:")
        self.run_dropdown = widgets.Dropdown(
            options=runs, value=runs[0], layout=widgets.Layout(width="200px")
        )
        self.run_dropdown.observe(self.display_run_handler, names="value")

        # Create a label widget for the description
        self.dropdown_description = widgets.Label("Select Template:")
        self.template_dropdown = widgets.Dropdown(
            options=[],
            value=None,
            layout=widgets.Layout(width="400px"),
            disabled=True,
        )
        self.template_dropdown.observe(self.display_template_handler, names="value")
        self.results_output = widgets.Output(
            layout=widgets.Layout(
                height="600px", overflow="auto", margin="20px 0px 0px 0px"
            )
        )
        self.display_run(runs[0])

    def display_template_handler(self, change: dict[str, str | None]) -> None:
        """Display the template and the corresponding evaluation results."""
        if change["new"] is None:
            return

        df_index = int(change["new"].split(" ")[1])
        self.display_eval_results(df_index)

    def display_run_handler(self, change: dict[str, str | None]) -> None:
        """Display the run and the corresponding templates."""
        if change["new"] is None:
            return

        path = change["new"]
        self.display_run(path)

    def display_run(self, path: str) -> None:
        """Display the results of a VAPO run."""
        self.run_dropdown.disabled = True
        filename = f"{path}/eval_results.json"
        eval_results = json.loads(read_file_from_gcs(filename))

        filename = f"{path}/templates.json"
        templates = json.loads(read_file_from_gcs(filename))

        if len(templates) == len(eval_results):
            offset = 0
        elif len(templates) == len(eval_results) + 1:
            # In some setups it is possible to have 1 more template than results.
            offset = 1
        else:
            raise ValueError(
                "Number of templates doesn't match number of eval results"
                f" {len(templates)} vs {len(eval_results)}"
            )
        self.templates = [
            pd.json_normalize(template) for template in templates[offset:]
        ]
        metric_columns = [col for col in self.templates[0].columns if "metric" in col]

        self.eval_results = [
            process_results(pd.read_json(io.StringIO(result["metrics_table"])))
            for result in eval_results
        ]
        options = []
        for i, template in enumerate(self.templates):
            metrics = []
            for col in metric_columns:
                value = template[col].tolist()[0]
                short_col = extract_metric_name(col)
                metrics.append(f"{short_col}: {value}")
            metrics_str = " ".join(metrics)
            options.append(f"Template {i} {metrics_str}")

        self.template_dropdown.disabled = False
        self.template_dropdown.options = options
        self.run_dropdown.disabled = False

    def display_eval_results(self, index: int) -> None:
        """Display the evaluation results for a specific template."""
        with self.results_output:
            self.results_output.clear_output(wait=True)  # Clear previous output
            display_dataframe(self.templates[index])
            print()
            display_dataframe(self.eval_results[index])

    def get_container(self) -> widgets.Output:
        """Get the container widget for the results UI."""
        return widgets.VBox(
            [
                self.run_label,
                self.run_dropdown,
                self.dropdown_description,
                self.template_dropdown,
                self.results_output,
            ]
        )
