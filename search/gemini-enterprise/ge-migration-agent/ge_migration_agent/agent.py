import json
import os
import logging
import subprocess
import shutil
import sys
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(env_path, override=True)
from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.skill_toolset import SkillToolset
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from skills import migration_skill

PROJECT_NUMBER = os.environ.get("GEMINI_API_PROJECT")
LOCATION = os.environ.get("GEMINI_API_LOCATION", "global")
MODEL_NAME = os.environ.get("GEMINI_API_MODEL") or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
if "/" not in MODEL_NAME:
    MODEL_PATH = f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/publishers/google/models/{MODEL_NAME}"
else:
    MODEL_PATH = MODEL_NAME

def run_cli(args: list[str]) -> str:
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cli_path = os.path.join(script_dir, "migrate.py")
    
    if shutil.which("uv"):
        cmd = ["uv", "run", cli_path, "--json"] + args
    else:
        cmd = [sys.executable, cli_path, "--json"] + args
        
    try:
        logging.info(f"Running CLI: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        logging.error(f"CLI failed with exit code {e.returncode}: {e.stderr}")
        return json.dumps({"error": f"CLI command failed: {e.stderr.strip() or e.stdout.strip()}"})
    except Exception as e:
        logging.error(f"Execution error: {e}")
        return json.dumps({"error": str(e)})


def list_notebooks(tool_context: ToolContext) -> str:
    """Call this tool to get a list of recently viewed notebooks."""
    return run_cli(["list-notebooks"])


def list_sources_and_types(tool_context: ToolContext, notebook_id: str) -> str:
    """Call this tool to list sources and their types for a specific notebook.

    Args:
        notebook_id: The ID of the notebook.
    """
    return run_cli(["list-sources", notebook_id])


def create_notebook(tool_context: ToolContext, title: str) -> str:
    """Call this tool to create a new notebook.

    Args:
        title: The title of the notebook to create.
    """
    return run_cli(["create-notebook", title])


def add_source_to_notebook(tool_context: ToolContext, notebook_id: str, source_content: str) -> str:
    """Call this tool to add a source to a notebook.

    Args:
        notebook_id: The ID of the notebook to add the source to.
        source_content: The JSON string of the userContent to add.
    """
    return run_cli(["add-source-to-notebook", notebook_id, source_content])


def list_employee_agents(tool_context: ToolContext) -> str:
    """Call this tool to list all employee-made low-code agents."""
    return run_cli(["list-agents"])


def get_agent_details(tool_context: ToolContext, agent_name: str) -> str:
    """Call this tool to retrieve the configuration details (instructions, model, connectors, and sub-agents) of a specific employee agent by name.

    Args:
        agent_name: The exact display name of the agent to retrieve details for.
    """
    return run_cli(["get-agent-details", agent_name])


def extract_agent_datastores(tool_context: ToolContext, source_agent_name: str) -> str:
    """Call this tool to extract and list the names of datastores used by an agent and its subagents.
    
    Args:
        source_agent_name: The exact display name of the source agent.
    """
    return run_cli(["extract-datastores", source_agent_name])


def migrate_agent(
    tool_context: ToolContext,
    source_agent_name: str,
    force: bool = False,
    connector_mapping: str = ""
) -> str:
    """Call this tool to migrate (create) an employee-made low-code agent to a target environment.
    
    Args:
        source_agent_name: The exact display name of the source agent to migrate.
        force: Set to True to proceed with migration even if some dependencies are missing.
        connector_mapping: Optional JSON dict or mapping string.
    """
    args = ["migrate-agent", source_agent_name]
    if force:
        args.append("--force")
    if connector_mapping:
        args.extend(["--connector-mapping", connector_mapping])
    return run_cli(args)


def migrate_notebook(
    tool_context: ToolContext,
    notebook_name_or_id: str,
    backup_bucket: str = ""
) -> str:
    """Call this tool to migrate an entire NotebookLM notebook and all its sources to the target environment.
    This will also implicitly upload a backup of the notebook definition to a GCS bucket first.
    
    Args:
        notebook_name_or_id: The exact title or ID of the source notebook to migrate.
        backup_bucket: Optional GCS bucket name for the backup.
    """
    args = ["migrate-notebook", notebook_name_or_id]
    if backup_bucket:
        args.extend(["--backup-bucket", backup_bucket])
    return run_cli(args)


def lookup_and_map_connectors(tool_context: ToolContext, source_agent_name: str) -> str:
    """Call this tool before migrating an agent to look up source connectors, map them intelligently to target connectors, and show the proposed mapping to the user for approval.
    
    Args:
        source_agent_name: The exact display name of the source agent.
    """
    return run_cli(["lookup-map-connectors", source_agent_name])


def export_agent_to_gcs(
    tool_context: ToolContext,
    source_agent_name: str,
    object_name: str,
    bucket_name: str = "",
    source_project_id: str = PROJECT_NUMBER,
    source_location: str = "global",
    source_engine_id: str = "enterprise-search-17416389_1741638989378"
) -> str:
    """Call this tool to export an employee-made low-code agent definition to a GCS bucket.
    
    Args:
        source_agent_name: The exact display name of the source agent to export.
        object_name: The name of the object (file path) in the bucket.
        bucket_name: The name of the GCS bucket to save the definition to. If not provided, reads from GCS_BUCKET_NAME env var.
        source_project_id: The Google Cloud project number of the source environment.
        source_location: The geographic location of the source environment.
        source_engine_id: The Discovery Engine engine ID of the source environment.
    """
    args = ["export-agent-gcs", source_agent_name, object_name, "--engine-id", source_engine_id]
    if bucket_name:
        args.extend(["--bucket", bucket_name])
    if source_project_id:
        args.extend(["--project", source_project_id])
    if source_location:
        args.extend(["--location", source_location])
    return run_cli(args)


def import_agent_from_gcs(
    tool_context: ToolContext,
    object_name: str,
    target_project_id: str,
    target_location: str,
    target_engine_id: str,
    bucket_name: str = "",
) -> str:
    """Call this tool to import an agent definition from GCS and create it in a target environment.
    
    Args:
        object_name: The name of the object (file path) in the bucket.
        target_project_id: The Google Cloud project number of the target environment.
        target_location: The geographic location of the target environment.
        target_engine_id: The Discovery Engine engine ID of the target environment.
        bucket_name: The name of the GCS bucket containing the definition. If not provided, reads from GCS_BUCKET_NAME env var.
    """
    args = [
        "import-agent-gcs", object_name,
        "--target-project", target_project_id,
        "--target-location", target_location,
        "--target-engine", target_engine_id
    ]
    if bucket_name:
        args.extend(["--bucket", bucket_name])
    return run_cli(args)


def export_notebook_to_gcs(
    tool_context: ToolContext,
    notebook_name: str,
    object_name: str,
    bucket_name: str = "",
    source_project_id: str = PROJECT_NUMBER,
    source_location: str = "global",
) -> str:
    """Call this tool to export a NotebookLM notebook definition (including metadata and sources) to a GCS bucket.
    
    Args:
        notebook_name: The exact title or ID of the source notebook to export.
        object_name: The name of the object (file path) in the bucket.
        bucket_name: The name of the GCS bucket to save the definition to. If not provided, reads from GCS_BUCKET_NAME env var.
        source_project_id: The Google Cloud project number of the source environment.
        source_location: The geographic location of the source environment.
    """
    args = ["export-notebook-gcs", notebook_name, object_name]
    if bucket_name:
        args.extend(["--bucket", bucket_name])
    if source_project_id:
        args.extend(["--project", source_project_id])
    if source_location:
        args.extend(["--location", source_location])
    return run_cli(args)


def import_notebook_from_gcs(
    tool_context: ToolContext,
    object_name: str,
    target_project_id: str,
    target_location: str,
    bucket_name: str = "",
) -> str:
    """Call this tool to import a notebook definition from GCS and create it in a target environment.
    
    Args:
        object_name: The name of the object (file path) in the bucket containing the notebook definition JSON.
        target_project_id: The Google Cloud project number of the target environment.
        target_location: The geographic location of the target environment.
        bucket_name: The name of the GCS bucket containing the definition. If not provided, reads from GCS_BUCKET_NAME env var.
    """
    args = [
        "import-notebook-gcs", object_name,
        "--target-project", target_project_id,
        "--target-location", target_location,
    ]
    if bucket_name:
        args.extend(["--bucket", bucket_name])
    return run_cli(args)


def list_datastores(
    tool_context: ToolContext,
    project_id: str,
    location: str = "global"
) -> str:
    """Call this tool to connect to a target location and get a list of all available datastores and their datastore IDs.
    
    Args:
        project_id: The target Google Cloud project number.
        location: The target location (e.g. global).
    """
    return run_cli(["list-datastores", "--project", project_id, "--location", location])


def get_migration_config(tool_context: ToolContext) -> str:
    """Call this tool FIRST upon greeting to retrieve the verified canonical Source and Target environment details and DataStore/Connector mappings directly from SKILL.md / migration_skill.json."""
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
    from skills import migration_skill
    skill = migration_skill.MigrationConfigSkill()
    return json.dumps({
        "environments": {
            "source": skill.get_source_env(),
            "target": skill.get_target_env()
        },
        "datastores_mapping": skill.get_datastores_mapping(),
        "connectors_mapping": skill.get_connectors_mapping()
    }, indent=2)


AGENT_INSTRUCTION = """
You are the Gemini Enterprise App Migration Agent. Your job is to migrate notebooks from one Gemini app to another, and to help users list employee-made agents.

CRITICAL RULES:
1. **Initial Greeting & Configuration Verification**: When a user asks for help or begins the session, FIRST show a clearly formatted bulleted list of tasks/activities you can perform (e.g., Migrate Notebooks, List Employee Agents, Migrate Employee Low-Code Agents). Then call `get_migration_config` to read the real verified migration configuration from `SKILL.md` and show both the active pre-loaded Source and Target environment details (Project Number, Project ID, Region, Engine ID) AND verified DataStore Mappings (`datastores_mapping`) directly on screen. Do NOT display Connector Mappings on screen! Never ask the user to input Project Numbers or Engine IDs!
2. **Mapping Verification**: Before migrating, verify that your active DataStore mappings match `SKILL.md`.
3. **Environment Memory**: Rely entirely on `SKILL.md` configuration defaults for migrations without prompting again.
4. **Name Verification**: When requested to perform an action on a specific agent or notebook, you MUST first verify its exact display name or title. If there is any shorthand, abbreviation, or potential name mismatch, call `list_employee_agents` (for agents) or `list_notebooks` (for notebooks) to find the exact match from the source environment. Use ONLY the exact retrieved display name or title in all subsequent tool calls. Do NOT call any other search or question tools (such as 'search_and_answer').

Workflow:
1. List all notebook apps from the source app (using `list_notebooks`).
2. Ask the user which notebook they want to migrate, or if they want to migrate all of them.
3. Ask the user for the target Gemini Enterprise app details (Project Number and Location).
4. Migrate each selected notebook using `migrate_notebook`. This will automatically save a backup to the GCS bucket first before performing target creation.
5. List employee-made agents using `list_employee_agents`. If you need configuration details (such as instructions, model, connectors, and sub-agents) for a specific agent, you MUST call `get_agent_details` with the exact display name of the agent. Do NOT call any other tool (such as 'get_agent').
6. Migrate (create) employee-made low-code agents to a target Gemini Enterprise environment using `migrate_agent`. This will also implicitly save a backup to a GCS bucket.
7. Export employee-made low-code agents to a GCS bucket using `export_agent_to_gcs` when requested.
8. Import employee-made low-code agents from a GCS bucket to a target environment using `import_agent_from_gcs` when requested.
9. Before migrating an employee-made low-code agent using `migrate_agent`, FIRST call `lookup_and_map_connectors` to look up available connectors in the target environment and intelligently map source connectors (e.g., Snowflake Mcp May29 -> snowflakeMcp). Present the proposed mapping table to the user and GET THEIR APPROVAL on the mapping before calling `migrate_agent` with the approved `connector_mapping`!
10. Export NotebookLM notebooks to a GCS bucket using `export_notebook_to_gcs` when requested.
11. Import NotebookLM notebooks from a GCS bucket to a target environment using `import_notebook_from_gcs` when requested.


Mapping sources:
- Type "google docs": use "googleDriveContent" with documentId extracted from location URL and mimeType "application/vnd.google-apps.document". Do NOT include "sourceName" at the root of the object.
- Type "website": use "webContent" with url. Do NOT include "sourceName" at the root unless confirmed valid.
- Type "copied text": use "textContent" with content.
- Type "youtube": use "videoContent" with youtubeUrl.

Critical Rule: Do NOT delete the source notebook or its sources after migration. This is a read-and-copy operation only.

Output Format:
When presenting lists of notebooks, sources, employee-made agents, or proposed/missing connector and datastore mappings, you MUST format them as complete, pristine Markdown tables:
1. Always include a proper Markdown header and separator row (e.g. `| Display Name | Description |\n|---|---|` or `| Source Connector | Target Mapping | Status |\n|---|---|---|`).
2. Separate each row cleanly with a line break (`\n`).
3. Replace any internal newlines within descriptions/items with spaces or `<br>` so table formatting does not break.
Do NOT output raw JSON or A2UI JSON, as the client cannot render it.

When a user asks for the details of an employee agent (e.g. "give details on Quarterly Business Review Generator"), output the details in exactly the following format without markdown code blocks:

[Agent Description]

Instructions: [Agent Instructions]

Model: [Model Name or "Gemini 3 Flash"]

Connectors: [List of connectors/tools/datastores]

Knowledge: [List of attached knowledge/files/datastores or "None"]

SubAgent : [SubAgent Display Name]
Description: [SubAgent Description]
Instructions: [SubAgent Instructions]
Model: [SubAgent Model]
Connectors: [SubAgent Connectors]
Output Format: [SubAgent Output Format]
Label: [SubAgent Label]

"""

root_agent = Agent(
    model=MODEL_PATH,
    name="GE_Migration_Agent",
    description="Gemini Enterprise App Migration Agent that migrates notebooks between apps and lists custom agents.",
    instruction=AGENT_INSTRUCTION,
    tools=[list_notebooks, list_sources_and_types, create_notebook, add_source_to_notebook, migrate_notebook, list_employee_agents, get_agent_details, migrate_agent, export_agent_to_gcs, import_agent_from_gcs, export_notebook_to_gcs, import_notebook_from_gcs, lookup_and_map_connectors, list_datastores, get_migration_config, SkillToolset(skills=[migration_skill.migration_config_skill])],
)
