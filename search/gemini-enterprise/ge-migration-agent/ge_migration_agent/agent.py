import json
import os
import logging
import subprocess
import shutil
import sys
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(env_path)
from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext
from google.adk.tools.skill_toolset import SkillToolset
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from skills import migration_skill

PROJECT_NUMBER = os.environ.get("GEMINI_API_PROJECT")
LOCATION = "global"

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


def list_notebooks(tool_context: ToolContext, project_number: str = PROJECT_NUMBER, location: str = LOCATION) -> str:
    """Call this tool to get a list of recently viewed notebooks.
    
    Args:
        project_number: The Google Cloud project number. Defaults to source project.
        location: The geographic location. Defaults to global.
    """
    args = ["list-notebooks"]
    if project_number:
        args.extend(["--project", project_number])
    if location:
        args.extend(["--location", location])
    return run_cli(args)


def list_sources_and_types(tool_context: ToolContext, notebook_id: str, project_number: str = PROJECT_NUMBER, location: str = LOCATION) -> str:
    """Call this tool to list sources and their types for a specific notebook.

    Args:
        notebook_id: The ID of the notebook.
        project_number: The Google Cloud project number. Defaults to source project.
        location: The geographic location. Defaults to global.
    """
    args = ["list-sources", notebook_id]
    if project_number:
        args.extend(["--project", project_number])
    if location:
        args.extend(["--location", location])
    return run_cli(args)


def create_notebook(tool_context: ToolContext, target_project_number: str, target_location: str, title: str) -> str:
    """Call this tool to create a new notebook in a target project.

    Args:
        target_project_number: The Google Cloud project number of the target app.
        target_location: The geographic location of the data store (e.g., global).
        title: The title of the notebook to create.
    """
    args = ["create-notebook", title]
    if target_project_number:
        args.extend(["--target-project", target_project_number])
    if target_location:
        args.extend(["--target-location", target_location])
    return run_cli(args)


def add_source_to_notebook(tool_context: ToolContext, target_project_number: str, target_location: str, notebook_id: str, source_content: str) -> str:
    """Call this tool to add a source to a notebook in a target project.

    Args:
        target_project_number: The Google Cloud project number of the target app.
        target_location: The geographic location of the data store.
        notebook_id: The ID of the notebook to add the source to.
        source_content: The JSON string of the userContent to add.
    """
    args = ["add-source-to-notebook", notebook_id, source_content]
    if target_project_number:
        args.extend(["--target-project", target_project_number])
    if target_location:
        args.extend(["--target-location", target_location])
    return run_cli(args)


def list_employee_agents(tool_context: ToolContext, project_id: str = PROJECT_NUMBER, location: str = LOCATION, engine_id: str = "enterprise-search-17416389_1741638989378") -> str:
    """Call this tool to list all employee-made low-code agents in a given engine.
    
    Args:
        project_id: The Google Cloud project number. Defaults to source project.
        location: The geographic location. Defaults to global.
        engine_id: The Discovery Engine engine ID containing the agents.
    """
    args = ["list-agents", "--engine-id", engine_id]
    if project_id:
        args.extend(["--project", project_id])
    if location:
        args.extend(["--location", location])
    return run_cli(args)


def extract_agent_datastores(
    tool_context: ToolContext,
    source_agent_name: str,
    source_project_id: str = PROJECT_NUMBER,
    source_location: str = LOCATION,
    source_engine_id: str = "enterprise-search-17416389_1741638989378"
) -> str:
    """Call this tool to extract and list the names of datastores used by an agent and its subagents.
    
    Args:
        source_agent_name: The exact display name of the source agent (e.g., "Quarterly Business Review Generator").
        source_project_id: The Google Cloud project number of the source environment.
        source_location: The geographic location of the source environment.
        source_engine_id: The Discovery Engine engine ID of the source environment.
    """
    args = ["extract-datastores", source_agent_name, "--engine-id", source_engine_id]
    if source_project_id:
        args.extend(["--project", source_project_id])
    if source_location:
        args.extend(["--location", source_location])
    return run_cli(args)


def migrate_employee_agent(
    tool_context: ToolContext,
    source_agent_name: str,
    target_project_id: str,
    target_location: str,
    target_engine_id: str,
    source_project_id: str = PROJECT_NUMBER,
    source_location: str = LOCATION,
    source_engine_id: str = "enterprise-search-17416389_1741638989378",
    force: bool = False,
    connector_mapping: str = ""
) -> str:
    """Call this tool to migrate (create) an employee-made low-code agent to a target environment.
    
    Args:
        source_agent_name: The exact display name of the source agent to migrate (e.g., "Quarterly Business Review Generator").
        target_project_id: The Google Cloud project number of the target environment.
        target_location: The geographic location of the target environment.
        target_engine_id: The Discovery Engine engine ID of the target environment.
        source_project_id: The Google Cloud project number of the source environment.
        source_location: The geographic location of the source environment.
        source_engine_id: The Discovery Engine engine ID of the source environment.
        force: Set to True to proceed with migration even if some dependencies (connectors/datastores) are missing in the target environment.
        connector_mapping: Optional JSON dict or comma-separated k:v mapping string (e.g. 'Snowflake Mcp May29:snowflakeMcp') approved by the user.
    """
    args = [
        "migrate-agent", source_agent_name,
        "--target-project", target_project_id,
        "--target-location", target_location,
        "--target-engine", target_engine_id,
        "--source-engine", source_engine_id
    ]
    if source_project_id:
        args.extend(["--source-project", source_project_id])
    if source_location:
        args.extend(["--source-location", source_location])
    if force:
        args.append("--force")
    if connector_mapping:
        args.extend(["--connector-mapping", connector_mapping])
    return run_cli(args)


def lookup_and_map_connectors(
    tool_context: ToolContext,
    source_agent_name: str,
    target_project_id: str,
    target_engine_id: str,
    source_project_id: str = PROJECT_NUMBER,
    source_location: str = LOCATION,
    target_location: str = LOCATION
) -> str:
    """Call this tool before migrating an agent to look up source connectors, map them intelligently to target connectors (e.g. Snowflake Mcp May29 -> snowflakeMcp), and show the proposed mapping to the user for approval.
    
    Args:
        source_agent_name: The exact display name of the source agent.
        target_project_id: The target Google Cloud project number.
        target_engine_id: The target Discovery Engine engine ID.
        source_project_id: The source Google Cloud project number.
    """
    return run_cli([
        "lookup-map-connectors", source_agent_name,
        "--target-project", target_project_id,
        "--target-engine", target_engine_id,
        "--source-project", source_project_id
    ])


def create_agent_from_gem(
    tool_context: ToolContext,
    name: str,
    instructions: str,
    target_project_id: str,
    target_engine_id: str,
    description: str = "",
    target_location: str = LOCATION
) -> str:
    """Call this tool to create a new Gemini Enterprise agent from a Gem definition (name and instructions).
    
    Args:
        name: The name of the Gem (will be used as agent display name).
        instructions: The custom instructions or prompt for the Gem.
        target_project_id: The target Google Cloud project number.
        target_location: The target location. Defaults to global.
        target_engine_id: The target Discovery Engine engine ID.
    """
    args = [
        "create-agent-from-gem", name, instructions,
        "--target-project", target_project_id,
        "--target-engine", target_engine_id
    ]
    if target_location:
        args.extend(["--target-location", target_location])
    if description:
        args.extend(["--description", description])
    return run_cli(args)


def import_gems_from_file(
    tool_context: ToolContext,
    file_path: str,
    target_project_id: str,
    target_engine_id: str,
    target_location: str = "global"
) -> str:
    """Call this tool to import multiple Gems from a local HTML file dump.
    
    Args:
        file_path: The path (supports relative paths like './sample_data/gemini_gems_data.html' or 'sample_data/gemini_gems_data.html' and absolute paths) to the HTML file containing Gems data.
        target_project_id: The target Google Cloud project number.
        target_engine_id: The target Discovery Engine engine ID.
        target_location: The target location. Defaults to global.
    """
    args = [
        "import-gems", file_path,
        "--target-project", target_project_id,
        "--target-engine", target_engine_id
    ]
    if target_location:
        args.extend(["--target-location", target_location])
    return run_cli(args)


def export_agent_to_gcs(
    tool_context: ToolContext,
    source_agent_name: str,
    object_name: str,
    bucket_name: str = "",
    source_project_id: str = PROJECT_NUMBER,
    source_location: str = LOCATION,
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

Workflow:
1. List all notebook apps from the source app (using `list_notebooks`).
2. Ask the user which notebook they want to migrate, or if they want to migrate all of them.
3. Ask the user for the target Gemini Enterprise app details (Project Number and Location).
4. For each notebook to migrate:
   a. Get its sources and types using `list_sources_and_types`.
   b. Create a new notebook in the target app using `create_notebook` with the EXACT SAME title as the source notebook (do NOT append " (migrated)", " (Migrated)", or any suffix to the title!).
   c. For each source, map it to the correct format and add it to the new notebook using `add_source_to_notebook`.
5. List employee-made agents when requested using `list_employee_agents`.
6. Migrate (create) employee-made low-code agents to a target Gemini Enterprise environment using `migrate_employee_agent`. This will also implicitly save a backup to a GCS bucket.
7. Export employee-made low-code agents to a GCS bucket using `export_agent_to_gcs` when requested.
8. Import employee-made low-code agents from a GCS bucket to a target environment using `import_agent_from_gcs` when requested.
9. Import multiple Gems from a local file dump using `import_gems_from_file`. Accept relative paths like `./sample_data/gemini_gems_data.html` or `sample_data/gemini_gems_data.html` directly without requiring absolute paths. ALWAYS ask the user for the target project ID and engine ID before calling this tool!
10. When importing Gems with attached files using `import_gems_from_file`, first connect to the target location using `list_datastores` to get a list of all datastores and datastore IDs. Check with the user which datastore ID needs to be used for the attached knowledge before performing the import!
11. Before migrating an employee-made low-code agent using `migrate_employee_agent`, FIRST call `lookup_and_map_connectors` to look up available connectors in the target environment and intelligently map source connectors (e.g., Snowflake Mcp May29 -> snowflakeMcp). Present the proposed mapping table to the user and GET THEIR APPROVAL on the mapping before calling `migrate_employee_agent` with the approved `connector_mapping`!


Mapping sources:
- Type "google docs": use "googleDriveContent" with documentId extracted from location URL and mimeType "application/vnd.google-apps.document". Do NOT include "sourceName" at the root of the object.
- Type "website": use "webContent" with url. Do NOT include "sourceName" at the root unless confirmed valid.
- Type "copied text": use "textContent" with content.
- Type "youtube": use "videoContent" with youtubeUrl.

Critical Rule: Do NOT delete the source notebook or its sources after migration. This is a read-and-copy operation only.

Output Format:
When presenting lists of notebooks, sources, or employee-made agents, you MUST format them as complete, pristine Markdown tables:
1. Always include a proper Markdown header and separator row (e.g. `| Display Name | Description |\n|---|---|`).
2. Separate each row cleanly with a line break (`\n`).
3. Replace any internal newlines within descriptions with spaces or `<br>` so table formatting does not break.
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
    model=f"projects/{os.environ.get('GEMINI_API_PROJECT')}/locations/{os.environ.get('GEMINI_API_LOCATION')}/publishers/google/models/gemini-2.5-flash",
    name="GE_Migration_Agent",
    description="Gemini Enterprise App Migration Agent that migrates notebooks between apps and lists custom agents.",
    instruction=AGENT_INSTRUCTION,
    tools=[list_notebooks, list_sources_and_types, create_notebook, add_source_to_notebook, list_employee_agents, migrate_employee_agent, export_agent_to_gcs, import_agent_from_gcs, create_agent_from_gem, import_gems_from_file, lookup_and_map_connectors, list_datastores, get_migration_config, SkillToolset(skills=[migration_skill.migration_config_skill])],
)
