# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Tools for deploying the end-to-end Concierge demo."""

import click
from scripts.cli import langgraph_demo
import yaml


@click.group(help="Gen AI Experience Concierge demo tool.")
@click.option(
    "-f",
    "--config-file",
    required=False,
    help="YAML config file to configure command/subcommand defaults.",
    type=click.Path(exists=True, dir_okay=False, readable=True, resolve_path=True),
    default=None,
)
@click.pass_context
def concierge(ctx: click.Context, config_file: str | None = None) -> None:
    """Gen AI Experience Concierge demo tool."""

    ctx.ensure_object(dict)

    if config_file is None:
        return

    with open(config_file, "r", encoding="utf-8") as f:
        default_map = yaml.safe_load(f)
        ctx.default_map = default_map


def langgraph_demo_group() -> None:
    """LangGraph demo group. No group-level operations currently."""


langgraph_group = concierge.group(
    name="langgraph",
    help="Gen AI Experience Concierge demo orchestrated with LangGraph.",
)(langgraph_demo_group)

langgraph_dataset_creation_cmd = langgraph_group.command(
    help="""
Create a Cymbal Retail dataset and embedding model in the target project.
NOTE: This command does not need to be run if using the end-to-end deployment.
""".strip()
)(langgraph_demo.create_dataset)

langgraph_deploy_cmd = langgraph_group.command(
    help=""""
End-to-end deployment including project creation, infrastructure provisioning,
container builds and deployment with IAP authentication.
""".strip()
)(langgraph_demo.deploy)
