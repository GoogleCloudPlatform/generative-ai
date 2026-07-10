# Copyright 2026 Google LLC
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


# Deployed as a runtime template into the user's Cloud Shell (not imported by
# repo tooling); validated by py_compile and end-to-end demo deployments.
# Repo-level strict lint/typing is intentionally skipped for this generated-
# origin runtime code; incremental typing is planned as follow-up.
# flake8: noqa
# pylint: skip-file
# mypy: ignore-errors
# ruff: noqa

import os
from typing import Union, Any
import asyncio
from google.adk.agents.readonly_context import ReadonlyContext
import dotenv
import google.auth
import google.auth.transport.requests
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_tool import MCPTool
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
import httpx
from google.adk.auth import AuthCredential, AuthCredentialTypes, OAuth2Auth
import anyio
import time
import uuid
from google.adk.tools import ToolContext
from google.genai import client as genai_client, types as genai_types
import json
from fastapi.openapi.models import OAuth2, OAuthFlows, OAuthFlowAuthorizationCode

_orig_default = json.JSONEncoder.default
def _patched_default(self, obj):
    if isinstance(obj, genai_types.Part):
        return obj.model_dump(exclude_none=True)
    return _orig_default(self, obj)
json.JSONEncoder.default = _patched_default





def get_project_id():
    """Robustly retrieves the project ID from env, .env, or credentials."""
    # 1. Direct env
    pid = os.getenv("GOOGLE_CLOUD_PROJECT")
    if pid: return pid
    
    # 2. Try loading .env from root or package
    dotenv.load_dotenv()
    pid = os.getenv("GOOGLE_CLOUD_PROJECT")
    if pid: return pid
    
    # 3. Fallback to auth default
    try:
        _, pid = google.auth.default()
        if pid: return pid
    except: pass
    return "UNKNOWN"

# =============================================================================
# 🛡️ Stability Patches for Reasoning Engine (Mandatory)
# =============================================================================

_orig_client_init = httpx.AsyncClient.__init__
def _patched_client_init(self, *args, **kwargs):
    kwargs['http2'] = False 
    # Use long timeouts for stable MCP sessions (300s)
    kwargs['timeout'] = httpx.Timeout(300.0, connect=60.0)
    return _orig_client_init(self, *args, **kwargs)

_token_cache = {"token": None, "expiry": 0, "credentials": None}
_token_lock = asyncio.Lock()

async def _get_fresh_mcp_token():
    """Retrieves a fresh access token with async-safe caching."""
    global _token_cache
    async with _token_lock:
        now = time.time()
        if _token_cache["token"] and now < _token_cache["expiry"]:
            return _token_cache["token"]
        try:
            if _token_cache["credentials"] is None:
                # google.auth.default() makes blocking network calls. We run it in a thread
                # to prevent it from deadlocking the main asyncio event loop if the metadata server hangs.
                def _get_creds():
                    scopes = ["https://www.googleapis.com/auth/cloud-platform", "https://www.googleapis.com/auth/bigquery"]
                    creds, _ = google.auth.default(scopes=scopes)
                    return creds
                _token_cache["credentials"] = await anyio.to_thread.run_sync(_get_creds)
            
            credentials = _token_cache["credentials"]
            
            # CRITICAL: google.auth's Request does not accept a timeout in its constructor,
            # and defaults to infinite timeout. This hangs the worker thread and deadlocks the
            # entire asyncio TaskGroup on Cloud Run cold starts. We must inject a custom session.
            import requests
            class TimeoutSession(requests.Session):
                def request(self, *args, **kwargs):
                    kwargs.setdefault('timeout', 10.0)
                    return super().request(*args, **kwargs)
                    
            req = google.auth.transport.requests.Request(session=TimeoutSession())
            await anyio.to_thread.run_sync(credentials.refresh, req)
            _token_cache = {"token": credentials.token, "expiry": now + 1800, "credentials": credentials}
            return credentials.token
        except Exception as e: 
            import logging
            logging.warning(f"Failed to refresh MCP token: {e}")
            return ""

_orig_send = httpx.AsyncClient.send
async def _patched_send(self, request, *args, **kwargs):
    _url = str(request.url)
    
    # BigQuery, Firestore & Knowledge Catalog (Dataplex) MCP Auth Injection
    if "bigquery.googleapis.com/mcp" in _url or "firestore.googleapis.com/mcp" in _url or "dataplex.googleapis.com/mcp" in _url:
        token = await _get_fresh_mcp_token()
        if token: request.headers['Authorization'] = f"Bearer {token}"
            


    # Execute actual request
    response = await _orig_send(self, request, *args, **kwargs)
    
    # Error Transmutation (JSON-RPC Protocol Compliance)
    # MCP uses JSON-RPC, which requires all responses (including errors) to be HTTP 200.
    # Google's MCP endpoints sometimes return HTTP 400/403 for JSON-RPC errors (e.g., 
    # invalid SQL, permission denied, DML failures). If we don't convert these to HTTP 200,
    # the HTTP transport layer in ADK rejects them before the LLM can see the error details.
    # By converting to 200, the JSON-RPC error payload reaches the LLM, which can then
    # report the actual error (e.g., "Column not found") and attempt recovery.
    if response.status_code in [400, 403] and ("bigquery.googleapis.com/mcp" in _url or "firestore.googleapis.com/mcp" in _url or "dataplex.googleapis.com/mcp" in _url):
        try:
            body = b""
            async for chunk in response.aiter_bytes():
                body += chunk
                if len(body) > 0 or not chunk:
                    break
            # Only transmute if the body is a valid JSON-RPC response
            if b'"jsonrpc":' in body: response.status_code = 200
            response._content = body
        except Exception: 
            pass
    return response

# Apply Stability Patches
try:
    # 1. HTTP/2 Disable for stability
    httpx.AsyncClient.__init__ = _patched_client_init
    httpx.AsyncClient.send = _patched_send
    
    # 2. MCP Cancel-Scope Fix (backport for ADK <=1.31.1)
    # ADK's SessionContext._run() wraps client context entry in asyncio.wait_for(),
    # which runs in a nested task. AnyIO's CancelScope must be entered/exited in the
    # same task, so this causes "Attempted to exit cancel scope in a different task".
    # The fix (from ADK main branch) removes the wait_for wrapper.
    # When ADK ships the _MCP_GRACEFUL_ERROR_HANDLING flag, the env var takes over.
    from google.adk.tools.mcp_tool.session_context import SessionContext as _SC
    _orig_sc_run = _SC._run
    async def _patched_sc_run(self):
        try:
            async with __import__('contextlib').AsyncExitStack() as exit_stack:
                # NO asyncio.wait_for here — this is the fix
                transports = await exit_stack.enter_async_context(self._client)
                from datetime import timedelta
                if self._is_stdio:
                    session = await exit_stack.enter_async_context(
                        __import__('mcp').ClientSession(
                            *transports[:2],
                            read_timeout_seconds=timedelta(seconds=self._timeout)
                            if self._timeout is not None else None,
                            sampling_callback=getattr(self, '_sampling_callback', None),
                            sampling_capabilities=getattr(self, '_sampling_capabilities', None),
                        )
                    )
                else:
                    _srt = getattr(self, '_sse_read_timeout', None) or self._timeout
                    session = await exit_stack.enter_async_context(
                        __import__('mcp').ClientSession(
                            *transports[:2],
                            read_timeout_seconds=timedelta(seconds=_srt)
                            if _srt is not None else None,
                            sampling_callback=getattr(self, '_sampling_callback', None),
                            sampling_capabilities=getattr(self, '_sampling_capabilities', None),
                        )
                    )
                _init_timeout = max(self._timeout or 60, 60)  # At least 60s for custom MCP sidecars
                await asyncio.wait_for(session.initialize(), timeout=_init_timeout)
                import logging as _log
                _log.getLogger('google_adk.session_context').debug('Session initialized (patched)')
                self._session = session
                self._ready_event.set()
                await self._close_event.wait()
        except BaseException as e:
            import logging as _log
            _logger = _log.getLogger('google_adk.session_context')
            _logger.warning(f'Error on session runner task: {e}')
            # Log sub-exceptions for TaskGroup/ExceptionGroup errors
            if hasattr(e, 'exceptions'):
                for i, sub_ex in enumerate(e.exceptions):
                    _logger.warning(f'  Sub-exception [{i}]: {type(sub_ex).__name__}: {sub_ex}')
                    if hasattr(sub_ex, 'exceptions'):
                        for j, sub_sub in enumerate(sub_ex.exceptions):
                            _logger.warning(f'    Sub-sub-exception [{i}.{j}]: {type(sub_sub).__name__}: {sub_sub}')
            import traceback
            _logger.debug(f'Full traceback: {traceback.format_exc()}')
            raise
        finally:
            self._ready_event.set()
            self._close_event.set()
    _SC._run = _patched_sc_run
except Exception as e:
    import logging; logging.warning(f"Stability patches not applied: {e}")

# =============================================================================
# 3. Deterministic-5xx Fast-Fail (v10.71)
# Vertex returns 500 INTERNAL "Limits exceeded while trying to flatten
# schema. Schema is too complex to process." when a tool declaration cannot
# be compiled server-side (e.g. a recursive custom-MCP schema reached the
# API raw). The error is DETERMINISTIC for a given toolset, yet
# HttpRetryOptions treats every 500 as transient: tenacity burns attempts=8
# (~4 min) per LLM call, and the synth-salvage repeats it 3 more times --
# a ~16-minute hang ending in ServerError (confirmed 2026-06-10,
# demo-demand-inventor + line-bot-mcp-server).
# Patching at the google.genai errors layer (not httpx) is transport-
# agnostic: it works whether the SDK picks aiohttp or httpx. Demoting the
# status to 400 takes it out of the retriable code set ([429, 500, 503]),
# so the call fails in ~1s and the executor's salvage path takes over.
# The original error message is preserved inside response_json for logs.
# =============================================================================
try:
    from google.genai import errors as _genai_errors

    _DETERMINISTIC_5XX_MARKERS = (
        "flatten schema",
        "Schema is too complex",
    )

    def _is_deterministic_5xx(status_code, response_json):
        try:
            if not (500 <= int(status_code or 0) < 600):
                return False
        except Exception:
            return False
        try:
            _msg = str((response_json or {}).get("error", {}).get("message", ""))
        except Exception:
            _msg = str(response_json)
        return any(_m in _msg for _m in _DETERMINISTIC_5XX_MARKERS)

    _orig_raise_error = _genai_errors.APIError.raise_error.__func__
    _orig_raise_error_async = _genai_errors.APIError.raise_error_async.__func__

    @classmethod
    def _patched_raise_error(cls, status_code, response_json, response):
        if _is_deterministic_5xx(status_code, response_json):
            raise _genai_errors.ClientError(400, response_json, response)
        _orig_raise_error(cls, status_code, response_json, response)

    @classmethod
    async def _patched_raise_error_async(cls, status_code, response_json, response):
        if _is_deterministic_5xx(status_code, response_json):
            raise _genai_errors.ClientError(400, response_json, response)
        await _orig_raise_error_async(cls, status_code, response_json, response)

    _genai_errors.APIError.raise_error = _patched_raise_error
    _genai_errors.APIError.raise_error_async = _patched_raise_error_async
except Exception as e:
    import logging; logging.warning(f"Deterministic-5xx fast-fail patch not applied: {e}")

# =============================================================================
# 🔧 MCP Toolset Configuration
# =============================================================================
def get_maps_mcp_url():
    """Returns the base Maps MCP URL."""
    return "https://mapstools.googleapis.com/mcp"

def get_firestore_mcp_url():
    """Returns the base Firestore MCP URL."""
    return "https://firestore.googleapis.com/mcp"

def get_bigquery_mcp_url():
    """Returns the project-scoped BigQuery MCP URL using a query parameter."""
    project_id = get_project_id()
    # Using ?project= query parameter as the header alone was insufficient for public datasets
    return f"https://bigquery.googleapis.com/mcp?project={project_id}"

def get_bigquery_mcp_toolset():
    """Creates a BigQuery MCP toolset. URL is project-scoped to ensure quota/perms."""
    project_id = get_project_id()
    url = get_bigquery_mcp_url()
    if project_id == "UNKNOWN":
        print("  [CRITICAL] GOOGLE_CLOUD_PROJECT is missing! MCP calls will likely fail.")
        
    return McpToolset(connection_params=StreamableHTTPConnectionParams(
        url=url, 
        headers={"x-goog-user-project": project_id},
        timeout=300
    ))

def get_firestore_mcp_toolset():
    """Creates a Firestore MCP toolset (data ops only; DB/index admin excluded
    to reduce the agent's function-declaration count -- admin ops are handled by
    the setup script, never by the runtime agent)."""
    project_id = get_project_id()
    url = get_firestore_mcp_url()
    return McpToolset(connection_params=StreamableHTTPConnectionParams(
        url=url,
        headers={"x-goog-user-project": project_id},
        timeout=300
    ), tool_filter=[
        'get_document', 'add_document', 'update_document', 'delete_document',
        'list_documents', 'list_collections',
    ])

def get_maps_mcp_toolset():
    """Creates a Google Maps MCP toolset."""
    dotenv.load_dotenv()
    maps_api_key = os.getenv('MAPS_API_KEY')
    project_id = get_project_id()
    url = get_maps_mcp_url()
    return McpToolset(connection_params=StreamableHTTPConnectionParams(
        url=url,
        headers={
            "x-goog-api-key": maps_api_key
        },
        timeout=300
    ))

def get_knowledge_catalog_mcp_url():
    """Returns the Knowledge Catalog (Dataplex) remote MCP URL."""
    return "https://dataplex.googleapis.com/mcp"

def get_knowledge_catalog_mcp_toolset():
    """Creates a Knowledge Catalog (Dataplex Universal Catalog) MCP toolset.

    Read-only discovery + metadata retrieval so the agent can find the right
    data assets semantically (search_entries) and understand column meaning,
    classification, and relationships (lookup_entry / lookup_context) before
    composing BigQuery queries. Write tools (create/update_*) are excluded via
    tool_filter to keep the function-declaration count low, mirroring the
    Firestore toolset policy."""
    project_id = get_project_id()
    url = get_knowledge_catalog_mcp_url()
    return McpToolset(connection_params=StreamableHTTPConnectionParams(
        url=url,
        headers={"x-goog-user-project": project_id},
        timeout=300
    ), tool_filter=[
        'search_entries', 'lookup_entry', 'lookup_context',
        'list_data_products', 'list_data_assets',
        'get_data_product', 'get_data_asset',
    ])

# Initialize Firestore client for background task management
# Stored on builtins so tools.py functions can access it without circular imports
# NOTE: This MUST be outside the enableWorkspaceMcp conditional block
# so background task tools work regardless of Workspace MCP configuration.
import builtins
if not hasattr(builtins, '_firestore_client'):
    try:
        from google.cloud import firestore as _firestore_mod
        builtins._firestore_client = _firestore_mod.Client()
        print("[tools.py] Firestore client initialized successfully for background tasks", flush=True)
    except Exception as _fs_init_err:
        builtins._firestore_client = None
        print("[tools.py] FAILED to initialize Firestore client: " + type(_fs_init_err).__name__ + ": " + str(_fs_init_err), flush=True)



# --- Per-demo MCP server configuration (mcp_config.json) ---
# Written by the setup script next to this module: the list of imported MCP
# servers (local + remote) with precomputed ports and safe names, so this
# module stays fully static.
def _load_mcp_config():
    import json as _json
    _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_config.json")
    try:
        with open(_p, encoding="utf-8") as _f:
            return _json.load(_f).get("mcpServers", [])
    except (OSError, ValueError):
        return []

def get_mcp_config():
    """Returns the per-demo imported MCP server list (empty when none)."""
    return _load_mcp_config()

# --- Workspace MCP toolsets (enabled per demo via ENABLE_WORKSPACE_MCP) ---
if os.environ.get("ENABLE_WORKSPACE_MCP") == "1":
    import re
    import httpx
    from pydantic import AnyUrl

    # Thread-safe token holder for Workspace MCP authentication.
    # Uses builtins to share state across module boundaries (tools.py ↔ fast_api_app.py).
    # Updated by TokenExtractionMiddleware (primary) and _handle_request (fallback)
    # with the OAuth token from each A2A request.
    # The header_provider callback reads from this on each MCP HTTP call.
    if not hasattr(builtins, '_workspace_oauth_token'):
        builtins._workspace_oauth_token = ""

    # Try to import MCP OAuth components (available in mcp>=1.24.0)
    try:
        from mcp.client.auth import OAuthClientProvider
        from mcp.shared.auth import OAuthClientMetadata, OAuthToken
        _MCP_OAUTH_AVAILABLE = True
    except ImportError:
        _MCP_OAUTH_AVAILABLE = False
        import logging as _log
        _log.getLogger('workspace_mcp').warning("MCP OAuth imports not available - falling back to header-only auth")

    class WorkspaceTokenStorage:
        """Bridges Gemini Enterprise OAuth tokens into MCP OAuth flow.
    
        When OAuthClientProvider receives a 401 from the MCP server, it uses this
        storage to provide the pre-existing access token. If the token is accepted
        (no 401), the MCP OAuth handshake is skipped entirely.
        """
        def __init__(self, access_token):
            if _MCP_OAUTH_AVAILABLE and access_token:
                self._token = OAuthToken(access_token=access_token, token_type="Bearer")
            else:
                self._token = None
            self._client_info = None
    
        async def get_tokens(self):
            return self._token
    
        async def set_tokens(self, tokens):
            self._token = tokens
    
        async def get_client_info(self):
            return self._client_info
    
        async def set_client_info(self, client_info):
            self._client_info = client_info

    def _create_workspace_httpx_client_factory(mcp_server_url, scopes):
        """Returns the httpx_client_factory that injects OAuthClientProvider.
    
        On Cloud Run:
        - Creates OAuthClientProvider with the Google OAuth token from header_provider
        - OAuthClientProvider first tries to use the token as-is (Bearer header)
        - If MCP server returns 401, OAuthClientProvider handles the full OAuth handshake
    
        On local dev:
        - Falls back to default httpx client factory
        """
        import logging as _log
        _logger = _log.getLogger('workspace_mcp')
    
        def factory(headers=None, timeout=None, auth=None):
            from mcp.shared._httpx_utils import create_mcp_http_client
        
            # Only inject OAuthClientProvider on Cloud Run and when MCP OAuth is available
            if not os.environ.get("K_SERVICE") or not _MCP_OAUTH_AVAILABLE:
                return create_mcp_http_client(headers=headers, timeout=timeout, auth=auth)
        
            # Extract token from headers injected by header_provider
            token = None
            if headers and "Authorization" in headers:
                auth_header = headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                    _logger.warning(f"httpx_factory: Got token from headers (prefix={token[:30]}..., len={len(token)})")
        
            if not token:
                _logger.warning("httpx_factory: No token in headers, using default client")
                return create_mcp_http_client(headers=headers, timeout=timeout, auth=auth)
        
            try:
                # Create OAuthClientProvider with pre-existing token
                storage = WorkspaceTokenStorage(token)
            
                oauth_provider = OAuthClientProvider(
                    server_url=mcp_server_url,
                    client_metadata=OAuthClientMetadata(
                        client_name="Workspace MCP Agent",
                        redirect_uris=[AnyUrl("http://localhost:3000/callback")],
                        grant_types=["authorization_code", "refresh_token"],
                        response_types=["code"],
                        scope=" ".join(scopes),
                    ),
                    storage=storage,
                    redirect_handler=None,   # headless: full flow not possible
                    callback_handler=None,   # headless: full flow not possible
                )
            
                _logger.warning(f"httpx_factory: Created OAuthClientProvider for {mcp_server_url}")
            
                # Remove Authorization from headers since OAuthClientProvider will handle it
                clean_headers = {k: v for k, v in (headers or {}).items() if k != "Authorization"}
            
                return create_mcp_http_client(
                    headers=clean_headers if clean_headers else None,
                    timeout=timeout,
                    auth=oauth_provider
                )
            except Exception as ex:
                _logger.warning(f"httpx_factory: OAuthClientProvider creation failed ({type(ex).__name__}: {ex}), falling back to default client with Bearer header")
                return create_mcp_http_client(headers=headers, timeout=timeout, auth=auth)
    
        return factory

    def _workspace_header_provider(context) -> dict:
        """header_provider callback for McpToolset.
    
        Called by ADK on every MCP HTTP request to supply dynamic auth headers.
        Tries multiple strategies to find the OAuth token:
          1. context.state[auth_id] (ADK ReadonlyContext/CallbackContext)
          2. context.session.state[auth_id] (session-level state)
          3. builtins._workspace_oauth_token (cross-module fallback)
        """
        import logging as _log
        _logger = _log.getLogger('workspace_mcp')
        token = None
    
        auth_id = os.environ.get("GEMINI_AUTHORIZATION_ID", "")
        _logger.warning(f"header_provider: CALLED. auth_id='{auth_id}', context_type={type(context).__name__}")
    
        # Strategy 1: Direct access to context.state (no isinstance check)
        if not token and context and auth_id:
            try:
                state = getattr(context, 'state', None)
                if state is not None:
                    # Try dict-like access directly (works with proxy objects too)
                    t = state.get(auth_id) if hasattr(state, 'get') else None
                    if not t:
                        t = state[auth_id] if auth_id in state else None
                    if t:
                        token = t
                        _logger.warning(f"header_provider: ✅ Strategy1 OK - token from context.state (prefix={token[:30]}..., len={len(token)})")
                    else:
                        _logger.warning(f"header_provider: Strategy1 MISS - context.state exists (type={type(state).__name__}) but auth_id '{auth_id}' not found. keys={list(state.keys()) if hasattr(state, 'keys') else 'N/A'}")
            except Exception as ex:
                _logger.warning(f"header_provider: Strategy1 ERROR - context.state access failed: {type(ex).__name__}: {ex}")
    
        # Strategy 2: Try context.session.state
        if not token and context and auth_id:
            try:
                session = getattr(context, 'session', None)
                if session:
                    session_state = getattr(session, 'state', None)
                    if session_state is not None:
                        t = session_state.get(auth_id) if hasattr(session_state, 'get') else None
                        if not t:
                            t = session_state[auth_id] if auth_id in session_state else None
                        if t:
                            token = t
                            _logger.warning(f"header_provider: ✅ Strategy2 OK - token from context.session.state (prefix={token[:30]}..., len={len(token)})")
            except Exception as ex:
                _logger.warning(f"header_provider: Strategy2 ERROR - context.session.state access failed: {type(ex).__name__}: {ex}")
    
        # Strategy 3: Fallback to builtins
        if not token:
            import builtins
            token = getattr(builtins, '_workspace_oauth_token', '')
            if token:
                _logger.warning(f"header_provider: ✅ Strategy3 OK - token from builtins (prefix={token[:30]}..., len={len(token)})")
    
        if not token:
            _logger.warning("header_provider: ❌ NO TOKEN AVAILABLE - MCP calls will fail with permission denied")
    
        # Token scope verification for debugging - check on first 3 calls per instance
        call_count = getattr(_workspace_header_provider, '_call_count', 0) + 1
        _workspace_header_provider._call_count = call_count
        if token and call_count <= 3:
            try:
                import httpx
                resp = httpx.get(f"https://oauth2.googleapis.com/tokeninfo?access_token={token}", timeout=5)
                if resp.status_code == 200:
                    info = resp.json()
                    _logger.warning(f"header_provider: 🔍 TOKEN SCOPES: {info.get('scope', 'N/A')}")
                    _logger.warning(f"header_provider: 🔍 TOKEN EMAIL: {info.get('email', 'N/A')}, EXPIRES_IN: {info.get('expires_in', 'N/A')}")
                else:
                    _logger.warning(f"header_provider: 🔍 TOKEN INFO FAILED: status={resp.status_code}, body={resp.text[:200]}")
            except Exception as ex:
                _logger.warning(f"header_provider: 🔍 TOKEN INFO ERROR: {type(ex).__name__}: {ex}")
    
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    # Workspace MCP scope definitions (shared between factory and auth_kwargs)
    _GMAIL_SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.modify",
    ]
    _DRIVE_SCOPES = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/drive.file",
    ]
    _CALENDAR_SCOPES = [
        "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
        "https://www.googleapis.com/auth/calendar.events.freebusy",
        "https://www.googleapis.com/auth/calendar.events.readonly",
        "https://www.googleapis.com/auth/calendar.events",
    ]
    _PEOPLE_SCOPES = [
        "https://www.googleapis.com/auth/directory.readonly",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/contacts.readonly",
    ]
    _CHAT_SCOPES = [
        "https://www.googleapis.com/auth/chat.spaces.readonly",
        "https://www.googleapis.com/auth/chat.memberships.readonly",
        "https://www.googleapis.com/auth/chat.messages.readonly",
        "https://www.googleapis.com/auth/chat.messages.create",
        "https://www.googleapis.com/auth/chat.users.readstate.readonly",
    ]
    _ALL_WORKSPACE_SCOPES = _GMAIL_SCOPES + _DRIVE_SCOPES + _CALENDAR_SCOPES + _PEOPLE_SCOPES + _CHAT_SCOPES

    def _get_workspace_auth_kwargs() -> dict:
        """Returns auth_scheme/auth_credential kwargs for MCP OAuth authentication.
    
        On Cloud Run (K_SERVICE set), we MUST NOT pass auth_scheme/auth_credential
        because the A2A executor does not handle adk_request_credential events.
        Authentication is handled by httpx_client_factory + OAuthClientProvider.
    
        For local development (ADK Web UI), auth_scheme/auth_credential enables
        the interactive OAuth consent flow.
        """
        if os.environ.get("K_SERVICE"):
            return {}
        return {
            "auth_scheme": OAuth2(
                flows=OAuthFlows(
                    authorizationCode=OAuthFlowAuthorizationCode(
                        authorizationUrl="https://accounts.google.com/o/oauth2/auth?access_type=offline&prompt=consent",
                        tokenUrl="https://oauth2.googleapis.com/token",
                        scopes={s: s.split('/')[-1] for s in _ALL_WORKSPACE_SCOPES},
                    )
                )
            ),
            "auth_credential": AuthCredential(
                auth_type=AuthCredentialTypes.OAUTH2,
                oauth2=OAuth2Auth(
                    client_id=os.environ.get("OAUTH_CLIENT_ID", ""),
                    client_secret=os.environ.get("OAUTH_CLIENT_SECRET", ""),
                ),
            ),
        }

    def get_gmail_mcp_toolset():
        """Creates a Gmail MCP toolset with MCP OAuth support."""
        url = "https://gmailmcp.googleapis.com/mcp/v1"
        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=url,
                timeout=300,
                httpx_client_factory=_create_workspace_httpx_client_factory(url, _GMAIL_SCOPES),
            ),
            header_provider=_workspace_header_provider,
            tool_filter=['create_draft', 'create_label', 'update_label', 'delete_label', 'get_thread', 'label_message', 'label_thread', 'list_drafts', 'list_labels', 'search_threads', 'unlabel_message', 'unlabel_thread'],
            **_get_workspace_auth_kwargs()
        )

    def get_drive_mcp_toolset():
        """Creates a Google Drive MCP toolset with MCP OAuth support."""
        url = "https://drivemcp.googleapis.com/mcp/v1"
        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=url,
                timeout=300,
                httpx_client_factory=_create_workspace_httpx_client_factory(url, _DRIVE_SCOPES),
            ),
            header_provider=_workspace_header_provider,
            tool_filter=['create_file', 'copy_file', 'download_file_content', 'get_file_metadata', 'get_file_permissions', 'list_recent_files', 'read_file_content', 'search_files'],
            **_get_workspace_auth_kwargs()
        )

    def get_calendar_mcp_toolset():
        """Creates a Google Calendar MCP toolset with MCP OAuth support."""
        url = "https://calendarmcp.googleapis.com/mcp/v1"
        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=url,
                timeout=300,
                httpx_client_factory=_create_workspace_httpx_client_factory(url, _CALENDAR_SCOPES),
            ),
            header_provider=_workspace_header_provider,
            tool_filter=['create_event', 'delete_event', 'get_event', 'list_calendars', 'list_events', 'respond_to_event', 'suggest_time', 'update_event'],
            **_get_workspace_auth_kwargs()
        )

    def get_chat_mcp_toolset():
        """Creates a Google Chat MCP toolset.

        NOTE: 'search_messages' is intentionally excluded from tool_filter. Its input
        schema uses $defs/$ref (nested SearchParameters), which the ADK->Gemini
        function-declaration conversion expands into duplicate declarations, causing
        'Duplicate function declaration' errors. The remaining tools use flat schemas.
        Requires Chat app configuration (see setup script guidance).
        """
        url = "https://chatmcp.googleapis.com/mcp/v1"
        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=url,
                timeout=300,
                httpx_client_factory=_create_workspace_httpx_client_factory(url, _CHAT_SCOPES),
            ),
            header_provider=_workspace_header_provider,
            tool_filter=['list_messages', 'search_conversations', 'send_message'],
            **_get_workspace_auth_kwargs()
        )

    def get_people_mcp_toolset():
        """Creates a People API MCP toolset with MCP OAuth support."""
        url = "https://people.googleapis.com/mcp/v1"
        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=url,
                timeout=300,
                httpx_client_factory=_create_workspace_httpx_client_factory(url, _PEOPLE_SCOPES),
            ),
            header_provider=_workspace_header_provider,
            tool_filter=['search_directory_people', 'search_contacts', 'get_user_profile'],
            **_get_workspace_auth_kwargs()
        )

else:
    def get_gmail_mcp_toolset(): return None
    def get_drive_mcp_toolset(): return None
    def get_calendar_mcp_toolset(): return None
    def get_chat_mcp_toolset(): return None
    def get_people_mcp_toolset(): return None

async def generate_image(prompt: str, tool_context: ToolContext) -> dict:
    """Generates a professional business image or presentation slide based on the given prompt.
    
    This tool creates visual assets like infographics, charts, or slides. It automatically 
    stores the image in the current environment's artifact service to be rendered in the chat.
    
    Args:
        prompt: A highly detailed, descriptive prompt for the image. Include stylistic instructions (e.g., 'photorealistic', 'flat design').
                CRITICAL: The prompt text MUST be written in the EXACT SAME language that the user is using in the current chat session.
                If the conversation is in Japanese, you MUST write the entire prompt in Japanese (e.g., '武田電気株式会社の見積状況をまとめたスライド...').
                This ensures all text inside the generated image is rendered in the user's language.
        
    Returns:
        A dictionary with status and detail keys.
    """
    filename = f"image_{uuid.uuid4().hex[:8]}.jpeg"
    
    import os
    import logging
    import re
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    
    logging.info(f"generate_image called with prompt: {prompt}")
    logging.info(f"Using location: {location}, project: {project}")
    
    # 1. Automatic language detection on the prompt text (Detect Japanese characters)
    is_japanese = bool(re.search(r'[぀-ゟ゠-ヿ一-龯]', prompt))
    
    # 2. Construct robust system-level style and language guidelines based on detected language
    base_style_rule = "\n\nCRITICAL STYLE RULE: NEVER include headers, watermarks, logos, or any text reading 'Consulting Firm' in the generated image."
    
    if is_japanese:
        # Heavy reinforcement for Japanese rendering (Forces Imagen 3 to use Japanese fonts and text labels exclusively)
        lang_rule = (
            "\n\nCRITICAL LANGUAGE RULE: ALL text elements inside the generated image "
            "(including presentation titles, headers, table labels, chart legends, data points, bullet points, annotations, and company names) "
            "MUST be rendered EXCLUSIVELY in Japanese. Do NOT use any English or Latin characters. "
            "For example, render company names as '武田電気株式会社' (not Takeden Co), "
            "and use Japanese for headers like 'エグゼクティブサマリー' or '保留中の見積処理状況'. "
            "This is a strict requirement."
        )
    else:
        lang_rule = (
            "\n\nCRITICAL LANGUAGE RULE: ALL text elements inside the generated image "
            "(including titles, labels, axis names, legends, bullet points, annotations, captions) "
            "MUST be rendered in the SAME language as the prompt text above. Do NOT mix languages."
        )
        
    final_prompt = prompt + base_style_rule + lang_rule
    
    client = genai_client.Client(
        vertexai=True, 
        location=location, 
        project=project,
        http_options={'api_version': 'v1'}
    )
    from google.genai import types
    
    try:
        logging.info("Calling Gemini API for image generation...")
        # Generate image via the GenerateContent API
        result = await asyncio.to_thread(
            client.models.generate_content,
            model='gemini-3.1-flash-image',
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=final_prompt)]
                )
            ],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio="16:9",
                    output_mime_type="image/jpeg",
                )
            )
        )
        logging.info("Gemini API call returned.")
    except Exception as e:
        logging.error(f"API Error generating image: {e}", exc_info=True)
        return {'status': 'error', 'detail': f'API Error generating image: {str(e)}'}
    
    if not result.candidates or not result.candidates[0].content.parts:
        logging.warning(f"Failed to generate image for prompt: {prompt}. No candidates or parts.")
        return {'status': 'error', 'detail': f'Failed to generate image for prompt: {prompt}'}
        
    image_bytes = None
    for part in result.candidates[0].content.parts:
        if part.inline_data:
            image_bytes = part.inline_data.data
            break
            
    if not image_bytes:
        logging.warning(f"No image bytes found in the response for prompt: {prompt}")
        return {'status': 'error', 'detail': f'No image bytes found in the response for prompt: {prompt}'}
    
    # Store the image bytes in the session state so the callback can pick it up later
    tool_context.session.state['pending_generated_image'] = image_bytes
    
    return {
        'status': 'success',
        'detail': 'Image generated successfully. It will be attached to your final response automatically.',
    }


# =====================================================================
# Interactive HTML Dashboard publisher.
# The model authors a complete, self-contained interactive HTML dashboard
# (inline CSS/JS, chart lib from CDN, data embedded as a JSON literal) built
# from the demo's data. This tool uploads it to a NON-PUBLIC GCS bucket and
# returns a time-limited V4 signed URL that the agent surfaces as a Markdown
# link. The dashboard is a point-in-time snapshot (a signed static object
# cannot run server-side queries).
# =====================================================================
def _get_runtime_sa_email():
    """Resolve the runtime service account email (env first, metadata fallback)."""
    email = os.environ.get("RUNTIME_SA_EMAIL", "").strip()
    if email:
        return email
    try:
        import requests
        resp = requests.get(
            "http://metadata.google.internal/computeMetadata/v1/"
            "instance/service-accounts/default/email",
            headers={"Metadata-Flavor": "Google"},
            timeout=5.0,
        )
        if resp.status_code == 200:
            return resp.text.strip()
    except Exception:
        pass
    return ""


def _generate_v4_signed_url(bucket_name, object_name, content_type, expiration_days=7):
    """Mint a V4 signed GET URL using ADC + IAM signBlob (no key file on Cloud Run).

    Passing service_account_email + access_token makes the storage client sign
    remotely via the IAM signBlob API, which requires the runtime SA to hold
    roles/iam.serviceAccountTokenCreator on itself.
    """
    from google.cloud import storage
    from datetime import timedelta
    import google.auth
    import google.auth.transport.requests
    import requests as _requests

    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    creds, _ = google.auth.default(scopes=scopes)

    # Refresh with a bounded-timeout session so a slow metadata endpoint cannot
    # deadlock the event loop on a Cloud Run cold start.
    class _TimeoutSession(_requests.Session):
        def request(self, *a, **k):
            k.setdefault("timeout", 10.0)
            return super().request(*a, **k)

    creds.refresh(google.auth.transport.requests.Request(session=_TimeoutSession()))

    sa_email = _get_runtime_sa_email()
    if not sa_email:
        raise RuntimeError("Could not resolve the runtime service account email for signing")

    client = storage.Client(credentials=creds)
    blob = client.bucket(bucket_name).blob(object_name)
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(days=min(expiration_days, 7)),  # V4 hard max is 7 days
        method="GET",
        service_account_email=sa_email,
        access_token=creds.token,
        response_type=content_type,
    )


async def publish_dashboard(html: str, title: str, tool_context: ToolContext) -> dict:
    """Publishes a complete, interactive HTML dashboard and returns a shareable link.

    Use this when the user asks for an interactive dashboard, an executive
    dashboard, a clickable/visual report, or "something I can open in the browser".
    You author the ENTIRE dashboard yourself and pass it as one self-contained HTML
    document. The dashboard is a point-in-time SNAPSHOT of the data you embed -- it
    is NOT live -- so fetch the numbers first (e.g. via execute_sql) and embed them.

    Requirements for the html argument:
      - A single, self-contained HTML document (<!DOCTYPE html> ... </html>).
      - Inline ALL CSS and JavaScript. Do NOT reference local files.
      - Load chart libraries from a CDN (e.g. https://cdn.jsdelivr.net/npm/chart.js).
      - Embed the data directly in the page as a JSON literal (const DATA = {...};).
      - Make it interactive. The page MUST include ALL of:
          * a data table with click-to-sort columns (asc/desc toggle),
          * a free-text search box that live-filters the table rows,
          * category filter controls (dropdowns / toggle chips) for key dimensions,
          * tabbed sections (e.g. Overview / Details) via pure-JS show/hide,
          * charts with hover tooltips,
          * a light/dark mode toggle.
      - Chart sizing: wrap every <canvas> in a fixed-height container (e.g.
        height:320px) and set Chart.js maintainAspectRatio:false + responsive:true,
        so charts never grow to fill the page. Constrain overall page width with a
        centered max-width wrapper and responsive grids so the layout fits the screen.
      - Theming: drive ALL colors from CSS variables (light on :root, dark under
        html[data-theme='dark']); every surface reads bg+text from them. Do NOT
        hardcode colors on individual elements, or the other theme becomes unreadable.
        Ensure strong contrast in BOTH modes.
      - Write ALL visible text in the SAME language the user is using in the chat.
      - State on the page that the data is a point-in-time snapshot, not live.

    Args:
        html: The full self-contained HTML document for the dashboard.
        title: A short human-readable dashboard title (used for logging/labels).

    Returns:
        A dictionary with keys: status, detail, dashboard_url.
    """
    import uuid as _uuid
    import logging as _logging
    bucket = os.environ.get("DASHBOARDS_BUCKET", "").strip()
    if not bucket:
        return {'status': 'error',
                'detail': 'Dashboard hosting is not configured (DASHBOARDS_BUCKET missing).',
                'dashboard_url': ''}
    if not html or "<" not in html:
        return {'status': 'error',
                'detail': 'The html argument must be a complete, self-contained HTML document.',
                'dashboard_url': ''}
    object_name = f"dashboards/dash_{_uuid.uuid4().hex}.html"
    _ct = "text/html; charset=utf-8"

    def _upload_and_sign():
        from google.cloud import storage
        client = storage.Client()
        blob = client.bucket(bucket).blob(object_name)
        blob.upload_from_string(html, content_type=_ct)
        return _generate_v4_signed_url(bucket, object_name, _ct)

    try:
        url = await asyncio.to_thread(_upload_and_sign)
        # Never log the full signed URL: the query-string token grants read access.
        _logging.info("publish_dashboard: uploaded %s and minted a signed URL.", object_name)
        return {
            'status': 'success',
            'detail': 'Dashboard published. Present dashboard_url to the user as a Markdown '
                      'link like [Open Executive Dashboard](URL). Do not print the raw URL.',
            'dashboard_url': url,
        }
    except Exception as e:
        _logging.error(f"publish_dashboard failed: {e}", exc_info=True)
        return {'status': 'error', 'detail': f'Failed to publish dashboard: {str(e)}',
                'dashboard_url': ''}


# --- Computer Use browser agent (enabled per demo via ENABLE_COMPUTER_USE) ---
if os.environ.get("ENABLE_COMPUTER_USE") == "1":
    # =====================================================================
    # Computer Use (browser agent) -- Gemini built-in computer_use tool
    # (dedicated computer-use model) driven over a self-hosted headless
    # Chromium (Playwright). Adapted
    # from the official reference impl (github.com/google-gemini/
    # computer-use-preview, Apache-2.0): same generate_content loop, action
    # dispatch, coordinate denormalization and keep-last-N screenshot trim.
    # Runs inside a background task (the loop routinely exceeds the inline
    # rendering deadline). Screenshots are published to Firestore for the
    # live-view page and stashed for the in-chat filmstrip.
    # =====================================================================
    _CU_VIEWPORT_W = 1440
    _CU_VIEWPORT_H = 900
    _CU_MAX_STEPS = 40
    _CU_KEEP_SHOTS = 3
    _CU_STEP_TIMEOUT_MS = 15000
    _CU_MAX_CHAT_SHOTS = 6

    _CU_KEY_MAP = {
        "enter": "Enter", "return": "Enter", "tab": "Tab", "backspace": "Backspace",
        "delete": "Delete", "escape": "Escape", "esc": "Escape", "space": "Space",
        "up": "ArrowUp", "down": "ArrowDown", "left": "ArrowLeft", "right": "ArrowRight",
        "pageup": "PageUp", "pagedown": "PageDown", "home": "Home", "end": "End",
        "ctrl": "Control", "control": "Control", "alt": "Alt", "shift": "Shift",
        "meta": "Meta", "cmd": "Meta", "command": "Meta",
    }

    def _cu_denorm(v, size):
        try:
            return int(round((float(v) / 1000.0) * float(size)))
        except Exception:
            return 0

    def _cu_now_iso():
        import datetime as _dt
        return _dt.datetime.now(_dt.timezone.utc).isoformat()

    def _cu_session_doc(session_id):
        import builtins
        _fs = getattr(builtins, '_firestore_client', None)
        _demo_id = os.environ.get("DEMO_ID", "")
        if not _fs or not _demo_id:
            return None
        return _fs.collection(_demo_id + "_browser_sessions").document(session_id)

    async def _cu_publish(session_id, step, intent, url, status, shot_b64):
        _ref = _cu_session_doc(session_id)
        if _ref is None:
            return
        _doc = {
            "session_id": session_id, "step": step, "intent": intent or "",
            "url": url or "", "status": status, "updated_at": _cu_now_iso(),
        }
        if shot_b64 is not None:
            _doc["screenshot_b64"] = shot_b64
        try:
            await asyncio.to_thread(_ref.set, _doc, merge=True)
        except Exception:
            pass

    async def _cu_await_confirmation(session_id, action_text, category, shot_b64):
        # Human-in-the-loop: record a pending confirmation, then poll the same
        # doc for the decision the user makes on the live-view page. Returns True
        # only on explicit approval; anything else (reject/timeout/no backend) is
        # treated as not approved so irreversible actions never run unattended.
        _ref = _cu_session_doc(session_id)
        if _ref is None:
            return False
        try:
            _payload = {
                "session_id": session_id, "status": "awaiting_confirmation",
                "confirm_action": action_text or "", "confirm_category": category or "",
                "confirm_decision": "", "updated_at": _cu_now_iso(),
            }
            if shot_b64 is not None:
                _payload["screenshot_b64"] = shot_b64
            await asyncio.to_thread(_ref.set, _payload, merge=True)
        except Exception:
            return False
        for _i in range(150):
            await asyncio.sleep(2)
            try:
                _snap = await asyncio.to_thread(_ref.get)
                _d = _snap.to_dict() if (_snap and _snap.exists) else {}
            except Exception:
                _d = {}
            _dec = (_d or {}).get("confirm_decision", "")
            if _dec == "approved":
                try:
                    await asyncio.to_thread(_ref.set, {"status": "working", "confirm_decision": ""}, merge=True)
                except Exception:
                    pass
                return True
            if _dec == "rejected":
                return False
        return False

    def _cu_extract(candidate):
        _fcs = []
        _txt = []
        try:
            for _p in (candidate.content.parts or []):
                if getattr(_p, "function_call", None):
                    _fcs.append(_p.function_call)
                elif getattr(_p, "text", None) and not getattr(_p, "thought", False):
                    _txt.append(_p.text)
        except Exception:
            pass
        return _fcs, (" ".join(_txt)).strip()

    def _cu_trim(history):
        # Keep only the most recent _CU_KEEP_SHOTS screenshot turns to bound tokens.
        _seen = 0
        for _c in reversed(history):
            try:
                if getattr(_c, "role", "") == "user" and _c.parts and any(getattr(_p, "function_response", None) for _p in _c.parts):
                    _seen += 1
                    if _seen > _CU_KEEP_SHOTS:
                        for _p in _c.parts:
                            if getattr(_p, "function_response", None):
                                _p.function_response.parts = None
            except Exception:
                pass

    async def _cu_dispatch(page, name, args):
        # Execute a single computer-use action, returning the resulting page URL.
        # Handles both the 3.5 and legacy 2.5 predefined-function naming and common
        # argument key variants, since the exact schema varies by model version.
        n = (name or "").lower()

        def _num(*keys):
            for _k in keys:
                if _k in args and args[_k] is not None:
                    try:
                        return float(args[_k])
                    except Exception:
                        pass
            return None

        def _xy():
            _cx = _num("x", "x_coordinate", "start_x")
            _cy = _num("y", "y_coordinate", "start_y")
            if _cx is None and "coordinate" in args:
                try:
                    _c = args["coordinate"]
                    _cx = float(_c[0])
                    _cy = float(_c[1])
                except Exception:
                    pass
            if _cx is None or _cy is None:
                return (None, None)
            return (_cu_denorm(_cx, _CU_VIEWPORT_W), _cu_denorm(_cy, _CU_VIEWPORT_H))

        try:
            if "go_back" in n:
                await page.go_back()
            elif "go_forward" in n:
                await page.go_forward()
            elif "navigate" in n or n in ("open_web_browser", "open_url", "goto"):
                _url = args.get("url") or args.get("website") or ""
                if _url:
                    if "://" not in _url:
                        _url = "https://" + _url
                    await page.goto(_url, wait_until="load", timeout=_CU_STEP_TIMEOUT_MS)
            elif n == "search":
                # DuckDuckGo's HTML endpoint is automation-friendly (no CAPTCHA / bot wall,
                # unlike google.com), so searches land straight on parseable results.
                _q = args.get("query") or args.get("text") or ""
                await page.goto("https://duckduckgo.com/html/?q=" + str(_q).replace(" ", "+"), timeout=_CU_STEP_TIMEOUT_MS)
            elif "scroll" in n:
                _x, _y = _xy()
                _dir = str(args.get("direction") or "down").lower()
                _mag = _num("magnitude", "scroll_amount", "distance", "scroll_y")
                _amt = int(_mag) if _mag else int(_CU_VIEWPORT_H * 0.8)
                if _dir in ("up", "left"):
                    _amt = -abs(_amt)
                if _x is not None:
                    await page.mouse.move(_x, _y)
                if _dir in ("left", "right"):
                    await page.mouse.wheel(_amt, 0)
                else:
                    await page.mouse.wheel(0, _amt)
            elif "drag" in n:
                _x, _y = _xy()
                _dx = _num("destination_x", "x2", "end_x")
                _dy = _num("destination_y", "y2", "end_y")
                if _x is not None and _dx is not None:
                    await page.mouse.move(_x, _y)
                    await page.mouse.down()
                    await page.mouse.move(_cu_denorm(_dx, _CU_VIEWPORT_W), _cu_denorm(_dy, _CU_VIEWPORT_H))
                    await page.mouse.up()
            elif "hover" in n or n in ("move", "mouse_move"):
                _x, _y = _xy()
                if _x is not None:
                    await page.mouse.move(_x, _y)
            elif "double_click" in n:
                _x, _y = _xy()
                if _x is not None:
                    await page.mouse.click(_x, _y, click_count=2)
            elif "triple_click" in n:
                _x, _y = _xy()
                if _x is not None:
                    await page.mouse.click(_x, _y, click_count=3)
            elif "right_click" in n:
                _x, _y = _xy()
                if _x is not None:
                    await page.mouse.click(_x, _y, button="right")
            elif "middle_click" in n:
                _x, _y = _xy()
                if _x is not None:
                    await page.mouse.click(_x, _y, button="middle")
            elif "click" in n:
                _x, _y = _xy()
                if _x is not None:
                    await page.mouse.click(_x, _y)
            elif "type" in n:
                _x, _y = _xy()
                if _x is not None:
                    await page.mouse.click(_x, _y)
                    if args.get("clear_before_typing") or args.get("clear"):
                        await page.keyboard.press("Control+A")
                        await page.keyboard.press("Delete")
                _txt = args.get("text") or args.get("value") or ""
                await page.keyboard.type(str(_txt))
                if args.get("press_enter") or args.get("enter"):
                    await page.keyboard.press("Enter")
            elif "key" in n or "hotkey" in n:
                _keys = args.get("keys") or args.get("key") or args.get("key_combination") or args.get("text") or ""
                _seq = _keys if isinstance(_keys, list) else str(_keys).replace("+", " ").split()
                _mapped = [_CU_KEY_MAP.get(str(_k).lower(), str(_k)) for _k in _seq]
                if len(_mapped) > 1:
                    await page.keyboard.press("+".join(_mapped))
                elif _mapped:
                    await page.keyboard.press(_mapped[0])
            elif "wait" in n:
                await asyncio.sleep(1.0)
            else:
                pass
        except Exception:
            pass

        try:
            await page.wait_for_load_state(timeout=5000)
        except Exception:
            pass
        try:
            return page.url
        except Exception:
            return ""

    async def start_browser_session() -> dict:
        """Reserve a browser live-view session BEFORE running computer_use_browse.

        Call this FIRST for an inline browser task so you can show the user a clickable
        live-view link WHILE the browser runs (computer_use_browse blocks until it finishes,
        so the link must be shown before you call it). Returns instantly (no browser launch).

        After calling this: if it returns a non-empty live_view_url, show it to the user as a
        Markdown link, then call computer_use_browse(..., session_id=<the returned session_id>)
        so the live view matches the actual browser session.

        Returns:
            dict with session_id and live_view_url (live_view_url is empty when no Data Viewer
            is deployed - in that case just call computer_use_browse directly).
        """
        _sid = uuid.uuid4().hex[:12]
        _viewer = os.environ.get("DATA_VIEWER_URL", "")
        _live = (_viewer.rstrip("/") + "/browser-view?session=" + _sid) if _viewer else ""
        try:
            await _cu_publish(_sid, 0, "Preparing browser session...", "", "starting", None)
        except Exception:
            pass
        return {"session_id": _sid, "live_view_url": _live}

    async def computer_use_browse(goal: str, start_url: str, tool_context: ToolContext, session_id: str = "") -> dict:
        """Autonomously operates a real web browser to accomplish a goal on sites that have no API.

        Uses Gemini's built-in Computer Use capability over a headless Chromium browser: it
        looks at a screenshot, decides a UI action (click/type/navigate/scroll), executes it,
        and repeats until the goal is met. Ideal for legacy portals, competitor public pages,
        government/regulatory sites, and internal web apps that expose no API/MCP.

        Can be called inline (short, capped) or from a background task for longer jobs.

        Args:
            goal: Natural-language description of what to accomplish. Be specific about what
                  information to extract or what actions to take.
            start_url: The URL to open first. For a web search, pass a DuckDuckGo results URL
                  like 'https://duckduckgo.com/html/?q=<terms>' (avoid google.com - it CAPTCHAs
                  automated browsers), or a direct source URL. Defaults to a search page.
            session_id: OPTIONAL. Pass the session_id returned by start_browser_session so the
                  live-view link you already showed the user matches this run. Leave empty to
                  auto-assign (background tasks derive it from the task id automatically).

        Returns:
            dict with status, steps_taken, live_view_url, session_id, and result_summary.
        """
        import base64
        import logging
        from google.genai import types
        _log = logging.getLogger("computer_use")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        # Session id precedence: explicit arg (inline 2-step live view) > background task id
        # (worker session is named "task-<task_id>") > random. This keeps the live-view URL
        # consistent with whatever link was already shown to the user.
        _sid_ctx = ""
        try:
            _sid_ctx = getattr(getattr(tool_context, "session", None), "id", "") or ""
        except Exception:
            _sid_ctx = ""
        _is_inline = not _sid_ctx.startswith("task-")
        if session_id and session_id.strip():
            session_id = session_id.strip()
        elif _sid_ctx.startswith("task-"):
            session_id = _sid_ctx[len("task-"):]
        else:
            session_id = uuid.uuid4().hex[:12]
        _viewer = os.environ.get("DATA_VIEWER_URL", "")
        live_view_url = (_viewer.rstrip("/") + "/browser-view?session=" + session_id) if _viewer else ""

        try:
            from playwright.async_api import async_playwright
        except Exception as _imp:
            return {"status": "error", "detail": "Playwright is not installed in this environment: " + str(_imp)}

        client = genai_client.Client(vertexai=True, location=location, project=project)
        # Computer Use requires the dedicated computer-use model unless the
        # project is allowlisted for the tool on general models; reusing
        # AGENT_MODEL fails with 400 "computer use is not supported for this
        # model in this region" in non-allowlisted projects.
        model = os.environ.get("COMPUTER_USE_MODEL", "gemini-2.5-computer-use-preview-10-2025")
        cfg = types.GenerateContentConfig(
            temperature=1.0, top_p=0.95, top_k=40, max_output_tokens=8192,
            tools=[types.Tool(computer_use=types.ComputerUse(environment=types.Environment.ENVIRONMENT_BROWSER))],
        )

        # Inline calls must finish inside GE's chat render window, so cap steps and
        # wall-clock tightly; background calls (via a task) can run much longer.
        import time as _time
        _max_steps = 20 if _is_inline else _CU_MAX_STEPS
        _wall_budget = 240.0 if _is_inline else 600.0
        _deadline = _time.monotonic() + _wall_budget

        _shots_for_chat = []
        _steps = 0
        _final = ""
        _status = "completed"
        _pw = None
        _browser = None
        try:
            _pw = await async_playwright().start()
            _browser = await _pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-extensions", "--disable-plugins",
                      "--disable-blink-features=AutomationControlled"],
            )
            # Look like a normal desktop Chrome (headless UA + navigator.webdriver are the
            # biggest bot-detection giveaways that trigger CAPTCHAs).
            _ctx = await _browser.new_context(
                viewport={"width": _CU_VIEWPORT_W, "height": _CU_VIEWPORT_H},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page = await _ctx.new_page()

            _start = start_url or "https://duckduckgo.com/"
            if "://" not in _start:
                _start = "https://" + _start
            try:
                await page.goto(_start, wait_until="load", timeout=_CU_STEP_TIMEOUT_MS)
            except Exception:
                pass

            _shot = await page.screenshot(type="png")
            _jpg = await page.screenshot(type="jpeg", quality=60)
            await _cu_publish(session_id, 0, "Opened " + _start, page.url, "working", base64.b64encode(_jpg).decode("ascii"))
            history = [types.Content(role="user", parts=[
                types.Part.from_text(text="Goal: " + (goal or "") + chr(10) + "Complete this task in the browser. When finished, summarize what you found or did."),
                types.Part.from_bytes(data=_shot, mime_type="image/png"),
            ])]

            while _steps < _max_steps and _time.monotonic() < _deadline:
                try:
                    _resp = await asyncio.to_thread(client.models.generate_content, model=model, contents=history, config=cfg)
                except Exception as _ge:
                    _final = "Model call failed: " + str(_ge)[:300]
                    _status = "failed"
                    break
                if not _resp.candidates:
                    _final = "The model returned no response."
                    _status = "failed"
                    break
                _cand = _resp.candidates[0]
                history.append(_cand.content)
                _fcs, _reason = _cu_extract(_cand)
                if not _fcs:
                    _final = _reason or "Task complete."
                    break
                _fr_parts = []
                _abort = False
                for _fc in _fcs:
                    _a = dict(_fc.args) if _fc.args else {}
                    _extra = {}
                    _safety = _a.get("safety_decision")
                    _sdec = _safety.get("decision") if hasattr(_safety, "get") else None
                    if _sdec == "require_confirmation":
                        _pre = base64.b64encode(await page.screenshot(type="jpeg", quality=60)).decode("ascii")
                        try:
                            _act = _safety.get("explanation") or _safety.get("action") or _fc.name
                            _cat = _safety.get("category") or ""
                        except Exception:
                            _act = _fc.name
                            _cat = ""
                        _ok = await _cu_await_confirmation(session_id, str(_act), str(_cat), _pre)
                        if not _ok:
                            _final = "A browser action required user confirmation and was not approved: " + str(_act)
                            _status = "cancelled"
                            _abort = True
                            break
                        _extra["safety_acknowledgement"] = "true"
                    _url = await _cu_dispatch(page, _fc.name, _a)
                    _steps += 1
                    _shot = await page.screenshot(type="png")
                    # JPEG copy for the viewer + in-chat filmstrip (small enough for the
                    # Firestore 1MB doc limit and light in the chat artifact).
                    _jpg = await page.screenshot(type="jpeg", quality=60)
                    await _cu_publish(session_id, _steps, (_reason or _fc.name)[:200], _url, "working", base64.b64encode(_jpg).decode("ascii"))
                    _shots_for_chat.append(_jpg)
                    if len(_shots_for_chat) > _CU_MAX_CHAT_SHOTS:
                        del _shots_for_chat[1]  # keep the first frame + the most recent ones
                    _resp_dict = {"url": _url}
                    _resp_dict.update(_extra)
                    _fr_parts.append(types.Part(function_response=types.FunctionResponse(
                        name=_fc.name,
                        response=_resp_dict,
                        parts=[types.FunctionResponsePart(inline_data=types.FunctionResponseBlob(mime_type="image/png", data=_shot))],
                    )))
                if _abort:
                    break
                history.append(types.Content(role="user", parts=_fr_parts))
                _cu_trim(history)

            if not _final and (_steps >= _max_steps or _time.monotonic() >= _deadline):
                _final = ("Reached the browser step/time limit at " + str(_steps) + " steps. "
                          + ("For deeper browsing, ask to run this as a background task." if _is_inline else "Partial progress may have been made."))
                _status = "partial"
        except Exception as _e:
            _final = "Browser session error: " + str(_e)[:300]
            _status = "failed"
        finally:
            try:
                if _browser:
                    await _browser.close()
            except Exception:
                pass
            try:
                if _pw:
                    await _pw.stop()
            except Exception:
                pass

        try:
            _lastb64 = base64.b64encode(_shots_for_chat[-1]).decode("ascii") if _shots_for_chat else None
        except Exception:
            _lastb64 = None
        await _cu_publish(session_id, _steps, _final[:200], "", _status, _lastb64)

        if _shots_for_chat:
            tool_context.session.state['pending_browser_screenshots'] = _shots_for_chat

        return {
            "status": _status,
            "steps_taken": _steps,
            "live_view_url": live_view_url,
            "session_id": session_id,
            "result_summary": _final,
            "detail": "Browser automation finished (status: " + _status + "). Screenshots are attached; the full session can be watched at live_view_url.",
        }

else:
    async def start_browser_session() -> dict:
        return {"status": "error", "detail": "Computer Use is not enabled for this demo.", "live_view_url": ""}
    async def computer_use_browse(goal: str, start_url: str, tool_context: ToolContext = None, session_id: str = "") -> dict:
        return {"status": "error", "detail": "Computer Use is not enabled for this demo."}

def get_custom_mcp_toolsets():

    """Returns a list of McpToolset objects for all imported custom MCP servers."""
    import logging, os, re
    os.environ["FASTMCP_SHOW_SERVER_BANNER"] = "false"
    os.environ["FASTMCP_CHECK_FOR_UPDATES"] = "off"
    toolsets = []
    mcp_configs = [
        {"idx": m.get("local_idx", 0), "port": m.get("port", 9090), "entrypoint": m.get("entrypoint", ""),
         "required_keys": m.get("required_keys", ""), "name": m.get("safe_name") or ("mcp" + str(m.get("local_idx", 0)))}
        for m in get_mcp_config() if m.get("type") != "remote"
    ]
    if not mcp_configs:
        return []
    for cfg in mcp_configs:
        idx, port, entrypoint = cfg["idx"], cfg["port"], cfg["entrypoint"]
        prefix = cfg.get("name", f"mcp{idx}")
        label = f"MCP #{idx + 1} ({prefix})"
        try:
            logging.warning(f"U0001f50c [CUSTOM_MCP] Initializing {label}...")
            _rk = [v.strip() for v in cfg["required_keys"].split(",") if v.strip()]
            _missing = [k for k in _rk if not os.environ.get(k) or os.environ.get(k) == "UNDEFINED"]
            if _missing:
                logging.warning(f"⚠️ [CUSTOM_MCP] {label}: Missing env vars: {_missing}. Skipping.")
                continue
            if os.environ.get("K_SERVICE"):
                from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
                from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
                logging.warning(f"U0001f50c [CUSTOM_MCP] {label}: StreamableHTTP on port {port}")
                toolsets.append(McpToolset(connection_params=StreamableHTTPConnectionParams(url=f"http://127.0.0.1:{port}/mcp", timeout=300), tool_name_prefix=prefix))
            else:
                from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
                from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
                from mcp import StdioServerParameters
                import shlex
                if ":" in entrypoint and " " not in entrypoint:
                    mp, on = entrypoint.split(":")
                    command, args = "python", ["-c", f"import sys,logging,asyncio;logging.basicConfig(level=logging.INFO,stream=sys.stderr);from {mp} import {on}\ntry:\n {on}.run(transport='stdio')\nexcept TypeError:\n from mcp.server.stdio import stdio_server\n async def _r():\n  async with stdio_server() as (r,w):\n   await {on}.run(r,w,{on}.create_initialization_options())\n asyncio.run(_r())"]
                else:
                    parts = shlex.split(entrypoint)
                    command, args = parts[0], parts[1:]
                toolsets.append(McpToolset(connection_params=StdioConnectionParams(server_params=StdioServerParameters(command=command,args=args,env=dict(os.environ)),timeout=30.0), tool_name_prefix=prefix))
                logging.warning(f"✅ [CUSTOM_MCP] {label}: Stdio toolset created.")
        except Exception as e:
            logging.error(f"❌ [CUSTOM_MCP] {label}: Failed: {e}", exc_info=True)
    return toolsets if toolsets else []



def get_slack_mcp_toolset():
    """Slack MCP toolset using static User Token (xoxp-) from Secret Manager."""
    import logging, os

    if not any(m.get("type") == "remote" and m.get("auth_type") == "oauth2_slack" for m in get_mcp_config()):
        return None

    token = os.environ.get("SLACK_ACCESS_TOKEN", "")
    if not token:
        logging.warning("\u26a0\ufe0f [SLACK_MCP] SLACK_ACCESS_TOKEN not set — Slack tools unavailable")
        return None
    try:
        from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
        from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
        logging.warning("\U0001f50c [SLACK_MCP] Connecting with static token...")
        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url="https://mcp.slack.com/mcp",
                headers={"Authorization": f"Bearer {token}"},
                timeout=300,
            )
        )
    except Exception as e:
        logging.error(f"\u274c [SLACK_MCP] Failed to initialize: {e}", exc_info=True)
        return None


# =============================================================================
# Background Task Management (Long-Running Agent Orchestration)
# =============================================================================
import uuid as _task_uuid
import datetime as _task_dt
from google.adk.tools import LongRunningFunctionTool

def register_background_task(
    task_name: str,
    task_description: str,
    task_prompt: str,
    tool_context: ToolContext,
) -> dict:
    """Register a background task for async execution. CRITICAL RULES:
    1. Call this tool EXACTLY ONCE per user request — never split a workflow into multiple tasks.
    2. task_prompt MUST contain ALL workflow steps (SCAN, CLASSIFY, PROCESS, AUDIT, etc.)
       as a complete, self-contained instruction. The background agent uses ONLY task_prompt
       to execute the entire workflow autonomously.
    3. A second call while a task is still ACTIVE (pending/working/submitted) will be BLOCKED.
       Completed, failed, or cancelled tasks CAN be re-registered with a new call.

    Args:
        task_name: Short identifier for the ENTIRE workflow (e.g. 'store_optimization_workflow').
        task_description: Summary of the complete workflow scope.
        task_prompt: COMPLETE, SELF-CONTAINED instruction covering ALL steps from scan to audit.
                     This is the ONLY input the background agent receives. Include data queries,
                     business rules, success criteria, and reporting requirements for every step.

    Returns:
        dict with ticket-id and status.
    """
    # --- Structural guard: block recursive delegation ---
    # Background workers (user_id="background-worker") must execute tasks
    # directly using data tools, not re-register them as new background tasks.
    if tool_context.user_id == "background-worker":
        return {
            "status": "blocked",
            "message": "Cannot register background tasks from within a background worker. "
                       "Execute operations directly using data tools (get_document, update_document, list_documents, execute_sql, etc.).",
        }

    # --- F1 (v10.64): block the inline deep_analysis specialist from escalating ---
    # deep_analysis_agent runs INLINE. It sometimes self-escalates a long analysis
    # into a background task and then polls it, so the inline turn NEVER returns
    # (the user sees a permanent "thinking" hang). It is the inline EXECUTOR, not a
    # scheduler: forbid background registration from this agent.
    _caller_agent = getattr(tool_context, 'agent_name', None) or ''
    if not _caller_agent:
        try:
            _caller_agent = tool_context._invocation_context.agent.name
        except Exception:
            _caller_agent = ''
    if _caller_agent == 'deep_analysis_agent':
        return {
            "status": "blocked",
            "message": "deep_analysis_agent runs INLINE and must NOT register background tasks. "
                       "Complete the analysis directly with data tools and deliver the FINAL report "
                       "in THIS turn. Do not call register_background_task, get_task_result, or "
                       "list_background_tasks.",
        }

    return submit_background_task_now(task_name, task_description, task_prompt)


def submit_background_task_now(task_name: str, task_description: str, task_prompt: str) -> dict:
    """Create and fire a background task WITHOUT the agent-level guards.

    Shared core of register_background_task (the agent tool). Also called
    directly (no ToolContext) by the inline-overrun conversion watchdog in
    fast_api_app.py: when an inline turn exceeds the chat rendering deadline,
    the executor moves the pressed "Run Inline:" intent here so the user
    still receives the full report as a background task.
    """
    import builtins
    _fs = getattr(builtins, '_firestore_client', None)
    _demo_id = os.environ.get("DEMO_ID", "")

    _task_id = str(_task_uuid.uuid4())[:8]
    _now = _task_dt.datetime.now(_task_dt.timezone.utc)
    _now_iso = _now.isoformat()


    _def_doc = {
        "task_id": _task_id,
        "task_name": task_name,
        "task_description": task_description,
        "task_prompt": task_prompt,
        "task_type": "immediate",
        "created_at": _now_iso,
    }
    _exec_doc = {
        "task_id": _task_id,
        "definition_id": _task_id,
        "status": "submitted",
        "progress_pct": 0,
        "log_tail": "",
        "result_summary": "",
        "started_at": "",
        "completed_at": "",
        "reported_to_user": False,
    }

    import logging as _flog
    _bg_logger = _flog.getLogger("bg_task")

    if not _fs or not _demo_id:
        _bg_logger.error("register_background_task: PRECONDITION FAILED fs=%s demo_id=%s", bool(_fs), repr(_demo_id))
        return {
            "status": "error",
            "message": "Cannot register background task: Firestore client unavailable (client="
                       + str(bool(_fs)) + ", demo_id=" + repr(_demo_id) + "). "
                       + "The task management backend is not configured for this demo.",
        }

    # --- Duplicate task guard ---
    # Block registration if an ACTIVE task with the same task_name exists.
    # This prevents button-spam from creating duplicate tasks.
    # Names are NORMALIZED (lowercased, all non-alphanumerics stripped) before
    # comparison so cosmetic variants are treated as the SAME task. The model
    # sometimes emits register_background_task twice in one turn with names that
    # differ only in case/separators (e.g. "Apex_Contract_Health_Analysis" vs
    # "apex_contract_health_analysis"), which an exact-match guard let through.
    def _norm_task_name(_s):
        return "".join(_c for _c in str(_s).lower() if _c.isalnum())
    _norm_new_name = _norm_task_name(task_name)
    try:
        _active_statuses = ("submitted", "working")
        _existing_execs = _fs.collection(_demo_id + "_task_executions").where(
            "status", "in", list(_active_statuses)
        ).stream()
        for _edoc in _existing_execs:
            _edata = _edoc.to_dict()
            _existing_def_id = _edata.get("definition_id", "")
            if _existing_def_id:
                try:
                    _def_ref = _fs.collection(_demo_id + "_task_definitions").document(_existing_def_id).get()
                    if _def_ref.exists:
                        _def_data = _def_ref.to_dict()
                        if _norm_task_name(_def_data.get("task_name")) == _norm_new_name:
                            _bg_logger.warning(
                                "register_background_task: BLOCKED duplicate task_name=%s (existing task_id=%s status=%s)",
                                task_name, _edata.get("task_id", "?"), _edata.get("status", "?")
                            )
                            return {
                                "status": "already_active",
                                "ticket-id": _edata.get("task_id", _existing_def_id),
                                "task_name": task_name,
                                "message": "A task with the same name is already active (status: "
                                           + _edata.get("status", "unknown") + "). "
                                           + "Use get_task_result or list_background_tasks to check its progress.",
                            }
                except Exception:
                    pass
    except Exception as _dup_err:
        _bg_logger.warning("register_background_task: duplicate check failed (non-fatal): %s", str(_dup_err)[:200])

    try:
        _fs.collection(_demo_id + "_task_definitions").document(_task_id).set(_def_doc)
        _fs.collection(_demo_id + "_task_executions").document(_task_id).set(_exec_doc)
        _bg_logger.warning("register_background_task: Firestore docs written task_id=%s", _task_id)
    except Exception as _fs_err:
        _bg_logger.error("register_background_task: Firestore write FAILED: %s", str(_fs_err)[:300])
        return {
            "status": "error",
            "message": "Failed to register task: Firestore write error. " + str(_fs_err)[:200],
        }

    # Fire-and-forget: trigger worker endpoint via localhost
    # IMPORTANT: Do NOT use SELF_URL (public *.run.app URL) for self-calls.
    # Cloud Run --ingress internal blocks requests from the container's own
    # public URL because they exit via the internet and re-enter as "external".
    # Using localhost:PORT keeps the request inside the container.
    import threading as _threading
    import requests as _requests
    _port = os.environ.get("PORT", "8080")
    _worker_url = "http://localhost:" + _port + "/execute_task"

    def _fire():
        import logging as _log
        _logger = _log.getLogger("bg_task")
        _logger.warning("_fire: SENDING request worker_url=%s task_id=%s demo_id=%s", _worker_url, _task_id, _demo_id)
        try:
            _headers = {"Content-Type": "application/json"}
            # Use short read timeout (0.5s): this is fire-and-forget.
            # The execute_task endpoint runs the agent asynchronously;
            # we only need to confirm the request was accepted, not wait for completion.
            _resp = _requests.post(_worker_url + "?task_id=" + _task_id + "&demo_id=" + _demo_id, json={"task_id": _task_id, "demo_id": _demo_id}, headers=_headers, timeout=(5, 0.5))
            _logger.warning("_fire: response status=%s body=%s", _resp.status_code, _resp.text[:300])
        except _requests.exceptions.ReadTimeout:
            # Expected: the worker is processing asynchronously.
            _logger.warning("_fire: request accepted (ReadTimeout expected for async), task_id=%s", _task_id)
        except _requests.exceptions.ConnectionError as _ce:
            _logger.error("_fire CONNECTION_ERROR: server may not be ready. task_id=%s err=%s", _task_id, str(_ce)[:300])
        except Exception as _e:
            _logger.error("_fire FAILED: %s: %s", type(_e).__name__, str(_e)[:500])
    _threading.Thread(target=_fire, daemon=True).start()



    _ret = {
        "status": "submitted",
        "ticket-id": _task_id,
        "task_name": task_name,
        "message": "Task registered. Processing started in background.",
    }
    # Computer Use tasks: precompute the live-view URL (session id == task id, see
    # computer_use_browse) so the agent can surface a "Watch Browser Session" link
    # immediately, while the browser loop is still running.
    try:
        if "computer_use_browse" in (task_prompt or ""):
            _vurl = os.environ.get("DATA_VIEWER_URL", "")
            if _vurl:
                _live = _vurl.rstrip("/") + "/browser-view?session=" + _task_id
                _ret["live_view_url"] = _live
                _ret["message"] = ("Task registered. A browser session is starting. "
                                   "You MUST show the user this live-view link so they can watch it: " + _live)
    except Exception:
        pass
    return _ret

background_task_tool = LongRunningFunctionTool(func=register_background_task)


def list_background_tasks(tool_context: ToolContext) -> dict:
    """Lists all background tasks and their current status.

    Returns:
        dict with list of tasks.
    """
    import builtins
    _fs = getattr(builtins, '_firestore_client', None)
    _demo_id = os.environ.get("DEMO_ID", "")
    if not _fs or not _demo_id:
        return {"tasks": [], "error": "Firestore not available (client=" + str(bool(_fs)) + ", demo_id=" + repr(_demo_id) + ")"}
    try:
        _docs = _fs.collection(_demo_id + "_task_executions").order_by(
            "started_at", direction="DESCENDING"
        ).limit(20).stream()
        _tasks = []
        for _doc in _docs:
            _d = _doc.to_dict()
            _tasks.append({
                "task_id": _d.get("task_id"),
                "status": _d.get("status"),
                "progress_pct": _d.get("progress_pct", 0),
                "result_summary": _d.get("result_summary", "")[:200],
            })
        return {"tasks": _tasks, "total": len(_tasks)}
    except Exception as _fs_err:
        return {"tasks": [], "error": "Firestore query failed: " + str(_fs_err)[:200]}


def get_task_result(task_id: str, tool_context: ToolContext) -> dict:
    """Gets the detailed result of a specific background task.

    Args:
        task_id: The ticket-id returned from register_background_task.

    Returns:
        dict with status, progress, and result.
    """
    import builtins
    _fs = getattr(builtins, '_firestore_client', None)
    _demo_id = os.environ.get("DEMO_ID", "")
    if not _fs or not _demo_id:
        return {"error": "Firestore not available (client=" + str(bool(_fs)) + ", demo_id=" + repr(_demo_id) + ")"}
    try:
        _ref = _fs.collection(_demo_id + "_task_executions").document(task_id)
        _doc = _ref.get()
        if not _doc.exists:
            return {"error": "Task not found: " + task_id}
        _d = _doc.to_dict()
        # Mark as reported
        if _d.get("status") in ("completed", "failed") and not _d.get("reported_to_user"):
            try:
                _ref.update({"reported_to_user": True})
            except Exception:
                pass  # Non-critical: best-effort mark
        return {
            "task_id": _d.get("task_id"),
            "status": _d.get("status"),
            "progress_pct": _d.get("progress_pct", 0),
            "result_summary": _d.get("result_summary", ""),
            "log_tail": _d.get("log_tail", ""),
            "started_at": _d.get("started_at", ""),
            "completed_at": _d.get("completed_at", ""),
            "_MANDATORY_ACTION": "YOU MUST present result_summary below as formatted markdown text in your response. "
                "Output the result_summary content VERBATIM as text. Do NOT skip it. Do NOT output only suggestion chips. "
                "If your response contains NO text and only A2UI JSON, you have FAILED.",
        }
    except Exception as _fs_err:
        return {"error": "Firestore read failed: " + str(_fs_err)[:200]}


def cancel_background_task(task_id: str, tool_context: ToolContext) -> dict:
    """Cancels a pending or running background task.

    Args:
        task_id: The ticket-id of the task to cancel.

    Returns:
        dict with cancellation status.
    """
    import builtins
    _fs = getattr(builtins, '_firestore_client', None)
    _demo_id = os.environ.get("DEMO_ID", "")
    if not _fs or not _demo_id:
        return {"error": "Firestore not available (client=" + str(bool(_fs)) + ", demo_id=" + repr(_demo_id) + ")"}
    try:
        _ref = _fs.collection(_demo_id + "_task_executions").document(task_id)
        _doc = _ref.get()
        if not _doc.exists:
            return {"error": "Task not found: " + task_id}
        _status = _doc.to_dict().get("status", "")
        if _status in ("completed", "failed", "cancelled"):
            return {"error": "Task already in terminal state: " + _status}
        _ref.update({"status": "cancelled"})
        return {"status": "cancelled", "task_id": task_id}
    except Exception as _fs_err:
        return {"error": "Firestore operation failed: " + str(_fs_err)[:200]}


def update_task_progress(
    task_id: str,
    current_step: str,
    progress_pct: int,
    log_entry: str,
    tool_context: ToolContext,
    workflow_state: dict | None = None,
) -> dict:
    """Updates progress of a running background task. Call this after each
    major workflow step completes to report real-time progress.

    Args:
        task_id: The ticket-id of the background task.
        current_step: Name of the step just completed (e.g. 'CLASSIFY').
        progress_pct: Estimated completion percentage (10-90, not 0 or 100).
        log_entry: Brief description of what was done and key metrics.
        workflow_state: Optional structured state for workflow tracking.
            Keys: completed_steps (list of step names), pending_items (int),
            auto_processed (int), deferred_for_approval (int),
            errors (int), current_phase (str).

    Returns:
        dict with update status.
    """
    import builtins
    import datetime as _dt
    _fs = getattr(builtins, '_firestore_client', None)
    _demo_id = os.environ.get("DEMO_ID", "")
    if not _fs or not _demo_id:
        return {"error": "Firestore not available"}
    try:
        _ref = _fs.collection(_demo_id + "_task_executions").document(task_id)
        _doc = _ref.get()
        if not _doc.exists:
            return {"error": "Task not found: " + task_id}
        _current = _doc.to_dict()
        if _current.get("status") not in ("working", "pending"):
            return {"error": "Task not in active state: " + _current.get("status", "")}
        _now = _dt.datetime.now(_dt.timezone.utc).strftime("%H:%M:%S")
        _existing_log = _current.get("log_tail", "")
        _new_log = _existing_log + ("[" + _now + "] " + current_step + ": " + log_entry + chr(10)) if _existing_log else ("[" + _now + "] " + current_step + ": " + log_entry + chr(10))
        # Keep log_tail to last 1500 chars to prevent unbounded growth
        if len(_new_log) > 1500:
            _new_log = _new_log[-1500:]
        _pct = max(10, min(90, progress_pct))
        _update_data = {
            "progress_pct": _pct,
            "log_tail": _new_log,
        }
        if workflow_state and isinstance(workflow_state, dict):
            _update_data["workflow_state"] = workflow_state
        _ref.update(_update_data)
        return {"status": "updated", "task_id": task_id, "progress_pct": _pct, "step": current_step}
    except Exception as _fs_err:
        return {"error": "Firestore update failed: " + str(_fs_err)[:200]}

def register_scheduled_task(
    task_name: str,
    task_description: str,
    task_prompt: str,
    schedule_cron: str,
    tool_context: ToolContext,
) -> dict:
    """Registers a new scheduled task with automatic Cloud Scheduler job creation.

    Args:
        task_name: Short identifier (e.g. 'daily_report').
        task_description: What the task does.
        task_prompt: Detailed instruction for each execution.
        schedule_cron: Cron expression (e.g. '0 9 * * 1-5' for weekdays 9am).

    Returns:
        dict with task_id, schedule, and job_name.
    """
    import builtins, json as _json, logging as _logging
    _fs = getattr(builtins, '_firestore_client', None)
    _demo_id = os.environ.get("DEMO_ID", "")
    _project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    _region = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    if _region == "global":
        _region = "us-central1"
    _task_id = str(_task_uuid.uuid4())[:8]
    _now = _task_dt.datetime.now(_task_dt.timezone.utc).isoformat()

    # 1. Save definition to Firestore
    _def_doc = {
        "task_id": _task_id,
        "task_name": task_name,
        "task_description": task_description,
        "task_prompt": task_prompt,
        "task_type": "scheduled",
        "schedule_cron": schedule_cron,
        "created_at": _now,
    }
    if _fs and _demo_id:
        _fs.collection(_demo_id + "_task_definitions").document(_task_id).set(_def_doc)
        # Create initial execution document so Data Viewer shows correct status
        _exec_doc = {
            "task_id": _task_id,
            "definition_id": _task_id,
            "status": "scheduled",
            "progress_pct": 0,
            "log_tail": "",
            "result_summary": "",
            "started_at": "",
            "completed_at": "",
            "reported_to_user": False,
        }
        _fs.collection(_demo_id + "_task_executions").document(_task_id).set(_exec_doc)

    # 2. Create Cloud Scheduler job
    _job_name = ""
    _sched_topic = _demo_id + "-sched-tasks"
    try:
        from google.cloud import scheduler_v1
        _sched_client = scheduler_v1.CloudSchedulerClient()
        _parent = "projects/" + _project_id + "/locations/" + _region
        _job_id = _demo_id + "-sched-" + _task_id

        _payload = _json.dumps({"task_id": _task_id, "demo_id": _demo_id}).encode("utf-8")
        _topic_path = "projects/" + _project_id + "/topics/" + _sched_topic

        _job = scheduler_v1.Job(
            name=_parent + "/jobs/" + _job_id,
            schedule=schedule_cron,
            time_zone="Asia/Tokyo",
            pubsub_target=scheduler_v1.PubsubTarget(
                topic_name=_topic_path,
                data=_payload,
            ),
        )
        _created = _sched_client.create_job(parent=_parent, job=_job)
        _job_name = _created.name
        _logging.warning("Created Cloud Scheduler job: " + _job_name)
    except Exception as _e:
        _logging.error("Failed to create scheduler job: " + str(_e))
        return {
            "status": "partial",
            "task_id": _task_id,
            "error": "Firestore saved but scheduler creation failed: " + str(_e)[:200],
        }

    return {
        "status": "scheduled",
        "task_id": _task_id,
        "task_name": task_name,
        "schedule": schedule_cron,
        "job_name": _job_name,
        "message": "Scheduled task registered. Will execute at: " + schedule_cron,
    }


def update_scheduled_task(
    task_id: str,
    schedule_cron: str,
    tool_context: ToolContext,
) -> dict:
    """Updates the schedule of an existing scheduled task.

    Args:
        task_id: The task_id of the scheduled task to update.
        schedule_cron: New cron expression (e.g. '0 18 * * 1-5' for weekdays 6pm).

    Returns:
        dict with updated schedule info.
    """
    import builtins, logging as _logging
    _fs = getattr(builtins, '_firestore_client', None)
    _demo_id = os.environ.get("DEMO_ID", "")
    _project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    _region = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    if _region == "global":
        _region = "us-central1"

    if not _fs or not _demo_id:
        return {"error": "Firestore not available (client=" + str(bool(_fs)) + ", demo_id=" + repr(_demo_id) + ")"}

    # Update Firestore definition
    _def_ref = _fs.collection(_demo_id + "_task_definitions").document(task_id)
    _def_doc = _def_ref.get()
    if not _def_doc.exists:
        return {"error": "Task not found: " + task_id}
    _def_data = _def_doc.to_dict()
    if _def_data.get("task_type") != "scheduled":
        return {"error": "Task is not a scheduled task"}

    _def_ref.update({"schedule_cron": schedule_cron})

    # Update Cloud Scheduler job
    _job_id = _demo_id + "-sched-" + task_id
    try:
        from google.cloud import scheduler_v1
        from google.protobuf import field_mask_pb2
        _client = scheduler_v1.CloudSchedulerClient()
        _job_name = "projects/" + _project_id + "/locations/" + _region + "/jobs/" + _job_id
        _job = scheduler_v1.Job(name=_job_name, schedule=schedule_cron)
        _mask = field_mask_pb2.FieldMask(paths=["schedule"])
        _updated = _client.update_job(job=_job, update_mask=_mask)
        _logging.warning("Updated scheduler job: " + _updated.name + " -> " + schedule_cron)
        return {
            "status": "updated",
            "task_id": task_id,
            "new_schedule": schedule_cron,
            "job_name": _updated.name,
        }
    except Exception as _e:
        _logging.error("Failed to update scheduler job: " + str(_e))
        return {
            "status": "partial",
            "task_id": task_id,
            "message": "Firestore updated but scheduler update failed: " + str(_e)[:200],
        }


def delete_scheduled_task(
    task_id: str,
    tool_context: ToolContext,
) -> dict:
    """Deletes a scheduled task and its Cloud Scheduler job.

    Args:
        task_id: The task_id of the scheduled task to delete.

    Returns:
        dict with deletion status.
    """
    import builtins, logging as _logging
    _fs = getattr(builtins, '_firestore_client', None)
    _demo_id = os.environ.get("DEMO_ID", "")
    _project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
    _region = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    if _region == "global":
        _region = "us-central1"

    if not _fs or not _demo_id:
        return {"error": "Firestore not available (client=" + str(bool(_fs)) + ", demo_id=" + repr(_demo_id) + ")"}

    # Check definition exists
    _def_ref = _fs.collection(_demo_id + "_task_definitions").document(task_id)
    _def_doc = _def_ref.get()
    if not _def_doc.exists:
        return {"error": "Task not found: " + task_id}

    # Delete Cloud Scheduler job
    _job_id = _demo_id + "-sched-" + task_id
    try:
        from google.cloud import scheduler_v1
        _client = scheduler_v1.CloudSchedulerClient()
        _job_name = "projects/" + _project_id + "/locations/" + _region + "/jobs/" + _job_id
        _client.delete_job(name=_job_name)
        _logging.warning("Deleted scheduler job: " + _job_name)
    except Exception as _e:
        _logging.warning("Scheduler job deletion failed (may not exist): " + str(_e)[:200])

    # Delete Firestore documents (definition + execution)
    _def_ref.delete()
    _fs.collection(_demo_id + "_task_executions").document(task_id).delete()

    return {
        "status": "deleted",
        "task_id": task_id,
        "message": "Scheduled task, execution record, and Cloud Scheduler job deleted.",
    }


def run_scheduled_task_now(
    task_id: str,
    tool_context: ToolContext,
) -> dict:
    """Triggers ONE immediate background execution of a registered scheduled task.

    Use this for manual test runs ("run it now") of a scheduled task. The task's
    stored task_prompt is executed by the background worker exactly like a
    Cloud Scheduler fire. Returns immediately with a ticket. Results are written
    to the operations console on completion; the chat summary is announced at the
    start of the user's NEXT message turn (there is no push notification). Use
    get_task_result for on-demand progress checks.

    Args:
        task_id: The task_id of the registered scheduled task to execute now.

    Returns:
        dict with trigger status and ticket id.
    """
    import builtins
    _fs = getattr(builtins, '_firestore_client', None)
    _demo_id = os.environ.get("DEMO_ID", "")
    if not _fs or not _demo_id:
        return {"error": "Firestore not available (client=" + str(bool(_fs)) + ", demo_id=" + repr(_demo_id) + ")"}

    _def_doc = _fs.collection(_demo_id + "_task_definitions").document(task_id).get()
    if not _def_doc.exists:
        return {"error": "Scheduled task not found: " + task_id}

    _exec_snap = _fs.collection(_demo_id + "_task_executions").document(task_id).get()
    if _exec_snap.exists and (_exec_snap.to_dict() or {}).get("status") == "working":
        return {
            "status": "already_running",
            "ticket-id": task_id,
            "message": "This task is already executing. Use get_task_result to check progress.",
        }

    # Fire-and-forget: trigger the /execute_task worker via localhost (same
    # pattern as register_background_task; see the comment there for why the
    # public SELF_URL must NOT be used for self-calls). force_run lets the
    # worker re-run a task whose single per-definition execution doc still
    # holds a terminal status from a previous run.
    import threading as _threading
    import requests as _requests
    _port = os.environ.get("PORT", "8080")
    _worker_url = "http://localhost:" + _port + "/execute_task"

    def _fire_now():
        import logging as _log
        _logger = _log.getLogger("sched_test_run")
        try:
            _resp = _requests.post(
                _worker_url + "?task_id=" + task_id + "&demo_id=" + _demo_id + "&force_run=1",
                json={"task_id": task_id, "demo_id": _demo_id, "force_run": True},
                headers={"Content-Type": "application/json"},
                timeout=(5, 0.5),
            )
            _logger.warning("run_now fire: status=%s task_id=%s", _resp.status_code, task_id)
        except _requests.exceptions.ReadTimeout:
            # Expected: the worker processes asynchronously.
            _logger.warning("run_now fire: accepted (ReadTimeout expected), task_id=%s", task_id)
        except Exception as _e:
            _logger.error("run_now fire FAILED: %s: %s", type(_e).__name__, str(_e)[:500])
    _threading.Thread(target=_fire_now, daemon=True).start()

    return {
        "status": "triggered",
        "ticket-id": task_id,
        "message": "Test execution started in the background. Results are written "
                   "to the operations console immediately upon completion, and a "
                   "chat summary will be announced at the start of the user's next "
                   "message turn (there is NO push notification — never promise "
                   "one, and never promise a completion time). Use get_task_result "
                   "for on-demand progress checks.",
    }


def write_operational_alert(
    alert_title: str,
    alert_message: str,
    status: str = "pending",
    tool_context: ToolContext = None
) -> dict:
    """Writes a high-priority operational alert or outreach task into the Firestore database.
    ALWAYS use this tool when you need to record a high-risk client alert, outreach task, 
    manual verification workflow, or log a manual review flag. Do NOT use raw MCP add_document.
    
    Args:
        alert_title: Clear, descriptive title of the alert (e.g., 'High-Priority Outreach: Satoru Gojo').
        alert_message: Detailed description of rules triggered, client profile, AUM, and required actions.
        status: Initial status of the alert, defaults to 'pending'.
        
    Returns:
        dict with write status and created alert_id.
    """
    import builtins, uuid, datetime
    _fs = getattr(builtins, '_firestore_client', None)
    _demo_id = os.environ.get("DEMO_ID", "")
    if not _fs or not _demo_id:
        return {"status": "error", "message": "Firestore operational database is not configured."}
    
    alert_id = f"alert_{uuid.uuid4().hex[:8]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    doc_data = {
        "alert_id": alert_id,
        "title": alert_title,
        "message": alert_message,
        "status": status,
        "created_at": now_iso,
        "updated_at": now_iso
    }
    try:
        _fs.collection(f"{_demo_id}_alerts").document(alert_id).set(doc_data)
        return {"status": "success", "alert_id": alert_id, "message": "Alert recorded successfully in operational database."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to record alert: {str(e)}"}


_FS_REST_SCALAR_KEYS = ("stringValue", "booleanValue", "timestampValue", "bytesValue", "referenceValue", "geoPointValue")

def _normalize_rest_values(v):
    # The agent is instructed to use Firestore REST typed-value format
    # (e.g. {"stringValue": "X"}) for the Firestore MCP. When that same format is
    # passed to this SDK-based tool it would be stored literally as a map field,
    # breaking downstream consumers (e.g. the Data Viewer). Unwrap to native values.
    if isinstance(v, dict):
        ks = list(v.keys())
        if len(ks) == 1:
            k = ks[0]
            inner = v[k]
            if k in _FS_REST_SCALAR_KEYS:
                return inner
            if k == "nullValue":
                return None
            if k == "integerValue":
                try:
                    return int(inner)
                except Exception:
                    return inner
            if k == "doubleValue":
                try:
                    return float(inner)
                except Exception:
                    return inner
            if k == "mapValue":
                fields = (inner or {}).get("fields", {}) if isinstance(inner, dict) else {}
                return {kk: _normalize_rest_values(vv) for kk, vv in (fields or {}).items()}
            if k == "arrayValue":
                vals = (inner or {}).get("values", []) if isinstance(inner, dict) else []
                return [_normalize_rest_values(x) for x in (vals or [])]
        return {kk: _normalize_rest_values(vv) for kk, vv in v.items()}
    if isinstance(v, list):
        return [_normalize_rest_values(x) for x in v]
    return v

def save_document_to_db(
    collection_name: str,
    document_id: str,
    document_json_string: str,
    tool_context: ToolContext = None
) -> dict:
    """Saves or updates a structured document in the Firestore operational database.
    Use this general tool to write structured records (orders, client updates, tasks).
    Accepts either a raw dictionary or a clean JSON-serialized string.
    
    Args:
        collection_name: Target collection name (e.g., 'outreach_tasks', 'client_status').
        document_id: Unique document identifier (e.g., 'client_102').
        document_json_string: Document body serialized as a JSON string OR a raw key-value dictionary.
        
    Returns:
        dict with database write status.
    """
    import builtins, json
    _fs = getattr(builtins, '_firestore_client', None)
    _demo_id = os.environ.get("DEMO_ID", "")
    if not _fs or not _demo_id:
        return {"status": "error", "message": "Firestore database is not configured."}
        
    try:
        if isinstance(document_json_string, dict):
            data = document_json_string
        else:
            data = json.loads(document_json_string)
            
        if not isinstance(data, dict):
            return {"status": "error", "message": "JSON body must represent a key-value dictionary."}

        # Defensively unwrap any Firestore REST typed-value wrappers so they are
        # stored as native scalars rather than literal {"stringValue": ...} maps.
        data = _normalize_rest_values(data)

        # Automatically inject ISO-8601 timestamp representing last update time for dynamic sorting in Data Viewer
        import datetime
        data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        full_coll = f"{_demo_id}_{collection_name}" if not collection_name.startswith(_demo_id) else collection_name
        _fs.collection(full_coll).document(document_id).set(data)
        return {"status": "success", "document_id": document_id, "message": f"Document saved successfully in {full_coll}."}
    except Exception as e:
        return {"status": "error", "message": f"Failed to save document: {str(e)}"}
