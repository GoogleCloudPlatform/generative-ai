import json
import os
import logging
import time
import re
import google.auth
from google.auth.transport.requests import AuthorizedSession

ENDPOINT_LOCATION = "global"

def get_session():
    """Returns an authorized Google API requests session."""
    credentials, project = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    return AuthorizedSession(credentials)

def list_notebooks(project_number: str, location: str = "global") -> list:
    """Lists recently viewed notebooks in the specified project."""
    session = get_session()
    url = f"https://{ENDPOINT_LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/{project_number}/locations/{location}/notebooks:listRecentlyViewed"

    resp = session.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get("notebooks", [])

def list_sources_and_types(notebook_id: str, project_number: str, location: str = "global") -> list:
    """Lists sources and maps their types for a given notebook."""
    session = get_session()
    base_url = f"https://{ENDPOINT_LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/{project_number}/locations/{location}/notebooks/{notebook_id}"

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
            "location": source_location,
            "raw_data": src_data
        })

    return results

def create_notebook(target_project_number: str, target_location: str, title: str) -> dict:
    """Creates a new empty notebook in the target project."""
    logging.info(f"DEBUG: create_notebook called with title='{title}', project='{target_project_number}', location='{target_location}'")
    session = get_session()
    url = f"https://{ENDPOINT_LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/{target_project_number}/locations/{target_location}/notebooks"

    resp = session.post(url, json={"title": title})
    resp.raise_for_status()
    return resp.json()

def add_source_to_notebook(target_project_number: str, target_location: str, notebook_id: str, source_content: dict) -> dict:
    """Adds a single source (userContent payload) to the specified notebook."""
    logging.info(f"DEBUG: add_source_to_notebook called with notebook_id='{notebook_id}', project='{target_project_number}'")
    session = get_session()
    url = f"https://{ENDPOINT_LOCATION}-discoveryengine.googleapis.com/v1alpha/projects/{target_project_number}/locations/{target_location}/notebooks/{notebook_id}/sources:batchCreate"

    # Make a copy to avoid mutating inputs
    content_obj = json.loads(json.dumps(source_content))
    if "sourceName" in content_obj:
        logging.info(f"DEBUG: Removing invalid 'sourceName' from payload: {content_obj['sourceName']}")
        content_obj.pop("sourceName")
    
    logging.info(f"DEBUG: Sending request to {url} with payload: {json.dumps(content_obj)}")
    resp = session.post(url, json={"userContents": [content_obj]}, timeout=60)
    logging.info(f"DEBUG: Response status: {resp.status_code}")
    resp.raise_for_status()
    return resp.json()

def migrate_notebook_pipeline(
    notebook_id_or_title: str,
    target_project_number: str,
    target_location: str,
    source_project_number: str,
    source_location: str = "global"
) -> dict:
    """Migrates an entire notebook and all its sources deterministically in a python loop."""
    logging.info(f"Starting deterministic notebook migration for '{notebook_id_or_title}'")
    
    # 1. List source notebooks
    notebooks = list_notebooks(source_project_number, source_location)
    source_notebook = None
    for nb in notebooks:
        nb_id = nb.get("name", "").split("/")[-1]
        nb_title = nb.get("title", "")
        if nb_id == notebook_id_or_title or nb_title == notebook_id_or_title:
            source_notebook = nb
            break
            
    if not source_notebook:
        raise ValueError(f"Source notebook '{notebook_id_or_title}' not found.")
        
    source_nb_id = source_notebook.get("name", "").split("/")[-1]
    source_nb_title = source_notebook.get("title", "Migrated Notebook")
    
    # 2. Get all sources
    sources = list_sources_and_types(source_nb_id, source_project_number, source_location)
    logging.info(f"Found {len(sources)} sources to migrate for notebook '{source_nb_title}'")
    
    # 3. Create target notebook
    target_nb = create_notebook(target_project_number, target_location, source_nb_title)
    target_nb_id = target_nb.get("name", "").split("/")[-1]
    logging.info(f"Created target notebook '{source_nb_title}' with ID: {target_nb_id}")
    
    # 4. For each source, map and add
    migrated_sources = []
    failed_sources = []
    
    for src in sources:
        title = src.get("title", "Untitled Source")
        raw_data = src.get("raw_data", {})
        
        # Determine userContent payload
        user_content = raw_data.get("userContent")
        if user_content:
            payload = json.loads(json.dumps(user_content))
        else:
            # Reconstruct payload as fallback
            payload = {}
            metadata = raw_data.get("metadata", {})
            if "webpageMetadata" in metadata:
                payload["webContent"] = {
                    "url": metadata["webpageMetadata"].get("webpageUrl")
                }
            elif "googleDocsMetadata" in metadata:
                payload["googleDriveContent"] = {
                    "documentId": metadata["googleDocsMetadata"].get("documentId"),
                    "mimeType": "application/vnd.google-apps.document"
                }
            elif "textContent" in raw_data:
                payload["textContent"] = raw_data["textContent"]
            elif "textContent" in metadata:
                payload["textContent"] = metadata["textContent"]
                
        # Ensure displayName is set
        if "displayName" not in payload:
            payload["displayName"] = title
            
        # Strip readonly fields
        if "sourceName" in payload:
            payload.pop("sourceName")
            
        logging.info(f"Adding source '{title}' to target notebook '{target_nb_id}'")
        try:
            add_resp = add_source_to_notebook(target_project_number, target_location, target_nb_id, payload)
            migrated_sources.append({
                "title": title,
                "status": "success",
                "response": add_resp
            })
        except Exception as e:
            logging.error(f"Failed to add source '{title}': {e}")
            failed_sources.append({
                "title": title,
                "status": "failed",
                "error": str(e)
            })
            
    return {
        "success": len(failed_sources) == 0,
        "source_notebook_id": source_nb_id,
        "source_notebook_title": source_nb_title,
        "target_notebook_id": target_nb_id,
        "migrated_sources_count": len(migrated_sources),
        "failed_sources_count": len(failed_sources),
        "migrated": migrated_sources,
        "failed": failed_sources
    }

def list_employee_agents(
    project_id: str,
    location: str = "global",
    engine_id: str = "enterprise-search-17416389_1741638989378"
) -> list:
    """Lists employee-made low-code agents."""
    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    parent = f"projects/{project_id}/locations/{location}/collections/default_collection/engines/{engine_id}/assistants/default_assistant"
    url = f"{base_url}/{parent}/agents"

    logging.info(f"DEBUG: list_employee_agents called for {parent}")
    resp = session.get(url)
    resp.raise_for_status()
    data = resp.json()
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
            "sub_agents": sub_agents,
            "raw_agent": agent
        })
    return employee_agents

def extract_connectors(agent_def: dict) -> list:
    """Extracts unique connector and datastore names from an agent definition."""
    connectors = set()
    nodes = agent_def.get("nodes", [])
    for node in nodes:
        llm_node = node.get("llmAgentNode", {})
        
        selected_tools = llm_node.get("selectedTools", {})
        tools_list = selected_tools.get("tool", [])
        for t in tools_list:
            name = t.get("name")
            if name:
                connectors.add(name)
                
        for spec in llm_node.get("dataStoreSpecs", {}).get("specs", []):
            ds = spec.get("dataStore", "")
            if ds:
                ds_name = ds.split("/")[-1]
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
    source_agent_name: str,
    source_project_id: str,
    source_location: str = "global",
    source_engine_id: str = "enterprise-search-17416389_1741638989378"
) -> dict:
    """Extracts and lists the names of datastores used by an agent and its subagents."""
    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    source_parent = f"projects/{source_project_id}/locations/{source_location}/collections/default_collection/engines/{source_engine_id}/assistants/default_assistant"
    source_url = f"{base_url}/{source_parent}/agents"
    
    resp = session.get(source_url)
    resp.raise_for_status()
    agents = resp.json().get("agents", [])
    
    agent_to_check = None
    for agent in agents:
        if agent.get("displayName") == source_agent_name and "lowCodeAgentDefinition" in agent:
            agent_to_check = agent
            break
            
    if not agent_to_check:
        raise ValueError(f"Source agent '{source_agent_name}' not found or is not a low-code agent.")
        
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
            
    return {
        "agent_name": source_agent_name,
        "datastores": datastore_report
    }

def migrate_employee_agent(
    source_agent_name: str,
    target_project_id: str,
    target_location: str,
    target_engine_id: str,
    source_project_id: str,
    source_location: str = "global",
    source_engine_id: str = "enterprise-search-17416389_1741638989378",
    force: bool = False,
    backup_bucket: str = ""
) -> dict:
    """Migrates an employee-made low-code agent to a target environment."""
    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    
    target_parent = f"projects/{target_project_id}/locations/{target_location}/collections/default_collection/engines/{target_engine_id}/assistants/default_assistant"
    target_url = f"{base_url}/{target_parent}/agents"
    
    # 1. Fetch the source agent definition
    source_parent = f"projects/{source_project_id}/locations/{source_location}/collections/default_collection/engines/{source_engine_id}/assistants/default_assistant"
    source_url = f"{base_url}/{source_parent}/agents"
    
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
        raise ValueError(f"Source agent '{source_agent_name}' not found or is not a low-code agent.")
        
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
         return {
             "success": False,
             "warning": "Missing dependencies in target environment.",
             "report": report,
             "message": f"The following dependencies are missing in the target environment: {missing_connectors}."
         }
         
    # 1.5 Upload to GCS (Backup) implicitly
    bucket_name = backup_bucket if backup_bucket else os.environ.get("GCS_BUCKET_NAME")
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
            logging.info("Reading back agent definition from GCS for migration.")
            gcs_content = blob.download_as_string()
            agent_to_migrate = json.loads(gcs_content)
            logging.info("Successfully read agent definition from GCS.")
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
         
    return {
        "success": True,
        "message": message,
        "target_agent": create_resp.json()
    }

def create_agent_from_gem(
    name: str,
    instructions: str,
    target_project_id: str,
    target_engine_id: str,
    description: str = "",
    target_location: str = "global"
) -> dict:
    """Creates a new Gemini Enterprise agent from Gem definition (name and instructions)."""
    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    target_url = f"{base_url}/projects/{target_project_id}/locations/{target_location}/collections/default_collection/engines/{target_engine_id}/assistants/default_assistant/agents"
    
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
    
    logging.info(f"Creating new agent from Gem at target {target_url}")
    create_resp = session.post(target_url, json=payload)
    create_resp.raise_for_status()
    
    return {
        "success": True,
        "message": f"Successfully created agent '{name}' from Gem in target environment.",
        "target_agent": create_resp.json()
    }

def import_gems_from_file(
    file_path: str,
    target_project_id: str,
    target_engine_id: str,
    target_location: str = "global"
) -> dict:
    """Imports multiple Gems from a local HTML file dump."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at {file_path}")
        
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
            resp = create_agent_from_gem(
                name=name,
                instructions=instructions,
                target_project_id=target_project_id,
                target_engine_id=target_engine_id,
                description=description,
                target_location=target_location
            )
            if resp.get("success"):
                success_count += 1
                results.append(f"Success: {name}")
            else:
                fail_count += 1
                results.append(f"Failed: {name} - {resp.get('error')}")
        except Exception as e:
            fail_count += 1
            results.append(f"Failed: {name} - {e}")
            
    return {
        "success": True,
        "message": f"Processed file. Successfully imported {success_count} agents, failed {fail_count}.",
        "details": results
    }

def export_agent_to_gcs(
    source_agent_name: str,
    object_name: str,
    bucket_name: str = "",
    source_project_id: str = "",
    source_location: str = "global",
    source_engine_id: str = "enterprise-search-17416389_1741638989378"
) -> dict:
    """Exports an employee-made low-code agent definition to a GCS bucket."""
    if not bucket_name:
        bucket_name = os.environ.get("GCS_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("bucket_name not provided and GCS_BUCKET_NAME not found in environment.")

    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    source_parent = f"projects/{source_project_id}/locations/{source_location}/collections/default_collection/engines/{source_engine_id}/assistants/default_assistant"
    source_url = f"{base_url}/{source_parent}/agents"
    
    resp = session.get(source_url)
    resp.raise_for_status()
    agents = resp.json().get("agents", [])
    
    agent_to_export = None
    for agent in agents:
        if agent.get("displayName") == source_agent_name and "lowCodeAgentDefinition" in agent:
            agent_to_export = agent
            break
            
    if not agent_to_export:
        raise ValueError(f"Source agent '{source_agent_name}' not found or is not a low-code agent.")
        
    from google.cloud import storage
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_string(json.dumps(agent_to_export, indent=2))
    
    return {
        "success": True,
        "message": f"Successfully exported agent '{source_agent_name}' to gs://{bucket_name}/{object_name}"
    }

def import_agent_from_gcs(
    object_name: str,
    target_project_id: str,
    target_location: str,
    target_engine_id: str,
    bucket_name: str = ""
) -> dict:
    """Imports an agent definition from GCS and creates it in a target environment."""
    if not bucket_name:
        bucket_name = os.environ.get("GCS_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("bucket_name not provided and GCS_BUCKET_NAME not found in environment.")

    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    
    from google.cloud import storage
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    agent_data = json.loads(blob.download_as_string())
    
    definition = agent_data.get("lowCodeAgentDefinition", {})
    if "session" in definition:
        del definition["session"]
        
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
            
    source_name = agent_data.get("name", "")
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
    
    return {
        "success": True,
        "message": f"Successfully imported agent from gs://{bucket_name}/{object_name} to target environment.",
        "target_agent": create_resp.json()
    }
