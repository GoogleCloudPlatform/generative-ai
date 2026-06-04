import json
import os
import logging
import time
from google.adk.agents.llm_agent import Agent
from google.adk.tools.tool_context import ToolContext
import google.auth
from google.auth.transport.requests import AuthorizedSession

PROJECT_NUMBER = os.environ.get("GEMINI_API_PROJECT")
LOCATION = "global"
ENDPOINT_LOCATION = "global"

def get_session():
    credentials, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return AuthorizedSession(credentials)

def list_notebooks(tool_context: ToolContext, project_number: str = PROJECT_NUMBER, location: str = LOCATION) -> str:
    """Call this tool to get a list of recently viewed notebooks.
    
    Args:
        project_number: The Google Cloud project number. Defaults to source project.
        location: The geographic location. Defaults to global.
    """
    session = get_session()
    url = f"https://{ENDPOINT_LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/{project_number}/locations/{location}/notebooks:listRecentlyViewed"

    try:
        resp = session.get(url)
        resp.raise_for_status()
        data = resp.json()
        notebooks = data.get("notebooks", [])
        return json.dumps(notebooks)
    except Exception as e:
        return json.dumps({"error": str(e)})

def list_sources_and_types(tool_context: ToolContext, notebook_id: str, project_number: str = PROJECT_NUMBER, location: str = LOCATION) -> str:
    """Call this tool to list sources and their types for a specific notebook.

    Args:
        notebook_id: The ID of the notebook.
        project_number: The Google Cloud project number. Defaults to source project.
        location: The geographic location. Defaults to global.
    """
    session = get_session()
    base_url = f"https://{ENDPOINT_LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/{project_number}/locations/{location}/notebooks/{notebook_id}"

    try:
        get_resp = session.get(base_url)
        get_resp.raise_for_status()
        nb_data = get_resp.json()
        sources = nb_data.get("sources", [])

        results = []
        for src in sources:
            src_id = src.get("sourceId", {}).get("id")
            src_title = src.get("title")

            src_url = f"{base_url}/sources/{src_id}"
            src_resp = session.get(src_url)
            src_resp.raise_for_status()
            src_data = src_resp.json()

            metadata = src_data.get("metadata", {})

            source_type = "copied text"
            source_location = "N/A"

            if "webpageMetadata" in metadata:
                source_type = "website"
                source_location = metadata["webpageMetadata"].get("webpageUrl")
            elif "googleDocsMetadata" in metadata:
                source_type = "google docs"
                doc_id = metadata["googleDocsMetadata"].get("documentId")
                source_location = f"https://docs.google.com/document/d/{doc_id}/edit"

            results.append({
                "title": src_title,
                "id": src_id,
                "type": source_type,
                "location": source_location
            })

        return json.dumps(results)
    except Exception as e:
        return json.dumps({"error": str(e)})

def create_notebook(tool_context: ToolContext, target_project_number: str, target_location: str, title: str) -> str:
    """Call this tool to create a new notebook in a target project.

    Args:
        target_project_number: The Google Cloud project number of the target app.
        target_location: The geographic location of the data store (e.g., global).
        title: The title of the notebook to create.
    """
    logging.info(f"DEBUG: create_notebook called with title='{title}', project='{target_project_number}', location='{target_location}'")
    session = get_session()
    endpoint_location = "global"
    url = f"https://{endpoint_location}-discoveryengine.googleapis.com/v1alpha/projects/{target_project_number}/locations/{target_location}/notebooks"

    try:
        resp = session.post(url, json={"title": title})
        resp.raise_for_status()
        data = resp.json()
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": str(e)})

def add_source_to_notebook(tool_context: ToolContext, target_project_number: str, target_location: str, notebook_id: str, source_content: str) -> str:
    """Call this tool to add a source to a notebook in a target project.

    Args:
        target_project_number: The Google Cloud project number of the target app.
        target_location: The geographic location of the data store.
        notebook_id: The ID of the notebook to add the source to.
        source_content: The JSON string of the userContent to add.
    """
    logging.info(f"DEBUG: add_source_to_notebook called with notebook_id='{notebook_id}', project='{target_project_number}'")
    session = get_session()
    endpoint_location = "global"
    url = f"https://{endpoint_location}-discoveryengine.googleapis.com/v1alpha/projects/{target_project_number}/locations/{target_location}/notebooks/{notebook_id}/sources:batchCreate"

    try:
        content_obj = json.loads(source_content)
        if "sourceName" in content_obj:
            logging.info(f"DEBUG: Removing invalid 'sourceName' from payload: {content_obj['sourceName']}")
            content_obj.pop("sourceName")
        logging.info(f"DEBUG: Sending request to {url} with payload: {json.dumps(content_obj)}")
        resp = session.post(url, json={"userContents": [content_obj]}, timeout=60)
        logging.info(f"DEBUG: Response status: {resp.status_code}")
        logging.info(f"DEBUG: Response body: {resp.text}")
        resp.raise_for_status()
        data = resp.json()
        return json.dumps(data)
    except Exception as e:
        return json.dumps({"error": str(e)})

def list_employee_agents(tool_context: ToolContext, project_id: str = PROJECT_NUMBER, location: str = LOCATION, engine_id: str = "enterprise-search-17416389_1741638989378") -> str:
    """Call this tool to list all employee-made low-code agents in a given engine.
    
    Args:
        project_id: The Google Cloud project number. Defaults to source project.
        location: The geographic location. Defaults to global.
        engine_id: The Discovery Engine engine ID containing the agents.
    """
    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    parent = f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/assistants/default_assistant"
    url = f"{base_url}/{parent}/agents"

    try:
        logging.info(f"DEBUG: list_employee_agents called for {parent}")
        resp = session.get(url)
        resp.raise_for_status()
        data = resp.json()
        logging.info(f"DEBUG: list_employee_agents API response: {json.dumps(data, indent=2)}")
        agents = data.get("agents", [])
        
        employee_agents = []
        for agent in agents:
            displayName = agent.get("displayName")
            name = agent.get("name")
            description = agent.get("description")
            
            root_instructions = "No instructions found."
            root_tools = []
            sub_agents = []
            
            if "lowCodeAgentDefinition" in agent:
                definition = agent.get("lowCodeAgentDefinition", {})
                nodes = definition.get("nodes", [])
                root_id = definition.get("rootAgentId")
                
                for node in nodes:
                    node_id = node.get("id")
                    llm_node = node.get("llmAgentNode", {})
                    node_instruction = llm_node.get("instruction", "No instructions found.")
                    
                    # Extract tools for this node
                    node_tools = []
                    for t in llm_node.get("selectedTools", {}).get("tool", []):
                        node_tools.append(t.get("name", "Unknown Tool"))
                    for spec in llm_node.get("dataStoreSpecs", {}).get("specs", []):
                        ds = spec.get("dataStore", "")
                        if ds:
                            ds_name = ds.split("/")[-1]
                            node_tools.append(f"DataStore: {ds_name}")
                        
                    if node_id == root_id:
                        root_instructions = node_instruction
                        root_tools = node_tools
                    else:
                        sub_agents.append({
                            "displayName": node.get("displayName", "Sub-Agent"),
                            "description": llm_node.get("description", ""),
                            "model": llm_node.get("model", "Unknown Model"),
                            "instructions": node_instruction,
                            "tools": node_tools
                        })
            elif "skillAgentDefinition" in agent:
                definition = agent.get("skillAgentDefinition", {})
                root_instructions = definition.get("instruction", "No instructions found.")
                
            employee_agents.append({
                "displayName": displayName,
                "name": name,
                "description": description,
                "instructions": root_instructions,
                "connectors_and_tools": root_tools,
                "sub_agents": sub_agents
            })
        return json.dumps(employee_agents)
    except Exception as e:
        return json.dumps({"error": str(e)})

def extract_connectors(agent_def: dict) -> list:
    """Extracts unique connector and datastore names from an agent definition."""
    connectors = set()
    nodes = agent_def.get("nodes", [])
    for node in nodes:
        llm_node = node.get("llmAgentNode", {})
        
        # Extract tools
        selected_tools = llm_node.get("selectedTools", {})
        tools_list = selected_tools.get("tool", [])
        for t in tools_list:
            name = t.get("name")
            if name:
                connectors.add(name)
                
        # Extract datastores as dependencies
        for spec in llm_node.get("dataStoreSpecs", {}).get("specs", []):
            ds = spec.get("dataStore", "")
            if ds:
                ds_name = ds.split("/")[-1]
                # Apply heuristic to get friendly name (e.g., monday-mcp_... -> Monday Mcp)
                parts = ds_name.split("_")
                if parts:
                    prefix = parts[0]
                    friendly_name = " ".join([w.capitalize() for w in prefix.split("-")])
                    connectors.add(friendly_name)
                else:
                    connectors.add(ds_name)
                
    return list(connectors)

def list_target_connectors(session, base_url, target_parent) -> list:
    """Lists connectors used by agents in the target environment."""
    target_url = f"{base_url}/{target_parent}/agents"
    try:
        logging.info(f"Fetching target agents from {target_url}")
        resp = session.get(target_url)
        resp.raise_for_status()
        agents = resp.json().get("agents", [])
        
        target_connectors = set()
        for agent in agents:
            if "lowCodeAgentDefinition" in agent:
                definition = agent.get("lowCodeAgentDefinition", {})
                connectors = extract_connectors(definition)
                for c in connectors:
                    target_connectors.add(c)
        return list(target_connectors)
    except Exception as e:
        logging.error(f"Failed to list target connectors: {e}")
        return []

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
    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    
    source_parent = f"projects/{source_project_id}/locations/{source_location}/collections/default_collection/engines/{source_engine_id}/assistants/default_assistant"
    source_url = f"{base_url}/{source_parent}/agents"
    
    try:
        logging.info(f"Fetching source agent from {source_url}")
        resp = session.get(source_url)
        resp.raise_for_status()
        agents = resp.json().get("agents", [])
        
        agent_to_check = None
        for agent in agents:
            if agent.get("displayName") == source_agent_name and "lowCodeAgentDefinition" in agent:
                agent_to_check = agent
                break
                
        if not agent_to_check:
            return json.dumps({"error": f"Source agent '{source_agent_name}' not found or is not a low-code agent."})
            
        definition = agent_to_check.get("lowCodeAgentDefinition", {})
        nodes = definition.get("nodes", [])
        
        datastore_report = {}
        for node in nodes:
            node_name = node.get("displayName", "Unknown Node")
            llm_node = node.get("llmAgentNode", {})
            datastores = []
            for spec in llm_node.get("dataStoreSpecs", {}).get("specs", []):
                ds = spec.get("dataStore", "")
                if ds:
                    ds_name = ds.split("/")[-1]
                    datastores.append(ds_name)
            if datastores:
                datastore_report[node_name] = datastores
                
        return json.dumps({
            "success": True,
            "agent_name": source_agent_name,
            "datastores": datastore_report
        }, indent=2)
        
    except Exception as e:
        logging.error(f"Failed to extract datastores: {e}")
        return json.dumps({"error": str(e)})


def migrate_employee_agent(

    tool_context: ToolContext,
    source_agent_name: str,
    target_project_id: str,
    target_location: str,
    target_engine_id: str,
    source_project_id: str = PROJECT_NUMBER,
    source_location: str = LOCATION,
    source_engine_id: str = "enterprise-search-17416389_1741638989378",
    force: bool = False
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
    """
    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    
    target_parent = f"projects/{target_project_id}/locations/{target_location}/collections/default_collection/engines/{target_engine_id}/assistants/default_assistant"
    target_url = f"{base_url}/{target_parent}/agents"
    
    # 1. Fetch the source agent definition
    source_parent = f"projects/{source_project_id}/locations/{source_location}/collections/default_collection/engines/{source_engine_id}/assistants/default_assistant"
    source_url = f"{base_url}/{source_parent}/agents"
    
    try:
        logging.info(f"Fetching source agent from {source_url}")
        resp = session.get(source_url)
        resp.raise_for_status()
        agents = resp.json().get("agents", [])
        
        agent_to_migrate = None
        for agent in agents:
            if agent.get("displayName") == source_agent_name and "lowCodeAgentDefinition" in agent:
                agent_to_migrate = agent
                break
                
        if not agent_to_migrate:
            return json.dumps({"error": f"Source agent '{source_agent_name}' not found or is not a low-code agent."})
            
        # 1.4 Validation and Reporting
        src_connectors = extract_connectors(agent_to_migrate.get("lowCodeAgentDefinition", {}))
        target_connectors = list_target_connectors(session, base_url, target_parent)
        
        missing_connectors = [c for c in src_connectors if c not in target_connectors]
        
        report = {
            "source_connectors": src_connectors,
            "target_connectors_used": target_connectors,
            "missing_connectors": missing_connectors
        }
        
        logging.info(f"Connector Validation Report: {json.dumps(report)}")
        
        if missing_connectors and not force:
             return json.dumps({
                 "warning": "Missing dependencies in target environment.",
                 "report": report,
                 "message": f"The following dependencies are missing in the target environment: {missing_connectors}. Do you want to proceed anyway? If yes, please call this tool again with 'force=True'."
             })
        elif missing_connectors and force:
             logging.warning(f"Validation Warning: Missing connectors in target environment: {missing_connectors}. Proceeding anyway as forced.")
             
        # 1.5 Upload to GCS (Backup) implicitly
        bucket_name = os.environ.get("GCS_BUCKET_NAME")
        if bucket_name:
            try:
                from google.cloud import storage
                client = storage.Client()
                bucket = client.bucket(bucket_name)
                timestamp = int(time.time())
                object_name = f"exports/{source_agent_name}_{timestamp}.json"
                blob = bucket.blob(object_name)
                blob.upload_from_string(json.dumps(agent_to_migrate, indent=2))
                logging.info(f"Implicitly backed up agent '{source_agent_name}' to gs://{bucket_name}/{object_name}")
                
                # Read content back from GCS to use instead of memory
                logging.info(f"Reading back agent definition from GCS for migration.")
                gcs_content = blob.download_as_string()
                agent_to_migrate = json.loads(gcs_content)
                logging.info(f"Successfully read agent definition from GCS.")
            except Exception as e:
                logging.error(f"Failed to implicitly backup agent to GCS: {e}")
        
        # 2. Create the payload for the target environment
        definition = agent_to_migrate.get("lowCodeAgentDefinition", {})
        if "session" in definition:
            del definition["session"]
            
        # Strip datastores and add googleSearch
        nodes = definition.get("nodes", [])
        for node in nodes:
            llm_node = node.get("llmAgentNode", {})
            if "selectedTools" not in llm_node:
                llm_node["selectedTools"] = {"tool": []}
            selected_tools = llm_node["selectedTools"]
            if "tool" not in selected_tools:
                selected_tools["tool"] = []
            
            tools_list = selected_tools["tool"]
            has_google_search = False
            for t in tools_list:
                if t.get("name") == "googleSearch":
                    has_google_search = True
                    break
            if not has_google_search:
                logging.info(f"DEBUG: Adding googleSearch to node {node.get('displayName')}")
                tools_list.append({"name": "googleSearch"})
                
        payload_str = json.dumps({
            "displayName": agent_to_migrate.get("displayName"),
            "description": agent_to_migrate.get("description", ""),
            "lowCodeAgentDefinition": definition
        })
        payload_str = payload_str.replace(f"projects/{source_project_id}", f"projects/{target_project_id}")
        payload_str = payload_str.replace(source_engine_id, target_engine_id)
        payload = json.loads(payload_str)
        
        logging.info(f"Creating new agent at target {target_url}")
        create_resp = session.post(target_url, json=payload)
        create_resp.raise_for_status()
        
        message = f"Successfully migrated agent '{source_agent_name}' to target environment. Reminder: This migration assumes all required datastores are available in the target environment with the exact same names as in source."
        if missing_connectors:
             message += f" WARNING: Missing connectors were ignored: {missing_connectors}"
             
        return json.dumps({
            "success": True,
            "message": message,
            "target_agent": create_resp.json()
        })
    except Exception as e:
        error_detail = getattr(getattr(e, "response", None), "text", str(e))
        return json.dumps({"error": str(e), "detail": error_detail})

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
    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    target_url = f"{base_url}/projects/{target_project_id}/locations/{target_location}/collections/default_collection/engines/{target_engine_id}/assistants/default_assistant/agents"
    
    # Construct minimal lowCodeAgentDefinition
    definition = {
        "nodes": [
            {
                "llmAgentNode": {
                    "description": f"Migrated from Gem: {name}",
                    "model": "gemini-2.5-flash",
                    "instruction": instructions,
                    "selectedTools": {"tool": [{"name": "googleSearch"}]}
                },
                "id": "root_agent",
                "displayName": name
            }
        ],
        "rootAgentId": "root_agent"
    }
    
    payload = {
        "displayName": name,
        "description": description if description else f"Migrated from Gem: {name}",
        "lowCodeAgentDefinition": definition
    }
    
    try:
        logging.info(f"Creating new agent from Gem at target {target_url}")
        create_resp = session.post(target_url, json=payload)
        create_resp.raise_for_status()
        
        return json.dumps({
            "success": True,
            "message": f"Successfully created agent '{name}' from Gem in target environment.",
            "target_agent": create_resp.json()
        })
    except Exception as e:
        error_detail = getattr(getattr(e, "response", None), "text", str(e))
        return json.dumps({"error": str(e), "detail": error_detail})

def import_gems_from_file(
    tool_context: ToolContext,
    file_path: str,
    target_project_id: str,
    target_engine_id: str,
    target_location: str = "global"
) -> str:
    """Call this tool to import multiple Gems from a local HTML file dump.
    
    Args:
        file_path: The absolute path to the HTML file containing Gems data.
        target_project_id: The target Google Cloud project number.
        target_engine_id: The target Discovery Engine engine ID.
        target_location: The target location. Defaults to global.
    """
    import os
    
    logging.info(f"DEBUG: import_gems_from_file checking path: {file_path}")
    if not os.path.exists(file_path):
        return json.dumps({"error": f"File not found at {file_path}"})
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        gems_raw = content.split("<b>Name:</b>")
        
        success_count = 0
        fail_count = 0
        results = []
        
        for gem_str in gems_raw[1:]:
            if not gem_str.strip():
                continue
                
            parts = gem_str.split("<b>Instructions:</b>")
            if len(parts) < 2:
                logging.warning(f"Could not parse Gem entry: {gem_str[:50]}...")
                continue
                
            name_and_desc = parts[0]
            name_parts = name_and_desc.split("<b>Description:</b>")
            name = name_parts[0].replace("<br>", "").strip()
            description = ""
            if len(name_parts) > 1:
                description = name_parts[1].replace("<br>", "").strip()
            
            instructions_part = parts[1]
            inst_parts = instructions_part.split("<b>Files:</b>")
            instructions = inst_parts[0].strip()
            
            files_part = ""
            if len(inst_parts) > 1:
                files_part = inst_parts[1].strip()
                
            attached_files = []
            if files_part:
                import re
                matches = re.findall(r'<a\s+href="([^"]+)">([^<]+)</a>', files_part)
                for href, text in matches:
                    attached_files.append(f"- [{text}]({href})")
                    
            instructions = instructions.replace("<br>", "\n")
            instructions = instructions.replace("&#39;", "'")
            instructions = instructions.replace("&amp;", "&")
            
            if attached_files:
                instructions += "\n\n## Attached Files\n" + "\n".join(attached_files)
                
            logging.info(f"Importing Gem: {name}")
            try:
                resp_str = create_agent_from_gem(
                    tool_context=tool_context,
                    name=name,
                    instructions=instructions,
                    target_project_id=target_project_id,
                    target_engine_id=target_engine_id,
                    description=description,
                    target_location=target_location
                )
                resp = json.loads(resp_str)
                if resp.get("success"):
                    success_count += 1
                    results.append(f"Success: {name}")
                else:
                    fail_count += 1
                    results.append(f"Failed: {name} - {resp.get('error')}")
            except Exception as e:
                fail_count += 1
                results.append(f"Failed: {name} - {e}")
                
        return json.dumps({
            "success": True,
            "message": f"Processed file. Successfully imported {success_count} agents, failed {fail_count}.",
            "details": results
        })
        
    except Exception as e:
        return json.dumps({"error": str(e)})

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
    if not bucket_name:
        bucket_name = os.environ.get("GCS_BUCKET_NAME")
    if not bucket_name:
        return json.dumps({"error": "bucket_name not provided and GCS_BUCKET_NAME not found in environment."})

    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    
    # 1. Fetch the source agent definition
    source_parent = f"projects/{source_project_id}/locations/{source_location}/collections/default_collection/engines/{source_engine_id}/assistants/default_assistant"
    source_url = f"{base_url}/{source_parent}/agents"
    
    try:
        logging.info(f"Fetching source agent from {source_url}")
        resp = session.get(source_url)
        resp.raise_for_status()
        agents = resp.json().get("agents", [])
        
        agent_to_export = None
        for agent in agents:
            if agent.get("displayName") == source_agent_name and "lowCodeAgentDefinition" in agent:
                agent_to_export = agent
                break
                
        if not agent_to_export:
            return json.dumps({"error": f"Source agent '{source_agent_name}' not found or is not a low-code agent."})
            
        # 2. Upload to GCS
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        
        blob.upload_from_string(json.dumps(agent_to_export, indent=2))
        
        return json.dumps({
            "success": True,
            "message": f"Successfully exported agent '{source_agent_name}' to gs://{bucket_name}/{object_name}"
        })
    except Exception as e:
        error_detail = getattr(getattr(e, "response", None), "text", str(e))
        return json.dumps({"error": str(e), "detail": error_detail})

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
    if not bucket_name:
        bucket_name = os.environ.get("GCS_BUCKET_NAME")
    if not bucket_name:
        return json.dumps({"error": "bucket_name not provided and GCS_BUCKET_NAME not found in environment."})

    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    
    try:
        # 1. Read from GCS
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        
        agent_data = json.loads(blob.download_as_string())
        
        # 2. Prepare payload
        definition = agent_data.get("lowCodeAgentDefinition", {})
        if "session" in definition:
            del definition["session"]
            
        # Strip datastores and add googleSearch
        nodes = definition.get("nodes", [])
        for node in nodes:
            llm_node = node.get("llmAgentNode", {})
            if "selectedTools" not in llm_node:
                llm_node["selectedTools"] = {"tool": []}
            selected_tools = llm_node["selectedTools"]
            if "tool" not in selected_tools:
                selected_tools["tool"] = []
            
            tools_list = selected_tools["tool"]
            has_google_search = False
            for t in tools_list:
                if t.get("name") == "googleSearch":
                    has_google_search = True
                    break
            if not has_google_search:
                tools_list.append({"name": "googleSearch"})
                
        # Extract source project from the stored name to do replacements
        source_name = agent_data.get("name", "")
        import re
        match = re.search(r"projects/([^/]+)/locations/([^/]+)/collections/default_collection/engines/([^/]+)", source_name)
        
        payload_str = json.dumps({
            "displayName": agent_data.get("displayName"),
            "description": agent_data.get("description", ""),
            "lowCodeAgentDefinition": definition
        })
        
        if match:
            source_project_id = match.group(1)
            source_engine_id = match.group(3)
            payload_str = payload_str.replace(f"projects/{source_project_id}", f"projects/{target_project_id}")
            payload_str = payload_str.replace(source_engine_id, target_engine_id)
            
        payload = json.loads(payload_str)
        
        target_parent = f"projects/{target_project_id}/locations/{target_location}/collections/default_collection/engines/{target_engine_id}/assistants/default_assistant"
        target_url = f"{base_url}/{target_parent}/agents"
        
        logging.info(f"Creating new agent from GCS at target {target_url}")
        create_resp = session.post(target_url, json=payload)
        create_resp.raise_for_status()
        
        return json.dumps({
            "success": True,
            "message": f"Successfully imported agent from gs://{bucket_name}/{object_name} to target environment.",
            "target_agent": create_resp.json()
        })
        
    except Exception as e:
        error_detail = getattr(getattr(e, "response", None), "text", str(e))
        return json.dumps({"error": str(e), "detail": error_detail})

AGENT_INSTRUCTION = """
You are the Gemini Enterprise App Migration Agent. Your job is to migrate notebooks from one Gemini app to another, and to help users list employee-made agents.

CRITICAL RULES:
1. **Always start the interaction by asking the user for source and target environment details.** Do not perform any default actions until these details are confirmed.
2. **Once the user provides these details, keep them in your memory and do not ask again** for the duration of the session unless requested by the user.
3. The user must specify source details (e.g., project number, project id, region, engine id) and target details (e.g., project number, project id, region, target engine id).
   *Example Source:* Project Number 123456789012, Project ID mock-source-project, Region global, Engine ID enterprise-search-123456
    *Example Target:* Project Number 987654321098, Project ID mock-target-project, Region global, Target Engine ID gemini-enterprise-987654

Workflow:
1. List all notebook apps from the source app (using `list_notebooks`).
2. Ask the user which notebook they want to migrate, or if they want to migrate all of them.
3. Ask the user for the target Gemini Enterprise app details (Project Number and Location).
4. For each notebook to migrate:
   a. Get its sources and types using `list_sources_and_types`.
   b. Create a new notebook in the target app using `create_notebook`.
   c. For each source, map it to the correct format and add it to the new notebook using `add_source_to_notebook`.
5. List employee-made agents when requested using `list_employee_agents`.
6. Migrate (create) employee-made low-code agents to a target Gemini Enterprise environment using `migrate_employee_agent`. This will also implicitly save a backup to a GCS bucket.
7. Export employee-made low-code agents to a GCS bucket using `export_agent_to_gcs` when requested.
8. Import employee-made low-code agents from a GCS bucket to a target environment using `import_agent_from_gcs` when requested.
9. Create a new agent from Gem instructions using `create_agent_from_gem`. ALWAYS ask the user for the target project ID and engine ID before calling this tool!
10. Import multiple Gems from a local file dump using `import_gems_from_file`. ALWAYS ask the user for the target project ID and engine ID before calling this tool!


Mapping sources:
- Type "google docs": use "googleDriveContent" with documentId extracted from location URL and mimeType "application/vnd.google-apps.document". Do NOT include "sourceName" at the root of the object.
- Type "website": use "webContent" with url. Do NOT include "sourceName" at the root unless confirmed valid.
- Type "copied text": use "textContent" with content.
- Type "youtube": use "videoContent" with youtubeUrl.

Critical Rule: Do NOT delete the source notebook or its sources after migration. This is a read-and-copy operation only.

Output Format:
When presenting lists of notebooks or sources, you MUST use standard Markdown tables to make the output look grand and readable.
Do NOT output raw JSON or A2UI JSON, as the client cannot render it.

When a user asks for the details of an employee agent (e.g. "give details on Quarterly Business Review Generator"), output the details in exactly the following format without markdown code blocks:

[Agent Description]

Instructions: [Agent Instructions]

Model: [Model Name or "Gemini 3 Flash"]

Connectors: [List of connectors/tools/datastores]

Knowledge: None

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
    tools=[list_notebooks, list_sources_and_types, create_notebook, add_source_to_notebook, list_employee_agents, migrate_employee_agent, export_agent_to_gcs, import_agent_from_gcs, create_agent_from_gem, import_gems_from_file],
)
