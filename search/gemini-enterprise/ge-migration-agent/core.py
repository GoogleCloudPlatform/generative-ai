import json
import os
import logging
import time
import re
import urllib.parse
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(env_path)
except ImportError:
    pass
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
    source_nb_title = source_notebook.get("title", "Untitled Notebook")
    
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
        displayName = (agent.get("displayName") or "").replace("\r\n", " ").replace("\n", " ")
        name = agent.get("name")
        description = (agent.get("description") or "").replace("\r\n", " ").replace("\n", " ")
        
        root_instructions = "No instructions found."
        root_tools = []
        root_knowledge = []
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
                node_knowledge = []
                for k_field in ["groundingSources", "userContents", "files", "knowledge"]:
                    for item in llm_node.get(k_field, []):
                        title = item.get("displayName") or item.get("googleDriveContent", {}).get("documentId")
                        if title and title not in node_knowledge:
                            node_knowledge.append(title)
                for match in re.findall(r'\[([^\]]+)\]\(https://drive\.google\.com/[^\)]+\)', node_instruction):
                    if match and match not in node_knowledge:
                        node_knowledge.append(match)
                    
                if node_id == root_id:
                    root_instructions = node_instruction
                for nt in node_tools:
                    if nt not in root_tools:
                        root_tools.append(nt)
                for nk in node_knowledge:
                    if nk not in root_knowledge:
                        root_knowledge.append(nk)
                else:
                    sub_agents.append({
                        "displayName": node.get("displayName", "Sub-Agent"),
                        "description": llm_node.get("description", ""),
                        "model": llm_node.get("model", "Unknown Model"),
                        "instructions": node_instruction,
                        "tools": node_tools,
                        "knowledge": node_knowledge
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
            "knowledge": root_knowledge,
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

def clean_connector_name(name: str) -> str:
    """Strips common suffixes like May29, dates, punctuation for robust fuzzy matching."""
    clean = re.sub(r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\d*', '', name, flags=re.IGNORECASE)
    return re.sub(r'[^a-zA-Z0-9]', '', clean).lower()

def lookup_and_map_connectors(
    source_agent_name: str,
    target_project_id: str,
    target_location: str,
    target_engine_id: str,
    source_project_id: str,
    source_location: str = "global",
    source_engine_id: str = "enterprise-search-17416389_1741638989378"
) -> dict:
    """Intelligently matches source agent connectors against target environment connectors."""
    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    source_parent = f"projects/{source_project_id}/locations/{source_location}/collections/default_collection/engines/{source_engine_id}/assistants/default_assistant"
    source_url = f"{base_url}/{source_parent}/agents"
    
    resp = session.get(source_url)
    if resp.status_code == 200:
        agents = resp.json().get("agents", [])
    else:
        agents = []
        
    src_connectors = set()
    for ag in agents:
        if source_agent_name.upper() == "ALL" or ag.get("displayName", "").lower() == source_agent_name.lower():
            for c in extract_connectors(ag.get("lowCodeAgentDefinition", {})):
                src_connectors.add(c)
    src_connectors = list(src_connectors)
            
    target_parent = f"projects/{target_project_id}/locations/{target_location}/collections/default_collection/engines/{target_engine_id}/assistants/default_assistant"
    target_connectors = list_target_connectors(session, base_url, target_parent)
    try:
        source_ds_objs = list_datastores(source_project_id, source_location)
    except Exception:
        source_ds_objs = []
    try:
        target_ds_objs = list_datastores(target_project_id, target_location)
    except Exception:
        target_ds_objs = []
        
    canonical_tools = ["googleSearch", "urlContext", "geGmail", "snowflakeMcp"]
    verified_target_ids = [ds["id"] for ds in target_ds_objs]
    all_targets = canonical_tools + verified_target_ids
    
    mapping = {}
    missing = []
    for sc in src_connectors:
        sc_clean = clean_connector_name(sc)
        matched = None
        for s_ds in source_ds_objs:
            if s_ds["id"] == sc or s_ds["displayName"].lower() == sc.lower():
                for t_ds in target_ds_objs:
                    if t_ds["displayName"].lower() == s_ds["displayName"].lower():
                        if s_ds["displayName"].lower() == "mcp_data":
                            s_pref = s_ds["id"].split("_")[0].split("-")[0].lower()
                            t_pref = t_ds["id"].split("_")[0].split("-")[0].lower()
                            if s_pref != t_pref:
                                continue
                        matched = t_ds["id"]
                        break
                break
                
        if not matched:
            for tc in all_targets:
                if clean_connector_name(tc) == sc_clean:
                    matched = tc
                    break
                    
        if matched:
            mapping[sc] = matched
        else:
            mapping[sc] = "❌ Missing (Not Ingested in Target)"
            missing.append(sc)
            
    return {
        "source_agent": source_agent_name,
        "source_connectors": src_connectors,
        "target_available": all_targets,
        "proposed_mapping": mapping,
        "missing_connectors": missing
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
    backup_bucket: str = "",
    connector_mapping: str = ""
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
            timestamp = int(time.time())
            object_name = f"exports/{source_agent_name}_{timestamp}.json"
            encoded_obj = urllib.parse.quote(object_name, safe="")
            upload_url = f"https://storage.googleapis.com/upload/storage/v1/b/{bucket_name}/o?uploadType=media&name={encoded_obj}"
            up_resp = session.post(
                upload_url,
                data=json.dumps(agent_to_migrate, indent=2),
                headers={"Content-Type": "application/json"}
            )
            up_resp.raise_for_status()
            logging.info(f"Implicitly backed up agent '{source_agent_name}' to gs://{bucket_name}/{object_name}")
        except Exception as e:
            logging.error(f"Failed to implicitly backup agent to GCS: {e}")
    
    # 2. Create the payload for the target environment
    definition = agent_to_migrate.get("lowCodeAgentDefinition", {})
    if "session" in definition:
        del definition["session"]
        
    mapping_dict = {}
    if connector_mapping:
        try:
            mapping_dict = json.loads(connector_mapping)
        except Exception:
            for pair in connector_mapping.split(","):
                if ":" in pair:
                    k, v = pair.split(":", 1)
                    mapping_dict[k.strip()] = v.strip()
                    
    # Apply tool mapping and ensure googleSearch
    all_nodes = definition.get("nodes", []) + definition.get("deployedNodes", [])
    for node in all_nodes:
        llm_node = node.get("llmAgentNode", {})
        if "selectedTools" not in llm_node:
            llm_node["selectedTools"] = {"tool": []}
        selected_tools = llm_node["selectedTools"]
        tools_list = selected_tools.get("tool", [])
        
        new_tools = []
        has_google_search = False
        for t in tools_list:
            t_name = t.get("name", "")
            if t_name in mapping_dict:
                t_name = mapping_dict[t_name]
            elif clean_connector_name(t_name) == clean_connector_name("snowflakeMcp"):
                t_name = mapping_dict.get("Snowflake Mcp May29", "snowflakeMcp")
                
            if t_name == "googleSearch":
                has_google_search = True
            if t_name:
                new_tools.append({"name": t_name})
                
        if not has_google_search:
            new_tools.append({"name": "googleSearch"})
        selected_tools["tool"] = new_tools
        
        new_specs = []
        for spec in llm_node.get("dataStoreSpecs", {}).get("specs", []):
            ds = spec.get("dataStore", "")
            if ds:
                ds_id = ds.split("/")[-1]
                if ds_id in mapping_dict:
                    ds_id = mapping_dict[ds_id]
                new_ds = f"projects/{target_project_id}/locations/{target_location}/collections/default_collection/dataStores/{ds_id}"
                new_specs.append({"dataStore": new_ds})
        if new_specs:
            llm_node["dataStoreSpecs"] = {"specs": new_specs}
            if any("snowflake" in s.get("dataStore", "").lower() for s in new_specs):
                sf_conn = mapping_dict.get("Snowflake Mcp May29", "custom_mcp")
                if not any(t.get("name") == sf_conn for t in new_tools):
                    new_tools.append({"name": sf_conn})
                selected_tools["tool"] = new_tools
            if any("drive" in s.get("dataStore", "").lower() for s in new_specs):
                dr_conn = mapping_dict.get("ge-drive-all", "Drive")
                if not any(t.get("name") == dr_conn for t in new_tools):
                    new_tools.append({"name": dr_conn})
                selected_tools["tool"] = new_tools
            
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
    
    created_agent = create_resp.json()
    tgt_extracted = extract_connectors(created_agent.get("lowCodeAgentDefinition", {}))
    message = f"Successfully migrated agent '{source_agent_name}' to target environment.\nConnectors in Source Agent: {src_connectors}\nConnectors in Target Agent: {tgt_extracted}"
    truly_missing = [c for c in missing_connectors if c not in mapping_dict]
    if truly_missing:
         message += f"\nWARNING: Missing connectors were ignored: {truly_missing}"
         
    return {
        "success": True,
        "message": message,
        "target_agent": created_agent
    }

def create_agent_from_gem(
    name: str,
    instructions: str,
    target_project_id: str,
    target_engine_id: str,
    description: str = "",
    target_location: str = "global",
    files: list = None
) -> dict:
    """Creates a new Gemini Enterprise agent from Gem definition (name and instructions)."""
    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    target_url = f"{base_url}/projects/{target_project_id}/locations/{target_location}/collections/default_collection/engines/{target_engine_id}/assistants/default_assistant/agents"
    
    llm_node = {
        "description": f"Migrated from Gem: {name}",
        "model": "gemini-2.5-flash",
        "instruction": instructions,
        "selectedTools": {"tool": [{"name": "googleSearch"}]}
    }
    
    grounding_specs = []
    if files:
        specs = []
        tools = [{"name": "googleSearch"}]
        for file_obj in files:
            doc_id = file_obj.get("documentId")
            if doc_id:
                dr_ds = "ge-drive-all_1780835769760_google_drive"
                d_name = file_obj.get("displayName", "Standard_Vendor_Template_2026")
                specs.append({
                    "dataStore": f"projects/{target_project_id}/locations/{target_location}/collections/default_collection/dataStores/{dr_ds}",
                    "filter": d_name
                })
                specs.append({
                    "dataStore": f"projects/{target_project_id}/locations/{target_location}/collections/default_collection/dataStores/{doc_id}_google_docs",
                    "filter": d_name
                })
                specs.append({
                    "dataStore": f"projects/{target_project_id}/locations/{target_location}/collections/default_collection/dataStores/{doc_id}_google_drive",
                    "filter": d_name
                })
                specs.append({
                    "dataStore": f"projects/{target_project_id}/locations/{target_location}/collections/default_collection/dataStores/{doc_id}_document",
                    "filter": d_name
                })
                specs.append({
                    "dataStore": f"projects/{target_project_id}/locations/{target_location}/collections/default_collection/dataStores/{doc_id}",
                    "filter": d_name
                })
        if specs:
            llm_node["dataStoreSpecs"] = {"specs": specs}
            llm_node["selectedTools"] = {"tool": tools}
            
    definition = {
        "nodes": [
            {
                "llmAgentNode": llm_node,
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
        list_resp = session.get(target_url)
        if list_resp.status_code == 200:
            for ex_ag in list_resp.json().get("agents", []):
                if ex_ag.get("displayName") == name and "name" in ex_ag:
                    logging.info(f"Deleting existing target agent '{name}' ({ex_ag['name']}) to overwrite.")
                    session.delete(f"{base_url}/{ex_ag['name']}")
    except Exception as e:
        logging.warning(f"Failed to check/delete existing target agent '{name}': {e}")
        
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
    root_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        file_path,
        os.path.join(root_dir, file_path),
        os.path.join(root_dir, file_path.lstrip("./")),
        os.path.join(root_dir, file_path.lstrip("./").replace("ge-migration-agent/", "", 1)),
        os.path.join(root_dir, "sample_data", os.path.basename(file_path))
    ]
    resolved_path = None
    for cand in candidates:
        if os.path.exists(cand):
            resolved_path = cand
            break
            
    if not resolved_path:
        raise FileNotFoundError(f"File not found at '{file_path}' (checked root {root_dir}).")
        
    with open(resolved_path, "r", encoding="utf-8") as f:
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
        parsed_files = []
        if files_part:
            matches = re.findall(r'<a\s+href="([^"]+)">([^<]+)</a>', files_part)
            for href, text in matches:
                attached_files.append(f"- [{text}]({href})")
                doc_id_match = re.search(r'[?&]id=([^&]+)', href) or re.search(r'/d/([^/]+)', href)
                if doc_id_match:
                    parsed_files.append({
                        "displayName": text.strip(),
                        "documentId": doc_id_match.group(1).strip()
                    })
                
        instructions = instructions.replace("<br>", "\n")
        instructions = instructions.replace("&#39;", "'")
        instructions = instructions.replace("&amp;", "&")
        
        if attached_files:
            instructions += "\n\n## Attached Files\n" + "\n".join(attached_files)
            
        logging.info(f"Importing Gem: {name} with {len(parsed_files)} attached files")
        try:
            resp = create_agent_from_gem(
                name=name,
                instructions=instructions,
                target_project_id=target_project_id,
                target_engine_id=target_engine_id,
                description=description,
                target_location=target_location,
                files=parsed_files
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
        
    encoded_obj = urllib.parse.quote(object_name, safe="")
    upload_url = f"https://storage.googleapis.com/upload/storage/v1/b/{bucket_name}/o?uploadType=media&name={encoded_obj}"
    up_resp = session.post(
        upload_url,
        data=json.dumps(agent_to_export, indent=2),
        headers={"Content-Type": "application/json"}
    )
    up_resp.raise_for_status()
    
    return {
        "success": True,
        "message": f"Successfully exported agent '{source_agent_name}' to gs://{bucket_name}/{object_name}"
    }

def import_agent_from_gcs(
    object_name: str,
    target_project_id: str,
    target_location: str,
    target_engine_id: str,
    bucket_name: str = "",
    connector_mapping: str = ""
) -> dict:
    """Imports an agent definition from GCS and creates it in a target environment."""
    if not bucket_name:
        bucket_name = os.environ.get("GCS_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("bucket_name not provided and GCS_BUCKET_NAME not found in environment.")

    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    
    encoded_object = urllib.parse.quote(object_name, safe="")
    gcs_url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o/{encoded_object}?alt=media"
    dl_resp = session.get(gcs_url)
    dl_resp.raise_for_status()
    agent_data = dl_resp.json()
    
    mapping_dict = {}
    if connector_mapping:
        try:
            mapping_dict = json.loads(connector_mapping)
        except Exception:
            for pair in connector_mapping.split(","):
                if ":" in pair:
                    k, v = pair.split(":", 1)
                    mapping_dict[k.strip()] = v.strip()

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
            
        new_specs = llm_node.get("dataStoreSpecs", {}).get("specs", [])
        if any("snowflake" in s.get("dataStore", "").lower() for s in new_specs):
            sf_conn = mapping_dict.get("Snowflake Mcp May29", "custom_mcp")
            if not any(t.get("name") == sf_conn for t in tools_list):
                tools_list.append({"name": sf_conn})
        if any("drive" in s.get("dataStore", "").lower() for s in new_specs):
            dr_conn = mapping_dict.get("ge-drive-all", "Drive")
            if not any(t.get("name") == dr_conn for t in tools_list):
                tools_list.append({"name": dr_conn})
            
        if "selectedTools" in llm_node:
            for t in llm_node["selectedTools"].get("tool", []):
                tool_name = t.get("name")
                if tool_name in mapping_dict:
                    t["name"] = mapping_dict[tool_name]
                    
        if "dataStoreSpecs" in llm_node:
            for s in llm_node["dataStoreSpecs"].get("specs", []):
                ds = s.get("dataStore", "")
                for src_id, tgt_id in mapping_dict.items():
                    if src_id in ds:
                        s["dataStore"] = ds.replace(src_id, tgt_id)
                        ds = s["dataStore"]

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

def list_datastores(project_id: str, location: str = "global", collection: str = "default_collection") -> list:
    """Lists all available datastores and their IDs in a target project/location."""
    session = get_session()
    base_url = "https://discoveryengine.googleapis.com/v1alpha"
    url = f"{base_url}/projects/{project_id}/locations/{location}/collections/{collection}/dataStores"
    
    logging.info(f"Fetching datastores from {url}")
    resp = session.get(url)
    resp.raise_for_status()
    
    datastores = resp.json().get("dataStores", [])
    results = []
    for ds in datastores:
        ds_name = ds.get("name", "")
        ds_id = ds_name.split("/")[-1] if ds_name else "Unknown ID"
        results.append({
            "id": ds_id,
            "displayName": ds.get("displayName", ""),
            "name": ds_name
        })
    return results
