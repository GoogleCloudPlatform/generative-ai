#!/usr/bin/env python3
"""
🚀 Gemini Enterprise Migration CLI

This script exposes all capabilities of the Gemini Enterprise Migration tool
directly via a deterministic, rapid Command-Line Interface.
"""
import os
import sys
import json
import argparse
import logging

# Ensure package directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import core

# ANSI color codes
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_BLUE = "\033[94m"
COLOR_BOLD = "\033[1m"
COLOR_RESET = "\033[0m"

def print_color(text, color):
    """Prints text in the specified ANSI color to stdout, or to stderr if outputting JSON."""
    file = sys.stderr if "--json" in sys.argv else sys.stdout
    if file.isatty():
        print(f"{color}{text}{COLOR_RESET}", file=file)
    else:
        print(text, file=file)

def format_table(headers, rows):
    """Formats and prints rows in a text-based grid table."""
    if not rows:
        print("No results found.")
        return
        
    # Calculate column widths
    col_widths = [len(h) for headers_list in [headers] for h in headers_list]
    for row in rows:
        for i, val in enumerate(row):
            str_val = str(val or "")
            if len(str_val) > col_widths[i]:
                col_widths[i] = len(str_val)
                
    # Build separator
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    
    # Print headers
    print_color(separator, COLOR_BOLD)
    header_row = "|" + "|".join(f" {h:<{col_widths[i]}} " for i, h in enumerate(headers)) + "|"
    print_color(header_row, COLOR_BOLD)
    print_color(separator, COLOR_BOLD)
    
    # Print rows
    for row in rows:
        row_str = "|" + "|".join(f" {str(row[i] or ''):<{col_widths[i]}} " for i in range(len(headers))) + "|"
        print(row_str)
        
    print_color(separator, COLOR_BOLD)

def get_env_default(var_names, default=None):
    """Returns the first non-empty environment variable value or default."""
    for name in var_names:
        val = os.environ.get(name)
        if val:
            return val
    return default

try:
    from skills import MigrationConfigSkill
    SKILL_CFG = MigrationConfigSkill()
except Exception:
    SKILL_CFG = None

def get_skill_env(env_type: str, key: str, default=None):
    if SKILL_CFG:
        cfg = SKILL_CFG.get_source_env() if env_type == "source" else SKILL_CFG.get_target_env()
        return cfg.get(key, default)
    return default

def handle_list_notebooks(args):
    project = args.project or get_env_default(["GEMINI_API_PROJECT", "GOOGLE_CLOUD_PROJECT"])
    location = args.location or "global"
    
    if not project:
        print_color("Error: Google Cloud project number must be provided via --project or environment variables.", COLOR_RED)
        sys.exit(1)
        
    print_color(f"Listing recently viewed notebooks in project {project} ({location})...", COLOR_BLUE)
    try:
        notebooks = core.list_notebooks(project, location)
        if args.json:
            print(json.dumps(notebooks, indent=2))
        else:
            headers = ["ID", "Title", "Create Time", "Update Time"]
            rows = []
            for nb in notebooks:
                nb_id = nb.get("name", "").split("/")[-1]
                rows.append([
                    nb_id,
                    nb.get("title", ""),
                    nb.get("createTime", "N/A"),
                    nb.get("updateTime", "N/A")
                ])
            format_table(headers, rows)
    except Exception as e:
        print_color(f"Error: {e}", COLOR_RED)
        sys.exit(1)

def handle_list_sources(args):
    project = args.project or get_env_default(["GEMINI_API_PROJECT", "GOOGLE_CLOUD_PROJECT"])
    location = args.location or "global"
    
    if not project:
        print_color("Error: Google Cloud project number must be provided via --project or environment variables.", COLOR_RED)
        sys.exit(1)
        
    print_color(f"Listing sources for notebook '{args.notebook_id}' in project {project}...", COLOR_BLUE)
    try:
        sources = core.list_sources_and_types(args.notebook_id, project, location)
        if args.json:
            # Strip raw_data from print to keep it clean, unless requested explicitly
            for s in sources:
                if not args.include_raw and "raw_data" in s:
                    s.pop("raw_data")
            print(json.dumps(sources, indent=2))
        else:
            headers = ["Title", "ID", "Type", "Location"]
            rows = []
            for src in sources:
                rows.append([
                    src.get("title", ""),
                    src.get("id", ""),
                    src.get("type", ""),
                    src.get("location", "")
                ])
            format_table(headers, rows)
    except Exception as e:
        print_color(f"Error: {e}", COLOR_RED)
        sys.exit(1)

def handle_migrate_notebook(args):
    source_project = args.source_project or get_env_default(["GEMINI_API_PROJECT", "GOOGLE_CLOUD_PROJECT"])
    target_project = args.target_project or get_env_default(["GOOGLE_CLOUD_PROJECT", "GEMINI_API_PROJECT"])
    source_location = args.source_location or "global"
    target_location = args.target_location or "global"
    
    if not source_project:
        print_color("Error: Source project must be specified via --source-project or environment.", COLOR_RED)
        sys.exit(1)
    if not target_project:
        print_color("Error: Target project must be specified via --target-project or environment.", COLOR_RED)
        sys.exit(1)
        
    print_color(f"Migrating notebook '{args.notebook}' from {source_project} ({source_location}) to {target_project} ({target_location})...", COLOR_BLUE)
    try:
        res = core.migrate_notebook_pipeline(
            args.notebook,
            target_project,
            target_location,
            source_project,
            source_location
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            if res.get("success"):
                print_color(f"\n🎉 Successfully migrated notebook '{res['source_notebook_title']}'!", COLOR_GREEN)
                print(f"Target Notebook ID: {res['target_notebook_id']}")
                print(f"Migrated Sources: {res['migrated_sources_count']}")
            else:
                print_color("\n⚠️ Notebook migrated with partial success.", COLOR_YELLOW)
                print(f"Target Notebook ID: {res['target_notebook_id']}")
                print(f"Migrated Sources: {res['migrated_sources_count']}")
                print_color(f"Failed Sources: {res['failed_sources_count']}", COLOR_RED)
                for f in res.get("failed", []):
                    print_color(f" - {f['title']}: {f['error']}", COLOR_RED)
    except Exception as e:
        print_color(f"Error during migration: {e}", COLOR_RED)
        sys.exit(1)

def handle_list_agents(args):
    project = args.project or get_env_default(["GEMINI_API_PROJECT", "GOOGLE_CLOUD_PROJECT"])
    location = args.location or "global"
    
    if not project:
        print_color("Error: Google Cloud project number must be specified.", COLOR_RED)
        sys.exit(1)
        
    print_color(f"Listing employee-made agents in project {project} (Engine: {args.engine_id})...", COLOR_BLUE)
    try:
        agents = core.list_employee_agents(project, location, args.engine_id)
        if args.json:
            for a in agents:
                if "raw_agent" in a:
                    a.pop("raw_agent")
            print(json.dumps(agents, indent=2))
        else:
            headers = ["Display Name", "Description", "Primary Tools"]
            rows = []
            for agent in agents:
                tools_str = ", ".join(agent.get("connectors_and_tools", []))
                if len(tools_str) > 40:
                    tools_str = tools_str[:37] + "..."
                rows.append([
                    agent.get("displayName", ""),
                    agent.get("description", "No description"),
                    tools_str
                ])
            format_table(headers, rows)
    except Exception as e:
        print_color(f"Error: {e}", COLOR_RED)
        sys.exit(1)

def handle_extract_datastores(args):
    project = args.project or get_env_default(["GEMINI_API_PROJECT", "GOOGLE_CLOUD_PROJECT"])
    location = args.location or "global"
    
    if not project:
        print_color("Error: Source project must be specified.", COLOR_RED)
        sys.exit(1)
        
    print_color(f"Extracting datastores for agent '{args.agent_name}'...", COLOR_BLUE)
    try:
        report = core.extract_agent_datastores(
            args.agent_name,
            project,
            location,
            args.engine_id
        )
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print_color(f"\nDatastore dependencies for agent: {report['agent_name']}", COLOR_BOLD)
            datastores = report.get("datastores", {})
            if not datastores:
                print("No datastores found.")
            for node, ds_list in datastores.items():
                print(f"Node '{node}':")
                for ds in ds_list:
                    print(f"  - {ds}")
    except Exception as e:
        print_color(f"Error: {e}", COLOR_RED)
        sys.exit(1)

def handle_migrate_agent(args):
    source_project = args.source_project or get_skill_env("source", "project_number") or get_env_default(["GEMINI_API_PROJECT", "GOOGLE_CLOUD_PROJECT"])
    target_project = args.target_project or get_skill_env("target", "project_number") or get_env_default(["GOOGLE_CLOUD_PROJECT", "GEMINI_API_PROJECT"])
    source_location = args.source_location or get_skill_env("source", "region", "global")
    target_location = args.target_location or get_skill_env("target", "region", "global")
    source_engine = args.source_engine or get_skill_env("source", "engine_id")
    target_engine = args.target_engine or get_skill_env("target", "engine_id")
    bucket = args.backup_bucket or get_env_default(["GCS_BUCKET_NAME"])
    
    mapping_str = args.connector_mapping
    if not mapping_str and SKILL_CFG:
        mapping = SKILL_CFG.get_connectors_mapping()
        mapping.update(SKILL_CFG.get_datastores_mapping())
        if mapping:
            mapping_str = json.dumps(mapping)
            
    if not source_project or not target_project:
        print_color("Error: Source and Target projects must be specified.", COLOR_RED)
        sys.exit(1)
        
    print_color(f"Migrating employee agent '{args.agent_name}' from project {source_project} to target project {target_project}...", COLOR_BLUE)
    try:
        res = core.migrate_employee_agent(
            args.agent_name,
            target_project,
            target_location,
            target_engine,
            source_project,
            source_location,
            source_engine,
            args.force,
            bucket,
            mapping_str
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            if res.get("success"):
                print_color(f"\n🎉 Successfully migrated agent '{args.agent_name}'!", COLOR_GREEN)
                print(res.get("message"))
            else:
                # Handle pre-flight validation failure
                if "warning" in res:
                    print_color(f"\n⚠️ Pre-flight Validation Failed: {res['warning']}", COLOR_YELLOW)
                    print(res.get("message"))
                    report = res.get("report", {})
                    print(f"Missing Connectors/Datastores: {report.get('missing_connectors', [])}")
                    print("\nTo bypass this check and proceed anyway, run the command again with --force.")
                else:
                    print_color(f"Migration failed: {res.get('message')}", COLOR_RED)
    except Exception as e:
        print_color(f"Error: {e}", COLOR_RED)
        sys.exit(1)

def handle_lookup_and_map_connectors(args):
    source_project = args.source_project or get_skill_env("source", "project_number") or get_env_default(["GEMINI_API_PROJECT", "GOOGLE_CLOUD_PROJECT"])
    target_project = args.target_project or get_skill_env("target", "project_number") or get_env_default(["GOOGLE_CLOUD_PROJECT", "GEMINI_API_PROJECT"])
    source_location = args.source_location or get_skill_env("source", "region", "global")
    target_location = args.target_location or get_skill_env("target", "region", "global")
    source_engine = args.source_engine or get_skill_env("source", "engine_id")
    target_engine = args.target_engine or get_skill_env("target", "engine_id")
    
    try:
        res = core.lookup_and_map_connectors(
            args.agent_name,
            target_project,
            target_location,
            target_engine,
            source_project,
            source_location,
            source_engine
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            headers = ["Source Connector / DataStore", "Target Mapping", "Status"]
            mapping = res.get("proposed_mapping", {})
            missing = res.get("missing_connectors", [])
            rows = []
            for k, v in mapping.items():
                status = "❌ Missing" if k in missing else "✅ Mapped"
                rows.append([k, v, status])
            format_table(headers, rows)
            if missing:
                print_color(f"\n⚠️ Missing Connectors/DataStores in Target: {missing}", COLOR_YELLOW)
    except Exception as e:
        print_color(f"Error: {e}", COLOR_RED)
        sys.exit(1)

def handle_import_gems(args):
    target_project = args.target_project or get_env_default(["GOOGLE_CLOUD_PROJECT", "GEMINI_API_PROJECT"])
    target_location = args.target_location or "global"
    
    if not target_project:
        print_color("Error: Target project must be specified.", COLOR_RED)
        sys.exit(1)
        
    print_color(f"Importing Gems from HTML file: {args.file} to target project {target_project}...", COLOR_BLUE)
    try:
        res = core.import_gems_from_file(
            args.file,
            target_project,
            args.target_engine,
            target_location
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print_color(f"\n🎉 {res.get('message')}", COLOR_GREEN)
            print("\nProcessing Details:")
            for item in res.get("details", []):
                if item.startswith("Success"):
                    print_color(f" - {item}", COLOR_GREEN)
                else:
                    print_color(f" - {item}", COLOR_RED)
    except Exception as e:
        print_color(f"Error importing Gems: {e}", COLOR_RED)
        sys.exit(1)

def handle_list_datastores(args):
    project = args.project or get_env_default(["GEMINI_API_PROJECT", "GOOGLE_CLOUD_PROJECT"])
    location = args.location or "global"
    
    if not project:
        print_color("Error: Google Cloud project number must be specified.", COLOR_RED)
        sys.exit(1)
        
    print_color(f"Listing DataStores in project {project} ({location})...", COLOR_BLUE)
    try:
        datastores = core.list_datastores(project, location)
        if args.json:
            print(json.dumps(datastores, indent=2))
        else:
            headers = ["DataStore ID", "Display Name", "Full Resource Name"]
            rows = [[ds["id"], ds["displayName"], ds["name"]] for ds in datastores]
            format_table(headers, rows)
    except Exception as e:
        print_color(f"Error: {e}", COLOR_RED)
        sys.exit(1)

def handle_export_agent_gcs(args):
    project = args.project or get_env_default(["GEMINI_API_PROJECT", "GOOGLE_CLOUD_PROJECT"])
    location = args.location or "global"
    bucket = args.bucket or get_env_default(["GCS_BUCKET_NAME"])
    
    if not project:
        print_color("Error: Source project must be specified.", COLOR_RED)
        sys.exit(1)
    if not bucket:
        print_color("Error: GCS bucket name must be specified via --bucket or environment.", COLOR_RED)
        sys.exit(1)
        
    print_color(f"Exporting agent '{args.agent_name}' definition to gs://{bucket}/{args.object_name}...", COLOR_BLUE)
    try:
        res = core.export_agent_to_gcs(
            args.agent_name,
            args.object_name,
            bucket,
            project,
            location,
            args.engine_id
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print_color(f"\n🎉 {res.get('message')}", COLOR_GREEN)
    except Exception as e:
        print_color(f"Error during export: {e}", COLOR_RED)
        sys.exit(1)

def handle_import_agent_gcs(args):
    project = args.target_project or get_env_default(["GOOGLE_CLOUD_PROJECT", "GEMINI_API_PROJECT"])
    location = args.target_location or "global"
    bucket = args.bucket or get_env_default(["GCS_BUCKET_NAME"])
    
    mapping_str = ""
    if SKILL_CFG:
        mapping = SKILL_CFG.get_connectors_mapping()
        mapping.update(SKILL_CFG.get_datastores_mapping())
        if mapping:
            mapping_str = json.dumps(mapping)
            
    if not project:
        print_color("Error: Target project must be specified.", COLOR_RED)
        sys.exit(1)
    if not bucket:
        print_color("Error: GCS bucket name must be specified via --bucket or environment.", COLOR_RED)
        sys.exit(1)
        
    print_color(f"Importing agent definition from gs://{bucket}/{args.object_name} to project {project}...", COLOR_BLUE)
    try:
        res = core.import_agent_from_gcs(
            args.object_name,
            project,
            location,
            args.target_engine,
            bucket,
            mapping_str
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print_color(f"\n🎉 {res.get('message')}", COLOR_GREEN)
    except Exception as e:
        print_color(f"Error during import: {e}", COLOR_RED)
        sys.exit(1)

def handle_create_notebook(args):
    target_project = args.target_project or get_env_default(["GOOGLE_CLOUD_PROJECT", "GEMINI_API_PROJECT"])
    target_location = args.target_location or "global"
    
    if not target_project:
        print_color("Error: Target project must be specified.", COLOR_RED)
        sys.exit(1)
        
    print_color(f"Creating notebook '{args.title}' in project {target_project}...", COLOR_BLUE)
    try:
        res = core.create_notebook(target_project, target_location, args.title)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print_color(f"🎉 Successfully created notebook '{args.title}'!", COLOR_GREEN)
            print(f"ID: {res.get('name', '').split('/')[-1]}")
    except Exception as e:
        print_color(f"Error: {e}", COLOR_RED)
        sys.exit(1)

def handle_add_source_to_notebook(args):
    target_project = args.target_project or get_env_default(["GOOGLE_CLOUD_PROJECT", "GEMINI_API_PROJECT"])
    target_location = args.target_location or "global"
    
    if not target_project:
        print_color("Error: Target project must be specified.", COLOR_RED)
        sys.exit(1)
        
    print_color(f"Adding source to notebook '{args.notebook_id}' in project {target_project}...", COLOR_BLUE)
    try:
        content_obj = json.loads(args.source_content)
        res = core.add_source_to_notebook(target_project, target_location, args.notebook_id, content_obj)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print_color(f"🎉 Successfully added source to notebook '{args.notebook_id}'!", COLOR_GREEN)
    except Exception as e:
        print_color(f"Error: {e}", COLOR_RED)
        sys.exit(1)

def handle_create_agent_from_gem(args):
    target_project = args.target_project or get_env_default(["GOOGLE_CLOUD_PROJECT", "GEMINI_API_PROJECT"])
    target_location = args.target_location or "global"
    
    if not target_project:
        print_color("Error: Target project must be specified.", COLOR_RED)
        sys.exit(1)
        
    print_color(f"Creating agent '{args.name}' from Gem...", COLOR_BLUE)
    try:
        res = core.create_agent_from_gem(
            args.name,
            args.instructions,
            target_project,
            args.target_engine,
            args.description or "",
            target_location
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            print_color(f"🎉 {res.get('message')}", COLOR_GREEN)
    except Exception as e:
        print_color(f"Error: {e}", COLOR_RED)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="🚀 Gemini Enterprise Migration CLI - Migrate low-code agents, Gems, and notebooks deterministically."
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON results instead of user-friendly text tables")
    
    subparsers = parser.add_subparsers(dest="command", help="Migration command to execute")
    
    # List notebooks
    p_list_nb = subparsers.add_parser("list-notebooks", help="List recently viewed notebooks in source project")
    p_list_nb.add_argument("--project", help="Google Cloud project number (defaults to GEMINI_API_PROJECT env)")
    p_list_nb.add_argument("--location", help="Geographic location (defaults to GEMINI_API_LOCATION env or 'global')")
    p_list_nb.set_defaults(func=handle_list_notebooks)
    
    # List sources
    p_list_src = subparsers.add_parser("list-sources", help="List sources and their types in a specific notebook")
    p_list_src.add_argument("notebook_id", help="The source notebook ID")
    p_list_src.add_argument("--project", help="Google Cloud project number (defaults to GEMINI_API_PROJECT env)")
    p_list_src.add_argument("--location", help="Geographic location (defaults to GEMINI_API_LOCATION env or 'global')")
    p_list_src.add_argument("--include-raw", action="store_true", help="Include raw source metadata in JSON output")
    p_list_src.set_defaults(func=handle_list_sources)
    
    # Migrate notebook
    p_mig_nb = subparsers.add_parser("migrate-notebook", help="Migrate a notebook and all its sources in a fast python loop")
    p_mig_nb.add_argument("notebook", help="The source notebook ID or title to migrate")
    p_mig_nb.add_argument("--source-project", help="Source project number (defaults to GEMINI_API_PROJECT env)")
    p_mig_nb.add_argument("--target-project", help="Target project number (defaults to GOOGLE_CLOUD_PROJECT env)")
    p_mig_nb.add_argument("--source-location", help="Source geographic location (defaults to 'global')")
    p_mig_nb.add_argument("--target-location", help="Target geographic location (defaults to 'global')")
    p_mig_nb.set_defaults(func=handle_migrate_notebook)
    
    # List agents
    p_list_ag = subparsers.add_parser("list-agents", help="List all employee-made low-code agents")
    p_list_ag.add_argument("--project", help="Source project number (defaults to GEMINI_API_PROJECT env)")
    p_list_ag.add_argument("--engine-id", required=True, help="Discovery Engine engine ID containing the agents")
    p_list_ag.add_argument("--location", help="Geographic location (defaults to 'global')")
    p_list_ag.set_defaults(func=handle_list_agents)
    
    # Extract datastores
    p_ext_ds = subparsers.add_parser("extract-datastores", help="Extract datastores used by an agent and its subagents")
    p_ext_ds.add_argument("agent_name", help="Exact display name of source low-code agent")
    p_ext_ds.add_argument("--project", help="Source project number (defaults to GEMINI_API_PROJECT env)")
    p_ext_ds.add_argument("--engine-id", required=True, help="Discovery Engine engine ID containing the agent")
    p_ext_ds.add_argument("--location", help="Geographic location (defaults to 'global')")
    p_ext_ds.set_defaults(func=handle_extract_datastores)
    
    # Migrate agent
    p_mig_ag = subparsers.add_parser("migrate-agent", help="Migrate a low-code agent from source to target")
    p_mig_ag.add_argument("agent_name", help="Exact display name of source low-code agent to migrate")
    p_mig_ag.add_argument("--source-project", help="Source project number (defaults to GEMINI_API_PROJECT env)")
    p_mig_ag.add_argument("--target-project", help="Target project number (defaults to GOOGLE_CLOUD_PROJECT env)")
    p_mig_ag.add_argument("--source-engine", help="Source Discovery Engine engine ID")
    p_mig_ag.add_argument("--target-engine", help="Target Discovery Engine engine ID")
    p_mig_ag.add_argument("--source-location", help="Source geographic location (defaults to 'global')")
    p_mig_ag.add_argument("--target-location", help="Target geographic location (defaults to 'global')")
    p_mig_ag.add_argument("--force", action="store_true", help="Bypass connector pre-flight validation check")
    p_mig_ag.add_argument("--backup-bucket", help="GCS bucket name for implicit backup (defaults to GCS_BUCKET_NAME env)")
    p_mig_ag.add_argument("--connector-mapping", help="Optional JSON dict or comma-separated k:v mapping string", default="")
    p_mig_ag.set_defaults(func=handle_migrate_agent)
    
    # Lookup and Map Connectors
    p_lookup_map = subparsers.add_parser("lookup-map-connectors", help="Lookup and intelligently map source connectors to target connectors")
    p_lookup_map.add_argument("agent_name", help="Exact display name of source agent")
    p_lookup_map.add_argument("--source-project", help="Source project number")
    p_lookup_map.add_argument("--target-project", help="Target project number")
    p_lookup_map.add_argument("--source-engine", help="Source engine ID")
    p_lookup_map.add_argument("--target-engine", help="Target engine ID")
    p_lookup_map.add_argument("--source-location", help="Source location", default="global")
    p_lookup_map.add_argument("--target-location", help="Target location", default="global")
    p_lookup_map.set_defaults(func=handle_lookup_and_map_connectors)
    
    # Import Gems
    p_imp_gems = subparsers.add_parser("import-gems", help="Batch import custom instructions (Gems) from an HTML dump file")
    p_imp_gems.add_argument("file", help="Path to the local HTML file containing Gems takeout data")
    p_imp_gems.add_argument("--target-project", help="Target project number (defaults to GOOGLE_CLOUD_PROJECT env)")
    p_imp_gems.add_argument("--target-engine", required=True, help="Target Discovery Engine engine ID")
    p_imp_gems.add_argument("--target-location", help="Target geographic location (defaults to 'global')")
    p_imp_gems.set_defaults(func=handle_import_gems)
    # List DataStores
    p_list_ds = subparsers.add_parser("list-datastores", help="List available DataStores in a project")
    p_list_ds.add_argument("--project", help="Google Cloud project number")
    p_list_ds.add_argument("--location", help="Location (defaults to 'global')", default="global")
    p_list_ds.set_defaults(func=handle_list_datastores)
    # Export Agent GCS
    p_exp_gcs = subparsers.add_parser("export-agent-gcs", help="Export an employee-made low-code agent to GCS")
    p_exp_gcs.add_argument("agent_name", help="Exact display name of source low-code agent")
    p_exp_gcs.add_argument("object_name", help="GCS object name (e.g. exports/my_agent.json)")
    p_exp_gcs.add_argument("--bucket", help="GCS bucket name (defaults to GCS_BUCKET_NAME env)")
    p_exp_gcs.add_argument("--project", help="Source project number (defaults to GEMINI_API_PROJECT env)")
    p_exp_gcs.add_argument("--engine-id", required=True, help="Source Discovery Engine engine ID")
    p_exp_gcs.add_argument("--location", help="Source geographic location (defaults to 'global')")
    p_exp_gcs.set_defaults(func=handle_export_agent_gcs)
    
    # Import Agent GCS
    p_imp_gcs = subparsers.add_parser("import-agent-gcs", help="Import an employee-made low-code agent definition from GCS")
    p_imp_gcs.add_argument("object_name", help="GCS object name of stored definition JSON")
    p_imp_gcs.add_argument("--bucket", help="GCS bucket name (defaults to GCS_BUCKET_NAME env)")
    p_imp_gcs.add_argument("--target-project", help="Target project number (defaults to GOOGLE_CLOUD_PROJECT env)")
    p_imp_gcs.add_argument("--target-engine", required=True, help="Target Discovery Engine engine ID")
    p_imp_gcs.add_argument("--target-location", help="Target geographic location (defaults to 'global')")
    p_imp_gcs.set_defaults(func=handle_import_agent_gcs)
    
    # Create notebook
    p_create_nb = subparsers.add_parser("create-notebook", help="Create a new empty notebook in the target project")
    p_create_nb.add_argument("title", help="The title of the notebook to create")
    p_create_nb.add_argument("--target-project", help="Target project number (defaults to GOOGLE_CLOUD_PROJECT env)")
    p_create_nb.add_argument("--target-location", help="Target geographic location (defaults to 'global')")
    p_create_nb.set_defaults(func=handle_create_notebook)
    
    # Add source to notebook
    p_add_src = subparsers.add_parser("add-source-to-notebook", help="Add a single source to a notebook in the target project")
    p_add_src.add_argument("notebook_id", help="The ID of the notebook to add the source to")
    p_add_src.add_argument("source_content", help="The JSON string of the userContent to add")
    p_add_src.add_argument("--target-project", help="Target project number (defaults to GOOGLE_CLOUD_PROJECT env)")
    p_add_src.add_argument("--target-location", help="Target geographic location (defaults to 'global')")
    p_add_src.set_defaults(func=handle_add_source_to_notebook)

    # Create agent from gem
    p_create_gem = subparsers.add_parser("create-agent-from-gem", help="Create a new Gemini Enterprise agent from Gem definition")
    p_create_gem.add_argument("name", help="The name of the Gem (used as agent display name)")
    p_create_gem.add_argument("instructions", help="The custom instructions or prompt for the Gem")
    p_create_gem.add_argument("--target-project", help="Target project number (defaults to GOOGLE_CLOUD_PROJECT env)")
    p_create_gem.add_argument("--target-engine", required=True, help="Target Discovery Engine engine ID")
    p_create_gem.add_argument("--target-location", help="Target geographic location (defaults to 'global')")
    p_create_gem.add_argument("--description", help="Description of the agent")
    p_create_gem.set_defaults(func=handle_create_agent_from_gem)
    
    args = parser.parse_args()
    
    # Set up basic logging format
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(levelname)s - %(message)s")
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
        
    args.func(args)

if __name__ == "__main__":
    main()
