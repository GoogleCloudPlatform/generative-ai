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

# --- Workspace auth plumbing (user OAuth; MCP mode or auth-only mode) ---
if os.environ.get("ENABLE_WORKSPACE_MCP") == "1" or os.environ.get("ENABLE_WORKSPACE_AUTH") == "1":

    # =============================================================================
    # Workspace USER-OAUTH plumbing (auth-only OR full Workspace MCP).
    # Present whenever the GE authorization exists - independent of the
    # Developer-Preview Workspace MCP servers. Consumed by the MCP toolsets
    # (when enabled), the Drive handoff tool, and the gws token pass-through.
    # =============================================================================
    # Thread-safe token holder for Workspace user authentication.
    # Uses builtins to share state across module boundaries (tools.py <-> fast_api_app.py).
    # Updated by TokenExtractionMiddleware (primary) and _handle_request (fallback)
    # with the OAuth token from each A2A request.
    if not hasattr(builtins, '_workspace_oauth_token'):
        builtins._workspace_oauth_token = ""
    # v11.6: per-session token registry, refreshed on EVERY user request by
    # _process_request_body. Needed because session.state[auth_id] only ever
    # holds the CREATE-time token: ADK's InMemorySessionService.get_session
    # returns a COPY, so per-turn state mutation never persists, and ~1h after
    # the session started the state token is expired even while GE keeps
    # sending fresh ones (confirmed live 2026-07-16: Drive save failed with an
    # expired token while the current token sat unused in builtins).
    if not hasattr(builtins, '_ws_session_tokens'):
        builtins._ws_session_tokens = {}

    def _workspace_header_provider(context) -> dict:
        """Returns Authorization headers carrying the USER's Workspace OAuth token.

        Used as the McpToolset header_provider (full Workspace MCP mode) and
        called directly by the Drive handoff / gws token pass-through.
        Tries multiple strategies, FRESHEST FIRST (v11.6 reorder):
          0. builtins._ws_session_tokens[session_id] (per-session, per-request fresh)
          1. builtins._workspace_oauth_token (process-global, per-request fresh)
          2. context.state[auth_id] (ADK context state - CREATE-time snapshot)
          3. context.session.state[auth_id] (session state - CREATE-time snapshot)
        State-based lookups (2/3) hold the token stored at session CREATION and
        go stale after ~1h, so they are last-resort fallbacks only. The global
        holder (1) can in principle serve another session's token when several
        users share one instance - same accepted demo trade-off as the .wstoken
        rotation - but it is always CURRENT, which is what Workspace calls need.
        """
        import logging as _log
        _logger = _log.getLogger('workspace_mcp')
        token = None

        auth_id = os.environ.get("GEMINI_AUTHORIZATION_ID", "")
        _logger.warning(f"header_provider: CALLED. auth_id='{auth_id}', context_type={type(context).__name__}")

        # Strategy 0 (v11.6): per-session registry - correct per-user AND fresh.
        # Session id discovery is best-effort across ADK context flavors.
        if not token:
            try:
                _sid = None
                _sess = getattr(context, 'session', None)
                if _sess is not None:
                    _sid = getattr(_sess, 'id', None)
                if not _sid:
                    _ictx = getattr(context, '_invocation_context', None)
                    if _ictx is not None:
                        _isess = getattr(_ictx, 'session', None)
                        if _isess is not None:
                            _sid = getattr(_isess, 'id', None)
                if _sid:
                    t = getattr(builtins, '_ws_session_tokens', {}).get(_sid)
                    if t:
                        token = t
                        _logger.warning(f"header_provider: OK Strategy0 - per-session registry (session={_sid}, prefix={token[:30]}..., len={len(token)})")
            except Exception as ex:
                _logger.warning(f"header_provider: Strategy0 ERROR - registry lookup failed: {type(ex).__name__}: {ex}")

        # Strategy 1 (v11.6, was Strategy 3): process-global holder, refreshed on
        # every request by TokenExtractionMiddleware / _process_request_body.
        if not token:
            t = getattr(builtins, '_workspace_oauth_token', '')
            if t:
                token = t
                _logger.warning(f"header_provider: OK Strategy1 - token from builtins (prefix={token[:30]}..., len={len(token)})")

        # Strategy 2 (was 1): context.state - CREATE-time snapshot, may be stale.
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
                        _logger.warning(f"header_provider: OK Strategy2 - token from context.state (prefix={token[:30]}..., len={len(token)}) - CREATE-time snapshot, may be stale")
                    else:
                        _logger.warning(f"header_provider: Strategy2 MISS - context.state exists (type={type(state).__name__}) but auth_id '{auth_id}' not found. keys={list(state.keys()) if hasattr(state, 'keys') else 'N/A'}")
            except Exception as ex:
                _logger.warning(f"header_provider: Strategy2 ERROR - context.state access failed: {type(ex).__name__}: {ex}")

        # Strategy 3 (was 2): context.session.state - CREATE-time snapshot too.
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
                            _logger.warning(f"header_provider: OK Strategy3 - token from context.session.state (prefix={token[:30]}..., len={len(token)}) - CREATE-time snapshot, may be stale")
            except Exception as ex:
                _logger.warning(f"header_provider: Strategy3 ERROR - context.session.state access failed: {type(ex).__name__}: {ex}")

        if not token:
            _logger.warning("header_provider: ❌ NO TOKEN AVAILABLE - Workspace calls will fail with permission denied")

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
else:
    def _workspace_header_provider(context):
        return {}

# --- Workspace MCP toolsets (enabled per demo via ENABLE_WORKSPACE_MCP) ---
if os.environ.get("ENABLE_WORKSPACE_MCP") == "1":
    # =============================================================================
    # Workspace USER-OAUTH plumbing (auth-only OR full Workspace MCP).
    # Present whenever the GE authorization exists - independent of the
    # Developer-Preview Workspace MCP servers. Consumed by the MCP toolsets
    # (when enabled), the Drive handoff tool, and the gws token pass-through.
    # =============================================================================
    # Thread-safe token holder for Workspace user authentication.
    # Uses builtins to share state across module boundaries (tools.py <-> fast_api_app.py).
    # Updated by TokenExtractionMiddleware (primary) and _handle_request (fallback)
    # with the OAuth token from each A2A request.
    if not hasattr(builtins, '_workspace_oauth_token'):
        builtins._workspace_oauth_token = ""
    # v11.6: per-session token registry, refreshed on EVERY user request by
    # _process_request_body. Needed because session.state[auth_id] only ever
    # holds the CREATE-time token: ADK's InMemorySessionService.get_session
    # returns a COPY, so per-turn state mutation never persists, and ~1h after
    # the session started the state token is expired even while GE keeps
    # sending fresh ones (confirmed live 2026-07-16: Drive save failed with an
    # expired token while the current token sat unused in builtins).
    if not hasattr(builtins, '_ws_session_tokens'):
        builtins._ws_session_tokens = {}

    def _workspace_header_provider(context) -> dict:
        """Returns Authorization headers carrying the USER's Workspace OAuth token.

        Used as the McpToolset header_provider (full Workspace MCP mode) and
        called directly by the Drive handoff / gws token pass-through.
        Tries multiple strategies, FRESHEST FIRST (v11.6 reorder):
          0. builtins._ws_session_tokens[session_id] (per-session, per-request fresh)
          1. builtins._workspace_oauth_token (process-global, per-request fresh)
          2. context.state[auth_id] (ADK context state - CREATE-time snapshot)
          3. context.session.state[auth_id] (session state - CREATE-time snapshot)
        State-based lookups (2/3) hold the token stored at session CREATION and
        go stale after ~1h, so they are last-resort fallbacks only. The global
        holder (1) can in principle serve another session's token when several
        users share one instance - same accepted demo trade-off as the .wstoken
        rotation - but it is always CURRENT, which is what Workspace calls need.
        """
        import logging as _log
        _logger = _log.getLogger('workspace_mcp')
        token = None

        auth_id = os.environ.get("GEMINI_AUTHORIZATION_ID", "")
        _logger.warning(f"header_provider: CALLED. auth_id='{auth_id}', context_type={type(context).__name__}")

        # Strategy 0 (v11.6): per-session registry - correct per-user AND fresh.
        # Session id discovery is best-effort across ADK context flavors.
        if not token:
            try:
                _sid = None
                _sess = getattr(context, 'session', None)
                if _sess is not None:
                    _sid = getattr(_sess, 'id', None)
                if not _sid:
                    _ictx = getattr(context, '_invocation_context', None)
                    if _ictx is not None:
                        _isess = getattr(_ictx, 'session', None)
                        if _isess is not None:
                            _sid = getattr(_isess, 'id', None)
                if _sid:
                    t = getattr(builtins, '_ws_session_tokens', {}).get(_sid)
                    if t:
                        token = t
                        _logger.warning(f"header_provider: OK Strategy0 - per-session registry (session={_sid}, prefix={token[:30]}..., len={len(token)})")
            except Exception as ex:
                _logger.warning(f"header_provider: Strategy0 ERROR - registry lookup failed: {type(ex).__name__}: {ex}")

        # Strategy 1 (v11.6, was Strategy 3): process-global holder, refreshed on
        # every request by TokenExtractionMiddleware / _process_request_body.
        if not token:
            t = getattr(builtins, '_workspace_oauth_token', '')
            if t:
                token = t
                _logger.warning(f"header_provider: OK Strategy1 - token from builtins (prefix={token[:30]}..., len={len(token)})")

        # Strategy 2 (was 1): context.state - CREATE-time snapshot, may be stale.
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
                        _logger.warning(f"header_provider: OK Strategy2 - token from context.state (prefix={token[:30]}..., len={len(token)}) - CREATE-time snapshot, may be stale")
                    else:
                        _logger.warning(f"header_provider: Strategy2 MISS - context.state exists (type={type(state).__name__}) but auth_id '{auth_id}' not found. keys={list(state.keys()) if hasattr(state, 'keys') else 'N/A'}")
            except Exception as ex:
                _logger.warning(f"header_provider: Strategy2 ERROR - context.state access failed: {type(ex).__name__}: {ex}")

        # Strategy 3 (was 2): context.session.state - CREATE-time snapshot too.
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
                            _logger.warning(f"header_provider: OK Strategy3 - token from context.session.state (prefix={token[:30]}..., len={len(token)}) - CREATE-time snapshot, may be stale")
            except Exception as ex:
                _logger.warning(f"header_provider: Strategy3 ERROR - context.session.state access failed: {type(ex).__name__}: {ex}")

        if not token:
            _logger.warning("header_provider: ❌ NO TOKEN AVAILABLE - Workspace calls will fail with permission denied")

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


    import re
    import httpx
    from pydantic import AnyUrl

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

    # Workspace MCP scope definitions (shared between factory and auth_kwargs)
    # NOTE: _workspace_header_provider itself lives in the workspaceAuthEnabled
    # block above (it is shared with the auth-only mode).
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


def _generate_v4_signed_url(bucket_name, object_name, content_type, expiration_days=7, method="GET"):
    """Mint a V4 signed URL using ADC + IAM signBlob (no key file on Cloud Run).

    Passing service_account_email + access_token makes the storage client sign
    remotely via the IAM signBlob API, which requires the runtime SA to hold
    roles/iam.serviceAccountTokenCreator on itself.

    method="GET" (default) signs a download URL with a response content type.
    method="PUT" signs an upload URL; the uploader MUST send exactly the same
    Content-Type header that was signed here.
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
    _sign_kwargs = {}
    if method == "PUT":
        _sign_kwargs["content_type"] = content_type
    else:
        _sign_kwargs["response_type"] = content_type
    return blob.generate_signed_url(
        version="v4",
        expiration=timedelta(days=min(expiration_days, 7)),  # V4 hard max is 7 days
        method=method,
        service_account_email=sa_email,
        access_token=creds.token,
        **_sign_kwargs
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
    # Computer Use (browser agent) -- Gemini 3.5 Flash built-in computer_use
    # tool driven over a self-hosted headless Chromium (Playwright). Adapted
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
        # Pinned to gemini-3.5-flash: gemini-3.6-flash does not support the
        # Computer Use tool, so this must NOT follow AGENT_MODEL.
        model = os.environ.get("COMPUTER_USE_MODEL", "gemini-3.5-flash")
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
        _res = {
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
        if _d.get("status") == "completed":
            # Autonomous tasks share this collection, so this tool also gets
            # asked about them. Managed-agent builds re-sign deliverable links
            # live here (see _ma_attach_live_deliverables); a no-op for plain
            # background tasks, which have no deliverables prefix in storage.
            _attach = globals().get("_ma_attach_live_deliverables")
            if _attach is not None:
                try:
                    _attach(_res, task_id, "result_summary")
                except Exception:
                    pass  # status reporting must never fail on link refresh
        return _res
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


# --- Managed Agent (Antigravity) autonomous delegation (ENABLE_MANAGED_AGENT) ---
if os.environ.get("ENABLE_MANAGED_AGENT") == "1":
    # =============================================================================
    # Managed Autonomous Agent (Antigravity) delegation - v11.0
    # The setup script provisions a managed agent (Agents API, Pre-GA) that runs in
    # an isolated sandbox (bash, filesystem, code exec, web search). This section
    # talks to it over the Interactions API via plain REST + SSE (httpx, already a
    # transitive dependency) so no extra pinned package is needed.
    # Hybrid execution: stream synchronously for up to MANAGED_AGENT_SYNC_WAIT_S,
    # then hand off to the existing background-task infrastructure (Firestore
    # task_executions doc + _inject_completed_tasks announcement) while a daemon
    # thread keeps consuming the SSE stream. Cloud Run runs with min-instances=1
    # and no CPU throttling, so the thread survives after the turn returns.
    # =============================================================================
    _MANAGED_AGENT_ID = os.environ.get("MANAGED_AGENT_ID", "").strip()
    _MANAGED_AGENT_LOCATION = "global"  # the Managed Agents API is global-only
    _INTERACTIONS_API_REVISION = "2026-05-20"  # single pin point for header drift
    # 30s (not longer): real autonomous tasks essentially never finish inside the
    # sync window, so its job is just to show the delegation starting live in the
    # Thinking accordion (a handful of tool events) before handing off to the
    # background flow. Tunable per demo via the Cloud Run env var.
    _MA_SYNC_WAIT_S = int(os.environ.get("MANAGED_AGENT_SYNC_WAIT_S", "30"))
    _MA_MAX_RUNTIME_S = int(os.environ.get("MANAGED_AGENT_MAX_RUNTIME_S", "1800"))
    # After the SSE stream window closes, the interaction keeps running
    # server-side (background=true); we keep polling GET for this much longer.
    _MA_POLL_EXTRA_S = int(os.environ.get("MANAGED_AGENT_POLL_EXTRA_S", "3600"))

    _ma_creds = None

    # Cross-module progress channel: the SSE thread pushes short status snippets
    # here and the A2A executor (fast_api_app) drains them into Thinking-accordion
    # status events while the delegation tool is blocking. Published on builtins
    # (same pattern as _firestore_client) because tools.py and fast_api_app run in
    # the same process.
    import queue as _ma_queue_mod
    import builtins as _ma_builtins_mod
    _ma_progress_queue = _ma_queue_mod.Queue(maxsize=50)
    _ma_builtins_mod._ma_progress_queue = _ma_progress_queue

    def _ma_push_progress(text):
        if not text:
            return
        try:
            _ma_progress_queue.put_nowait(str(text).replace(chr(10), " ").strip()[:200])
        except Exception:
            pass  # queue full or closed - progress display is best-effort

    def _ma_drain_progress_queue():
        try:
            while True:
                _ma_progress_queue.get_nowait()
        except Exception:
            pass

    def _ma_get_access_token():
        """Returns an access token from module-cached ADC credentials.

        google-auth refreshes only when the cached token is expired, so this is
        cheap to call per delegation (tokens live about an hour)."""
        global _ma_creds
        import google.auth
        import google.auth.transport.requests
        if _ma_creds is None:
            _ma_creds, _unused = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        if not _ma_creds.valid:
            _ma_creds.refresh(google.auth.transport.requests.Request())
        return _ma_creds.token

    def _ma_interactions_url():
        return ("https://aiplatform.googleapis.com/v1beta1/projects/" + get_project_id()
                + "/locations/" + _MANAGED_AGENT_LOCATION + "/interactions")

    def _ma_override_tools(include_mcp=True):
        """Per-turn tools override for the Interactions API.

        The override COMPLETELY replaces the agent's preconfigured tools for the
        turn, so the first-party tools must always be re-listed. Google-hosted MCP
        servers (BigQuery / Firestore / Knowledge Catalog) are attached with a
        fresh bearer token because tokens cannot live in the static agent config.

        NOTE (verified live 2026-07-12, HTTP 400): unlike the AGENT config, the
        interactions tools override does NOT accept type 'filesystem' (supported:
        google_maps, mcp_server, code_execution, computer_use, function,
        url_context, google_search). The sandbox keeps its built-in bash +
        file_system abilities regardless, so filesystem is simply omitted here."""
        tools = [
            {"type": "code_execution"},
            {"type": "google_search"},
            {"type": "url_context"},
        ]
        if not include_mcp:
            return tools
        try:
            _headers = {
                "Authorization": "Bearer " + _ma_get_access_token(),
                "x-goog-user-project": get_project_id(),
            }
            tools.append({"type": "mcp_server", "name": "bigquery", "url": get_bigquery_mcp_url(), "headers": _headers})
            tools.append({"type": "mcp_server", "name": "firestore", "url": get_firestore_mcp_url(), "headers": _headers})
            tools.append({"type": "mcp_server", "name": "knowledge_catalog", "url": get_knowledge_catalog_mcp_url(), "headers": _headers})
        except Exception as _mcp_err:
            import logging as _l
            _l.getLogger("managed_agent").warning("MCP tool override skipped: %s", str(_mcp_err)[:200])
        return tools

    def _ma_fresh_environment():
        """Full sandbox spec for a NEW environment.

        The interaction-level environment does NOT inherit the agent's
        base_environment (verified live 2026-07-12): a bare remote spec yields a
        standard sandbox WITHOUT skills, and listing sources without network is
        rejected. So every fresh environment restates network + skills sources."""
        _env = {"type": "remote", "network": {"allowlist": [{"domain": "*"}]}}
        _src = os.environ.get("MANAGED_AGENT_SKILLS_SOURCE", "").strip()
        if _src:
            _env["sources"] = [{"type": "gcs", "source": _src, "target": "/.agent/skills"}]
        return _env

    def _ma_read_session_state():
        """Demo-wide sandbox continuity (environment + previous interaction ids).

        Stored in Firestore (not ADK session state) so background completions and
        later GE sessions reuse the same persistent sandbox filesystem."""
        import builtins
        _fs = getattr(builtins, "_firestore_client", None)
        _demo_id = os.environ.get("DEMO_ID", "")
        if not _fs or not _demo_id:
            return {}
        try:
            _snap = _fs.collection(_demo_id + "_managed_agent_state").document("current").get()
            return _snap.to_dict() if _snap.exists else {}
        except Exception:
            return {}

    def _ma_finalize_interaction_record(shared):
        """Post-completion hygiene for one interaction.

        Persists sandbox continuity, then - when the task message carried the
        user's Workspace token - DELETEs the stored interaction so the token
        does not linger in the interaction history (verified live: DELETE
        returns 200 and removes the stored record; the sandbox environment
        itself lives on independently via its env id). Token-bearing tasks
        therefore keep ENVIRONMENT continuity but give up conversational
        previous_interaction_id continuity.
        """
        _iid = shared.get("interaction_id", "")
        if shared.get("token_embedded"):
            _ma_write_session_state(shared.get("environment_id", ""), "")
            if _iid:
                try:
                    import httpx
                    _headers = {
                        "Authorization": "Bearer " + _ma_get_access_token(),
                        "Api-Revision": _INTERACTIONS_API_REVISION,
                    }
                    httpx.delete(_ma_interactions_url() + "/" + _iid, headers=_headers, timeout=30.0)
                except Exception:
                    import logging as _l
                    _l.getLogger("managed_agent").warning("token-bearing interaction cleanup failed for %s", _iid[:24])
            # Remove the rotating token object as well.
            _tid = shared.get("task_id", "")
            _bkt = os.environ.get("DASHBOARDS_BUCKET", "").strip()
            if _tid and _bkt:
                try:
                    from google.cloud import storage as _st
                    _st.Client().bucket(_bkt).blob("autonomous/" + _tid + "/.wstoken").delete()
                except Exception:
                    pass
        else:
            _ma_write_session_state(shared.get("environment_id", ""), _iid)

    def _ma_write_session_state(environment_id, interaction_id):
        import builtins
        import datetime as _dt
        _fs = getattr(builtins, "_firestore_client", None)
        _demo_id = os.environ.get("DEMO_ID", "")
        if not _fs or not _demo_id:
            return
        try:
            _data = {"updated_at": _dt.datetime.now(_dt.timezone.utc).isoformat()}
            if environment_id:
                _data["environment_id"] = environment_id
            if interaction_id:
                _data["previous_interaction_id"] = interaction_id
            _fs.collection(_demo_id + "_managed_agent_state").document("current").set(_data, merge=True)
        except Exception:
            pass

    _MA_DELIVERABLE_SPECS = [
        ("deliverable.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation", "presentation deck"),
        ("deliverable.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "Word document"),
        ("deliverable.pdf", "application/pdf", "PDF report"),
        ("deliverable.html", "text/html; charset=utf-8", "web page"),
        ("deliverable.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "spreadsheet"),
    ]

    def _ma_mint_upload_urls(task_id):
        """Signed PUT URLs (7 days) for the fixed deliverable filenames.

        The sandbox holds no credentials by design; pre-signed URLs are the only
        write path back to the project. Never log the returned URLs."""
        _bucket = os.environ.get("DASHBOARDS_BUCKET", "").strip()
        if not _bucket:
            return []
        _urls = []
        for _name, _mime, _label in _MA_DELIVERABLE_SPECS:
            try:
                _url = _generate_v4_signed_url(_bucket, "autonomous/" + task_id + "/" + _name, _mime, 7, "PUT")
                _urls.append((_name, _mime, _label, _url))
            except Exception as _sign_err:
                import logging as _l
                _l.getLogger("managed_agent").warning("upload URL signing failed for %s: %s", _name, str(_sign_err)[:200])
        return _urls

    def _ma_collect_deliverables(task_id):
        """Markdown download links for whatever the sandbox actually uploaded."""
        _bucket = os.environ.get("DASHBOARDS_BUCKET", "").strip()
        if not _bucket:
            return []
        try:
            from google.cloud import storage
            _client = storage.Client()
            _links = []
            for _blob in _client.list_blobs(_bucket, prefix="autonomous/" + task_id + "/"):
                _bname = _blob.name.split("/")[-1]
                if _bname.startswith("."):
                    continue  # internal objects (e.g. the rotating .wstoken)
                _mime = _blob.content_type or "application/octet-stream"
                _url = _generate_v4_signed_url(_bucket, _blob.name, _mime)
                _links.append("- [" + _bname + "](" + _url + ")")
            return _links
        except Exception as _list_err:
            import logging as _l
            _l.getLogger("managed_agent").warning("deliverable listing failed: %s", str(_list_err)[:200])
            return []

    _MA_NO_UPLOAD_NOTE = (
        "SYSTEM CHECK (auto-generated): no deliverable files were uploaded to cloud storage for this task. "
        "If the report above says files were produced or delivered, they exist ONLY inside the sandbox "
        "workspace and were NOT delivered to the user. Be honest about this - never present workspace-only "
        "files as delivered - and offer to run a short follow-up autonomous task that uploads the existing "
        "files (the sandbox filesystem persists between tasks, so re-delegating an upload-only task works; "
        "when delegating that follow-up, pass THIS task's ticket-id as deliverables_for_task_id so the "
        "uploads attach to this task and its status checks then return the download links).")

    _MA_DL_MARKER = "DELIVERABLE DOWNLOADS (links valid for 7 days):"

    def _ma_attach_live_deliverables(_out, _task_id, _report_key):
        """Attaches freshly signed deliverable links to a completed-task status
        payload. Status checks must NOT rely on the links frozen into the report
        at completion time: those signatures expire, and files can also land in
        storage AFTER the completion snapshot (a late upload, or a follow-up
        upload-only task writing into this task's prefix). So every check
        re-lists the bucket and mints fresh URLs. Returns True when at least one
        link was attached."""
        _links = _ma_collect_deliverables(_task_id)
        if not _links:
            return False
        _report = _out.get(_report_key) or ""
        # The completion-time link block (stale signatures) and the no-upload
        # honesty note (obsolete once files exist in storage) both mislead the
        # model when left next to the fresh links - drop them from the report.
        if _MA_DL_MARKER in _report:
            _report = _report.split(_MA_DL_MARKER)[0].rstrip()
        if _MA_NO_UPLOAD_NOTE in _report:
            _report = _report.replace(_MA_NO_UPLOAD_NOTE, "").rstrip()
        _out[_report_key] = _report
        _out["deliverable_downloads"] = _links
        _out["_MANDATORY_ACTION"] = (
            "Present the " + _report_key + " as formatted markdown text. Your response MUST ALSO list EVERY link "
            "in deliverable_downloads, verbatim, as markdown links under a short heading meaning 'Deliverables' in "
            "the conversation language. These are freshly signed download/view URLs for the files this task "
            "produced (valid for 7 days; an .html link opens as an interactive page in the browser). Reporting a "
            "completed file-producing task WITHOUT these file links is a FAILED response - never omit them.")
        return True

    def _ma_run_interaction(payload, shared):
        """Thread target: POSTs one interaction and consumes its SSE stream.

        Event shapes verified live (2026-07-12): 'interaction.created' (carries
        interaction.id), 'step.start' (step.type: model_output / function_call /
        function_result), 'step.delta' (delta.type 'text' carries incremental
        model text), 'step.stop', and 'interaction.completed' (carries
        environment_id + usage but NO output text - the report is the
        concatenation of the text deltas).

        Mutates shared in place: events, report_buf, last_text, environment_id,
        interaction_id, completed, error. Sets shared['_event'] when the stream
        ends (success or failure)."""
        import httpx
        import json as _json
        import time as _t
        try:
            _headers = {
                "Authorization": "Bearer " + _ma_get_access_token(),
                "Content-Type": "application/json",
                "Api-Revision": _INTERACTIONS_API_REVISION,
            }
            _deadline = _t.monotonic() + _MA_MAX_RUNTIME_S
            _timeout = httpx.Timeout(connect=30.0, read=600.0, write=60.0, pool=30.0)
            with httpx.Client(timeout=_timeout) as _client:
                with _client.stream("POST", _ma_interactions_url(), json=payload, headers=_headers) as _resp:
                    if _resp.status_code != 200:
                        _body = _resp.read().decode("utf-8", "replace")[:400]
                        shared["error"] = "HTTP " + str(_resp.status_code) + ": " + _body
                        return
                    if not shared.get("handoff"):
                        _ma_push_progress("Sandbox session opened - the autonomous agent is picking up the task...")
                    for _line in _resp.iter_lines():
                        if shared.get("cancelled"):
                            # User pressed Cancel (Data Viewer / cancel tool): the
                            # monitor flagged it; stop consuming immediately. The
                            # server-side interaction itself cannot be killed
                            # (no cancel API), it just runs out unobserved.
                            shared["stream_abandoned"] = True
                            break
                        if _t.monotonic() > _deadline:
                            # The interaction keeps running server-side
                            # (background=true): stop streaming, poll below.
                            shared["stream_abandoned"] = True
                            break
                        if not _line or not _line.startswith("data:"):
                            continue
                        try:
                            _event = _json.loads(_line[5:].strip())
                        except Exception:
                            continue
                        shared["events"] = shared.get("events", 0) + 1
                        _etype = _event.get("event_type", "") or _event.get("type", "")
                        _interaction = _event.get("interaction") if isinstance(_event.get("interaction"), dict) else {}
                        if _interaction.get("id"):
                            shared["interaction_id"] = _interaction["id"]
                        if _interaction.get("environment_id"):
                            shared["environment_id"] = _interaction["environment_id"]
                        if _etype == "step.delta":
                            _delta = _event.get("delta") if isinstance(_event.get("delta"), dict) else {}
                            if _delta.get("type") == "text" and isinstance(_delta.get("text"), str):
                                shared["report_buf"] = shared.get("report_buf", "") + _delta["text"]
                                shared["last_text"] = shared["report_buf"][-400:]
                                # Live progress into the Thinking accordion (inline
                                # phase only; rate-limited).
                                if not shared.get("handoff") and _t.monotonic() - shared.get("_last_push_t", 0) > 3:
                                    shared["_last_push_t"] = _t.monotonic()
                                    _ma_push_progress(shared["report_buf"][-200:])
                        elif _etype == "step.start":
                            _step = _event.get("step") if isinstance(_event.get("step"), dict) else {}
                            if _step.get("type") == "function_call":
                                _tool_name = _step.get("name", "") or "a sandbox tool"
                                # Long tool phases produce no text deltas, so this
                                # is what keeps the Data Viewer log (and the
                                # accordion) showing real activity, not just
                                # "working...".
                                shared["last_text"] = "Using tool: " + _tool_name
                                # Accordion pushes are throttled and deduplicated:
                                # rapid bursts of the same tool (e.g. 20x
                                # view_file while reading skills) flooded the GE
                                # stream with back-to-back status events, which
                                # the GE client handles poorly. One push per
                                # tool-name change, min 2.5s apart.
                                if (not shared.get("handoff")
                                        and _tool_name != shared.get("_last_tool_pushed")
                                        and _t.monotonic() - shared.get("_last_push_t", 0) > 2.5):
                                    shared["_last_tool_pushed"] = _tool_name
                                    shared["_last_push_t"] = _t.monotonic()
                                    _ma_push_progress("Using tool: " + _tool_name)
                        elif _etype == "interaction.completed":
                            shared["completed"] = True
            # Stream ended. If we never saw interaction.completed, treat a clean
            # close with accumulated output as complete anyway (defensive) -
            # unless we abandoned the stream on the deadline, in which case the
            # polling fallback below decides.
            if not shared.get("completed") and shared.get("report_buf") and not shared.get("stream_abandoned"):
                shared["completed"] = True
        except Exception as _run_err:
            shared["stream_error"] = str(_run_err)[:400]
        # Polling fallback: with background=true the interaction keeps running
        # server-side after the stream window closes (deadline, read timeout,
        # network drop). Poll GET on the interaction and harvest the final report
        # from its persisted steps (verified live 2026-07-12).
        try:
            if not shared.get("completed") and not shared.get("error") and not shared.get("cancelled"):
                _ma_poll_interaction(shared)
        except Exception as _poll_err:
            if not shared.get("error"):
                shared["error"] = str(_poll_err)[:400]
        if shared.get("cancelled"):
            shared["error"] = shared.get("error") or "Cancelled by the user."
            # Token hygiene on cancel: best-effort delete of the token-bearing
            # interaction record (may fail while it is still in_progress
            # server-side; the embedded token expires within the hour anyway).
            if shared.get("token_embedded") and shared.get("interaction_id"):
                try:
                    import httpx as _hx
                    _hx.delete(_ma_interactions_url() + "/" + shared["interaction_id"],
                               headers={"Authorization": "Bearer " + _ma_get_access_token(),
                                        "Api-Revision": _INTERACTIONS_API_REVISION},
                               timeout=30.0)
                except Exception:
                    pass
            if shared.get("token_embedded") and shared.get("task_id"):
                try:
                    from google.cloud import storage as _st
                    _bkt = os.environ.get("DASHBOARDS_BUCKET", "").strip()
                    if _bkt:
                        _st.Client().bucket(_bkt).blob("autonomous/" + shared["task_id"] + "/.wstoken").delete()
                except Exception:
                    pass
        elif not shared.get("completed") and not shared.get("error"):
            shared["error"] = (shared.get("stream_error")
                               or "The autonomous task was still running when the monitoring window ("
                                  + str(_MA_MAX_RUNTIME_S + _MA_POLL_EXTRA_S) + "s) closed. It may still finish; "
                                  "check again later with get_autonomous_task_status.")
        shared["done"] = True
        _evt = shared.get("_event")
        if _evt is not None:
            _evt.set()

    def _ma_poll_interaction(shared):
        """Polls GET .../interactions/<id> after the SSE stream is gone.

        On completion, harvests environment_id and rebuilds the final report from
        the persisted model_output steps (the GET body of a completed interaction
        contains the full step history - verified live)."""
        import httpx
        import time as _t
        _iid = shared.get("interaction_id", "")
        if not _iid:
            return
        if not shared.get("handoff"):
            _ma_push_progress("Live stream closed - switching to status polling (the sandbox keeps working)...")
        shared["last_text"] = "Live stream closed; polling interaction status (the sandbox keeps working)..."
        _url = _ma_interactions_url() + "/" + _iid
        _deadline = _t.monotonic() + _MA_POLL_EXTRA_S
        with httpx.Client(timeout=30.0) as _client:
            while _t.monotonic() < _deadline:
                _t.sleep(30)
                try:
                    _headers = {
                        "Authorization": "Bearer " + _ma_get_access_token(),
                        "Api-Revision": _INTERACTIONS_API_REVISION,
                    }
                    _resp = _client.get(_url, headers=_headers)
                    if _resp.status_code != 200:
                        continue
                    _data = _resp.json()
                except Exception:
                    continue
                shared["events"] = shared.get("events", 0) + 1
                if _data.get("environment_id"):
                    shared["environment_id"] = _data["environment_id"]
                _status = _data.get("status", "")
                if _status == "completed":
                    # Harvest report text from ALL non-input steps (not just
                    # type model_output - long agentic runs have surfaced text
                    # under other step shapes). user_input steps are EXCLUDED:
                    # they contain the task message (and possibly the Workspace
                    # token).
                    _texts = []
                    def _collect_step_texts(node):
                        if isinstance(node, dict):
                            for _k, _v in node.items():
                                if _k == "text" and isinstance(_v, str) and _v.strip():
                                    _texts.append(_v)
                                else:
                                    _collect_step_texts(_v)
                        elif isinstance(node, list):
                            for _item in node:
                                _collect_step_texts(_item)
                    for _step in (_data.get("steps") or []):
                        if isinstance(_step, dict) and _step.get("type") != "user_input":
                            _collect_step_texts(_step)
                    if _texts:
                        shared["report_buf"] = (chr(10) + chr(10)).join(_texts)
                    else:
                        # Diagnostic: log the STRUCTURE only (never content - it
                        # could include the task message / token).
                        try:
                            import logging as _l
                            _shape = []
                            for _step in (_data.get("steps") or []):
                                if isinstance(_step, dict):
                                    _ctypes = [(_c.get("type", "?") if isinstance(_c, dict) else "?") for _c in (_step.get("content") or [])]
                                    _shape.append(str(_step.get("type", "?")) + ":" + ",".join(_ctypes))
                            _l.getLogger("managed_agent").warning(
                                "poll harvest found NO text; interaction step shapes: %s", "; ".join(_shape)[:800])
                        except Exception:
                            pass
                    shared["completed"] = True
                    return
                if _status in ("failed", "cancelled"):
                    shared["error"] = "The autonomous interaction ended server-side with status: " + _status
                    return

    def _ma_final_report(shared):
        _report = (shared.get("report_buf") or "").strip()
        if not _report:
            _report = ("The autonomous agent finished but returned no text report. Its step-by-step "
                       "activity log is available in the Data Viewer Tasks tab; any uploaded deliverables "
                       "are linked below. Consider re-running the task with a simpler, outcome-focused brief.")
        return _report

    def _ma_monitor_task(task_id, shared):
        """Daemon monitor after a background handoff: mirrors SSE progress into the
        existing task_executions doc so _inject_completed_tasks and the View Full
        Report flow work unchanged."""
        import builtins
        import time as _t
        import datetime as _dt
        _fs = getattr(builtins, "_firestore_client", None)
        _demo_id = os.environ.get("DEMO_ID", "")
        if not _fs or not _demo_id:
            return
        _ref = _fs.collection(_demo_id + "_task_executions").document(task_id)
        _log = ""
        while not shared.get("done"):
            _t.sleep(12)
            try:
                _snap = _ref.get()
                if _snap.exists and _snap.to_dict().get("status") == "cancelled":
                    shared["cancelled"] = True
                    return
                _now = _dt.datetime.now(_dt.timezone.utc).strftime("%H:%M:%S")
                _snippet = (shared.get("last_text", "") or "working...").replace(chr(10), " ")[:180]
                _log = _log + "[" + _now + "] SANDBOX: " + _snippet + chr(10)
                if len(_log) > 1500:
                    _log = _log[-1500:]
                _pct = max(10, min(90, 10 + int(shared.get("events", 0) / 3)))
                # interaction_id is mirrored for diagnosability: it lets operators
                # inspect the live interaction via GET .../interactions/<id>.
                _ref.update({"progress_pct": _pct, "log_tail": _log, "interaction_id": shared.get("interaction_id", "")})
            except Exception:
                pass
        try:
            if shared.get("inline_reported"):
                # The delegation tool already presented the result inline and
                # finalizes the doc itself (reported_to_user=True) so the
                # completion is not announced a second time.
                return
            _now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
            if shared.get("error"):
                _ref.update({
                    "status": "failed",
                    "result_summary": "Autonomous task failed: " + shared.get("error", "unknown error"),
                    "completed_at": _now_iso,
                })
                return
            _report = _ma_final_report(shared)
            _links = _ma_collect_deliverables(shared.get("deliver_tid") or task_id)
            if _links:
                _report = _report + chr(10) + chr(10) + "DELIVERABLE DOWNLOADS (links valid for 7 days):" + chr(10) + chr(10).join(_links)
            else:
                _report = _report + chr(10) + chr(10) + _MA_NO_UPLOAD_NOTE
            _ref.update({
                "status": "completed",
                "result_summary": _report,
                "progress_pct": 100,
                "completed_at": _now_iso,
            })
            _ma_finalize_interaction_record(shared)
        except Exception:
            pass

    def _ma_build_task_message(task_description, input_data, upload_urls):
        _msg = task_description.strip()
        if input_data and input_data.strip():
            _msg = _msg + chr(10) + chr(10) + "INPUT DATA (provided by the requesting assistant):" + chr(10) + input_data.strip()
        if upload_urls:
            _lines = []
            for _name, _mime, _label, _url in upload_urls:
                _lines.append("- " + _label + " (" + _name + "): upload with curl -sS -X PUT --upload-file <file> -H " + chr(34) + "Content-Type: " + _mime + chr(34) + " " + chr(34) + _url + chr(34))
            _msg = (_msg + chr(10) + chr(10)
                    + "DELIVERABLE UPLOAD URLS (only if you produce a file of that type; send EXACTLY the Content-Type shown, retry once on failure):"
                    + chr(10) + chr(10).join(_lines))
        return _msg

    async def delegate_autonomous_task(
        task_name: str,
        task_description: str,
        input_data: str = "",
        deliverables_for_task_id: str = "",
        tool_context: ToolContext = None,
    ) -> dict:
        """Delegates a long-running, multi-step task to the fully autonomous cloud
        agent (isolated sandbox with bash, filesystem, code execution, pip/npm,
        Google Search, web page reading, direct BigQuery/Firestore access, and
        professional deliverable skills for decks / documents / PDFs / web pages).

        USE FOR: live web research combined with internal data, building and
        running code, producing downloadable business files (pptx/docx/pdf/html),
        and any autonomous work expected to take more than a minute.
        DO NOT USE FOR: quick lookups or analysis that inline tools (execute_sql,
        code execution, publish_dashboard) can finish in this turn, or demo-DB
        batch workflows (use register_background_task for those).

        Behavior: waits briefly for fast tasks and returns the finished report
        inline; longer tasks continue in the background and completion is
        announced automatically in a later turn (like background tasks).

        Args:
            task_name: Short identifier for the task (e.g. 'competitor_deck').
            task_description: COMPLETE, self-contained instruction in the USER'S
                language: goal, deliverable type, audience, and success criteria.
                The autonomous agent sees ONLY this text (plus input_data).
                Describe OUTCOMES only - NEVER reference this agent's own tool
                names (publish_dashboard, save_deliverables_to_drive, ...): the
                autonomous agent cannot call them and gets derailed trying.
            input_data: Optional data to embed verbatim (query results, lists,
                constraints) so the agent does not have to re-derive them.
            deliverables_for_task_id: LEAVE EMPTY for normal tasks. Set it ONLY
                when re-delegating an upload-only follow-up for a FINISHED task
                whose files stayed in the sandbox: pass that original ticket-id
                so the uploads land in the original task's deliverable storage
                and status checks on the original ticket return the file links.

        Returns:
            dict with either the finished report (status 'completed') or a
            background ticket (status 'working_in_background').
        """
        import asyncio as _asyncio
        import threading as _threading
        import builtins
        import datetime as _dt
        import uuid as _uuid

        if not _MANAGED_AGENT_ID:
            return {
                "status": "unavailable",
                "message": "The autonomous agent was not provisioned in this project (its Pre-GA creation "
                           "failed or timed out during setup; re-running the setup script retries it). "
                           "Complete the task with inline tools instead, and tell the user the "
                           "autonomous-delegation feature is not enabled.",
            }

        if tool_context is not None and getattr(tool_context, "user_id", "") == "background-worker":
            return {
                "status": "blocked",
                "message": "Background workers must not re-delegate work to the autonomous agent. "
                           "Execute the task directly with data tools.",
            }
        # NOTE (v11.2): deep_analysis_agent IS allowed to delegate. The original
        # F1-style block created a dead end: a mis-routed "Run Inline" press
        # landed a web/file/Workspace task on deep_analysis, the block forced it
        # inline, and the model rationalized the failure to the user as a
        # "security restriction" (observed live 2026-07-14). Unlike
        # register_background_task+polling (the F1 hang), this tool ALWAYS
        # returns within the sync window, so the hang risk that motivated F1
        # does not apply here.

        _fs = getattr(builtins, "_firestore_client", None)
        _demo_id = os.environ.get("DEMO_ID", "")

        # Duplicate guard (button spam): block a second delegation while an
        # autonomous task with the same normalized name is still active.
        def _norm(_s):
            return "".join(_c for _c in str(_s).lower() if _c.isalnum())
        if _fs and _demo_id:
            try:
                _actives = _fs.collection(_demo_id + "_task_executions").where(
                    "status", "in", ["submitted", "working"]).stream()
                for _edoc in _actives:
                    _edata = _edoc.to_dict()
                    _def_snap = _fs.collection(_demo_id + "_task_definitions").document(
                        _edata.get("definition_id", "")).get()
                    if _def_snap.exists:
                        _ddata = _def_snap.to_dict()
                        if _ddata.get("task_type") == "autonomous" and _norm(_ddata.get("task_name")) == _norm(task_name):
                            return {
                                "status": "already_active",
                                "ticket-id": _edata.get("task_id", ""),
                                "message": "An autonomous task with the same name is already running. "
                                           "Use get_autonomous_task_status to check its progress.",
                            }
            except Exception:
                pass

        _task_id = str(_uuid.uuid4())[:8]
        # Deliverable storage prefix: normally this task's own id. An upload-only
        # follow-up passes the ORIGINAL ticket id (see the Args doc) so its
        # uploads attach to the original task and status checks on that ticket
        # pick them up via the live re-collection in _ma_attach_live_deliverables.
        _deliver_tid = "".join(_c for _c in str(deliverables_for_task_id or "") if _c.isalnum() or _c in "-_")[:64] or _task_id
        _upload_urls = _ma_mint_upload_urls(_deliver_tid)
        _message = _ma_build_task_message(task_description, input_data, _upload_urls)

        # Workspace pass-through (auth-only or full MCP mode): hand the USER's
        # OAuth token to the sandbox so the gws CLI can act on their Workspace.
        # Accepted trade-off for demos: the token lands in the stored interaction
        # (it expires in about an hour); token-bearing interactions are DELETED
        # from the store right after their result is harvested.
        _ws_token_embedded = False
        if os.environ.get("ENABLE_WORKSPACE_MCP") == "1" or os.environ.get("ENABLE_WORKSPACE_AUTH") == "1":
            def _ma_refresh_token_object(_tid, _tok):
                # Rotating token object: the sandbox re-fetches the CURRENT user
                # token from a pre-signed URL when its snapshot expires. Kept fresh
                # by fast_api_app on every user turn (best-effort).
                _bkt = os.environ.get("DASHBOARDS_BUCKET", "").strip()
                if not _bkt or not _tok:
                    return
                try:
                    from google.cloud import storage as _st
                    _st.Client().bucket(_bkt).blob("autonomous/" + _tid + "/.wstoken").upload_from_string(_tok, content_type="text/plain")
                except Exception:
                    pass
            try:
                _ws_auth = (_workspace_header_provider(tool_context) or {}).get("Authorization", "")
            except Exception:
                _ws_auth = ""
            if _ws_auth.startswith("Bearer "):
                _message = (_message + chr(10) + chr(10)
                            + "WORKSPACE ACCESS (handle with care):" + chr(10)
                            + "- Before any Google Workspace operation, run: export GOOGLE_WORKSPACE_CLI_TOKEN=" + _ws_auth[7:] + chr(10)
                            + "- This user access token expires in about an hour: do Workspace operations EARLY in the task." + chr(10)
                            + "- Use the gws CLI for ALL Workspace reads/writes (see the gws-* skills under /.agent/skills). It is usually pre-installed at $HOME/bin/gws - call it by that absolute path. If missing: mkdir -p $HOME/bin && curl -sL https://github.com/googleworkspace/cli/releases/latest/download/google-workspace-cli-x86_64-unknown-linux-musl.tar.gz | tar xz -C $HOME/bin ./gws && chmod +x $HOME/bin/gws (do NOT use npm - its Linux binary needs GLIBC 2.39 which this sandbox lacks)." + chr(10)
                            + "- GUARDRAILS: NEVER send email - create Gmail drafts only, unless the task explicitly says to send. NEVER delete anything in Workspace. Post Chat messages ONLY to spaces the task explicitly names - and if the named space does not exist yet, CREATE it with that exact name first, then post (expected in demo environments; mention the creation in your report). Create Calendar events only when the task asks for them." + chr(10)
                            + "- Non-ASCII email headers (Subject etc.) MUST be RFC 2047 MIME-encoded; read the draft back to verify the subject is not garbled, and recreate it if needed." + chr(10)
                            + "- Report created drafts as ALREADY EXISTING in Gmail (subject + link https://mail.google.com/mail/u/0/#drafts), never as text to copy manually." + chr(10)
                            + "- NEVER write this token into your report, logs, code, or any file.")
                _ws_token_embedded = True
                _ma_refresh_token_object(_task_id, _ws_auth[7:])
                try:
                    _ws_refresh_url = _generate_v4_signed_url(
                        os.environ.get("DASHBOARDS_BUCKET", "").strip(),
                        "autonomous/" + _task_id + "/.wstoken", "text/plain", 7)
                    _message = (_message + chr(10)
                                + "- TOKEN REFRESH: if a Workspace call fails with 401 / invalid credentials, fetch the CURRENT token with: curl -s " + chr(34) + _ws_refresh_url + chr(34)
                                + " then re-export GOOGLE_WORKSPACE_CLI_TOKEN with the response body and retry. A fresh token appears there whenever the user talks to the assistant; if it is still expired, note that in your report and continue with the non-Workspace parts of the task.")
                except Exception:
                    pass


        # Task docs are created UP FRONT (not only on background handoff) so the
        # Data Viewer Tasks tab shows the sandbox working live from second zero.
        _docs_created = False
        if _fs and _demo_id:
            try:
                _now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
                _fs.collection(_demo_id + "_task_definitions").document(_task_id).set({
                    "task_id": _task_id,
                    "task_name": task_name,
                    "task_description": task_description,
                    "task_prompt": _message,
                    "task_type": "autonomous",
                    "created_at": _now_iso,
                })
                _fs.collection(_demo_id + "_task_executions").document(_task_id).set({
                    "task_id": _task_id,
                    "definition_id": _task_id,
                    "status": "working",
                    "progress_pct": 10,
                    "log_tail": "Delegated to the autonomous sandbox agent." + chr(10),
                    "result_summary": "",
                    "started_at": _now_iso,
                    "completed_at": "",
                    "reported_to_user": False,
                })
                _docs_created = True
            except Exception:
                pass

        _session = _ma_read_session_state()
        _env_value = _session.get("environment_id") or os.environ.get("MANAGED_AGENT_ENV_ID", "").strip() or _ma_fresh_environment()
        _payload = {
            "agent": _MANAGED_AGENT_ID,
            "stream": True,
            "background": True,
            "store": True,
            "environment": _env_value,
            "input": [{"type": "user_input", "content": [{"type": "text", "text": _message}]}],
            "tools": _ma_override_tools(True),
        }
        if _session.get("previous_interaction_id"):
            _payload["previous_interaction_id"] = _session["previous_interaction_id"]

        _ma_drain_progress_queue()
        _ma_push_progress("Delegating to the autonomous agent: " + task_name)
        _evt = _threading.Event()
        _shared = {"_event": _evt, "token_embedded": _ws_token_embedded, "task_id": _task_id, "deliver_tid": _deliver_tid}
        if _docs_created:
            _threading.Thread(target=_ma_monitor_task, args=(_task_id, _shared), daemon=True).start()
        _threading.Thread(target=_ma_run_interaction, args=(_payload, _shared), daemon=True).start()
        _finished = await _asyncio.to_thread(_evt.wait, _MA_SYNC_WAIT_S)

        # Fast-failure fallback: if the interaction failed almost immediately (for
        # example an MCP attachment problem), retry ONCE without the MCP override.
        if _finished and _shared.get("error") and not _shared.get("completed"):
            import logging as _l
            _l.getLogger("managed_agent").warning("delegation failed fast (%s) - retrying without MCP tools", _shared.get("error", "")[:200])
            _shared["inline_reported"] = True  # detach the old monitor from doc finalization
            _payload["tools"] = _ma_override_tools(False)
            _ma_push_progress("First attempt failed - retrying without data-tool attachments...")
            _evt = _threading.Event()
            _shared = {"_event": _evt, "token_embedded": _ws_token_embedded, "task_id": _task_id, "deliver_tid": _deliver_tid}
            if _docs_created:
                _threading.Thread(target=_ma_monitor_task, args=(_task_id, _shared), daemon=True).start()
            _threading.Thread(target=_ma_run_interaction, args=(_payload, _shared), daemon=True).start()
            _finished = await _asyncio.to_thread(_evt.wait, _MA_SYNC_WAIT_S)

        if _finished:
            _shared["inline_reported"] = True  # this turn presents the result; monitor must not finalize
            _now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()
            if _shared.get("error"):
                if _docs_created:
                    try:
                        _fs.collection(_demo_id + "_task_executions").document(_task_id).update({
                            "status": "failed",
                            "result_summary": "Autonomous task failed: " + _shared.get("error", ""),
                            "completed_at": _now_iso,
                            "reported_to_user": True,
                        })
                    except Exception:
                        pass
                return {
                    "status": "error",
                    "message": "The autonomous agent could not run this task: " + _shared.get("error", "unknown error")
                               + " - Complete what you can with inline tools and tell the user what happened.",
                }
            _report = _ma_final_report(_shared)
            _links = _ma_collect_deliverables(_deliver_tid)
            if _links:
                _report = _report + chr(10) + chr(10) + "DELIVERABLE DOWNLOADS (links valid for 7 days):" + chr(10) + chr(10).join(_links)
            else:
                _report = _report + chr(10) + chr(10) + _MA_NO_UPLOAD_NOTE
            _ma_finalize_interaction_record(_shared)
            if _docs_created:
                try:
                    _fs.collection(_demo_id + "_task_executions").document(_task_id).update({
                        "status": "completed",
                        "result_summary": _report,
                        "progress_pct": 100,
                        "completed_at": _now_iso,
                        "reported_to_user": True,
                    })
                except Exception:
                    pass
            return {
                "status": "completed",
                "report": _report,
                "_MANDATORY_ACTION": "Present the report below to the user as formatted markdown text. It is "
                                     "already written in the task language - do NOT translate, truncate, or "
                                     "convert it into A2UI cards. If deliverable download links are present, "
                                     "show them as markdown links.",
            }

        # Not finished inside the sync window: hand off to the background-task
        # infrastructure. The SSE thread keeps running; the monitor (started at
        # delegation time) mirrors its progress into Firestore and the completion
        # is auto-announced next turn.
        _shared["handoff"] = True  # stop Thinking-accordion pushes; the turn is ending
        _ma_drain_progress_queue()
        if not _docs_created:
            return {
                "status": "working_unmonitored",
                "message": "The autonomous task is running but the task backend is unavailable, so its "
                           "completion cannot be announced automatically. Tell the user the task was started "
                           "and results will be available in the sandbox session.",
            }
        _viewer_url = os.environ.get("DATA_VIEWER_URL", "").strip()
        _live_hint = ""
        if _viewer_url:
            _live_hint = (" Share this live-progress link with the user (opens the Data Viewer; the Tasks tab "
                          "streams the sandbox activity log): " + _viewer_url)
        return {
            "status": "working_in_background",
            "ticket-id": _task_id,
            "task_name": task_name,
            "message": "The autonomous agent accepted the task and keeps working in its sandbox. "
                       "Tell the user the work continues in the background and the finished result "
                       "(including any deliverable download links) will be announced automatically. "
                       "Progress can be checked anytime with get_autonomous_task_status." + _live_hint,
        }

    def get_autonomous_task_status(task_id: str, tool_context: ToolContext = None) -> dict:
        """Checks the live progress of a delegated autonomous task.

        Args:
            task_id: The ticket-id returned by delegate_autonomous_task.

        Returns:
            dict with status, progress_pct, recent activity log, and - once the
            task is finished - the full report with deliverable links.
        """
        import builtins
        _fs = getattr(builtins, "_firestore_client", None)
        _demo_id = os.environ.get("DEMO_ID", "")
        if not _fs or not _demo_id:
            return {"status": "error", "message": "Task backend unavailable."}
        try:
            _snap = _fs.collection(_demo_id + "_task_executions").document(task_id).get()
            if not _snap.exists:
                return {"status": "not_found", "message": "No autonomous task with ticket-id " + task_id}
            _d = _snap.to_dict()
            _out = {
                "status": _d.get("status", ""),
                "progress_pct": _d.get("progress_pct", 0),
                "recent_activity": _d.get("log_tail", ""),
                "interaction_id": _d.get("interaction_id", ""),
            }
            if _d.get("status") in ("completed", "failed"):
                _out["report"] = _d.get("result_summary", "")
                _out["_MANDATORY_ACTION"] = ("Present the report as formatted markdown text, verbatim, "
                                             "including any deliverable download links.")
                if _d.get("status") == "completed":
                    try:
                        _ma_attach_live_deliverables(_out, task_id, "report")
                    except Exception:
                        pass  # status reporting must never fail on link refresh
            return _out
        except Exception as _err:
            return {"status": "error", "message": "Status lookup failed: " + str(_err)[:200]}


    # Drive handoff requires BOTH the Managed Agent and Workspace auth
    # (inside the Managed Agent guard, so this equals the drive-handoff condition).
    if os.environ.get("ENABLE_WORKSPACE_MCP") == "1" or os.environ.get("ENABLE_WORKSPACE_AUTH") == "1":
        # =============================================================================
        # Google Drive handoff for Managed Agent deliverables (v11.0)
        # Requires BOTH Workspace MCP (user OAuth with drive.file scope via the GE
        # authorization) AND the Managed Agent (deliverables in GCS). Office files
        # are import-CONVERTED by Drive v3 into native Google formats; PDFs are
        # stored as-is; HTML deliverables intentionally STAY in GCS (their signed
        # URL previews in one click). Runs only in a LIVE user turn - the user OAuth
        # token is captured per-request and has no refresh path.
        # =============================================================================
        _MA_DRIVE_CONVERT = {
            ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/vnd.google-apps.presentation", "Google Slides"),
            ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/vnd.google-apps.document", "Google Docs"),
            ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/vnd.google-apps.spreadsheet", "Google Sheets"),
            ".pdf": ("application/pdf", "", "PDF"),
        }
        _MA_DRIVE_MAX_BYTES = 50 * 1024 * 1024

        def _ma_drive_multipart(meta, media_mime, media_bytes):
            import json as _json
            _b = "ma-drive-b0undary-7f3k9q"
            _crlf = chr(13) + chr(10)
            _head = ("--" + _b + _crlf
                     + "Content-Type: application/json; charset=UTF-8" + _crlf + _crlf
                     + _json.dumps(meta) + _crlf
                     + "--" + _b + _crlf
                     + "Content-Type: " + media_mime + _crlf + _crlf)
            _tail = _crlf + "--" + _b + "--"
            _body = _head.encode("utf-8") + media_bytes + _tail.encode("utf-8")
            return _body, "multipart/related; boundary=" + _b

        def save_deliverables_to_drive(ticket_id: str, tool_context: ToolContext = None) -> dict:
            """Saves the deliverable files of a completed autonomous task into the
            USER'S Google Drive. Office files become NATIVE Google files: pptx ->
            Google Slides, docx -> Google Docs, xlsx -> Google Sheets; PDFs are
            stored as-is. Web-page (html) deliverables keep their existing preview
            link and are not copied to Drive.

            USE WHEN: the user asks to save deliverables to Drive, or asked for the
            output as Google Slides / Docs / Sheets (call it right after announcing
            the completed task in the same turn).

            Args:
                ticket_id: The ticket-id of the delegated task whose files to save.

            Returns:
                dict with the saved files and their webViewLink URLs.
            """
            import builtins
            import httpx

            if tool_context is not None and getattr(tool_context, "user_id", "") == "background-worker":
                return {"status": "blocked",
                        "message": "Drive saving needs the live user's authorization and cannot run from a background worker."}

            _hdrs = None
            try:
                _hdrs = _workspace_header_provider(tool_context)
            except Exception:
                _hdrs = None
            _auth = (_hdrs or {}).get("Authorization", "")
            if not _auth:
                return {"status": "auth_required",
                        "message": "No Workspace authorization token is available for this user. Ask the user to "
                                   "re-authorize the agent in Gemini Enterprise (the consent prompt appears when a "
                                   "Workspace tool is used), then press the save button again."}

            _bucket = os.environ.get("DASHBOARDS_BUCKET", "").strip()
            if not _bucket:
                return {"status": "error", "message": "Deliverable storage is not configured (DASHBOARDS_BUCKET missing)."}

            _task_name = ""
            _fs = getattr(builtins, "_firestore_client", None)
            _demo_id = os.environ.get("DEMO_ID", "")
            if _fs and _demo_id:
                try:
                    _def_snap = _fs.collection(_demo_id + "_task_definitions").document(ticket_id).get()
                    if _def_snap.exists:
                        _task_name = (_def_snap.to_dict().get("task_name") or "").strip()
                except Exception:
                    pass
            _base_name = _task_name or ("autonomous-deliverable-" + ticket_id)

            try:
                from google.cloud import storage
                _client = storage.Client()
                _blobs = list(_client.list_blobs(_bucket, prefix="autonomous/" + ticket_id + "/"))
            except Exception as _ls_err:
                return {"status": "error", "message": "Could not list deliverables: " + str(_ls_err)[:200]}
            if not _blobs:
                return {"status": "not_found",
                        "message": "No STAGED deliverable files for ticket " + ticket_id + " in cloud storage. This does NOT "
                                   "mean the task produced nothing: when the autonomous agent saved its output directly to "
                                   "Google Drive / Docs / Slides / Sheets, nothing is left to stage here and that save already "
                                   "succeeded. Check the task report (get_autonomous_task_status) for Drive links before "
                                   "concluding anything; NEVER tell the user no file was generated based on this status alone."}

            _saved = []
            _kept_links = []
            _errors = []
            with httpx.Client(timeout=120.0) as _hclient:
                for _blob in _blobs:
                    _fname = _blob.name.split("/")[-1]
                    if _fname.startswith("."):
                        continue  # internal objects (e.g. the rotating .wstoken)
                    _ext = "." + _fname.split(".")[-1].lower() if "." in _fname else ""
                    if _ext == ".html":
                        # Stays in GCS by design: the signed URL previews in one click.
                        try:
                            _url = _generate_v4_signed_url(_bucket, _blob.name, _blob.content_type or "text/html; charset=utf-8")
                            _kept_links.append({"name": _fname, "type": "web page (opens directly via its preview link)", "webViewLink": _url})
                        except Exception:
                            pass
                        continue
                    if (_blob.size or 0) > _MA_DRIVE_MAX_BYTES:
                        _errors.append(_fname + " skipped (larger than 50MB)")
                        continue
                    try:
                        _data = _blob.download_as_bytes()
                    except Exception as _dl_err:
                        _errors.append(_fname + " download failed: " + str(_dl_err)[:120])
                        continue
                    _src_mime, _target_mime, _label = _MA_DRIVE_CONVERT.get(
                        _ext, (_blob.content_type or "application/octet-stream", "", "file"))
                    _stem = _fname.rsplit(".", 1)[0] if "." in _fname else _fname
                    if _target_mime:
                        _meta = {"name": _base_name + " - " + _stem, "mimeType": _target_mime}
                    else:
                        _meta = {"name": _base_name + " - " + _fname}
                    _body, _ctype = _ma_drive_multipart(_meta, _src_mime, _data)
                    try:
                        _resp = _hclient.post(
                            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,mimeType,webViewLink",
                            content=_body,
                            headers={"Authorization": _auth, "Content-Type": _ctype},
                        )
                        if _resp.status_code in (401, 403):
                            return {"status": "auth_required",
                                    "message": "Google Drive rejected the user's authorization (HTTP " + str(_resp.status_code)
                                               + "). Ask the user to re-authorize the agent in Gemini Enterprise and try again."}
                        if _resp.status_code != 200:
                            _errors.append(_fname + " upload failed (HTTP " + str(_resp.status_code) + "): " + _resp.text[:150])
                            continue
                        _fmeta = _resp.json()
                        _saved.append({"name": _fmeta.get("name", _fname),
                                       "type": _label,
                                       "webViewLink": _fmeta.get("webViewLink", "")})
                    except Exception as _up_err:
                        _errors.append(_fname + " upload error: " + str(_up_err)[:150])

            if not _saved and not _kept_links:
                return {"status": "error",
                        "message": "No files could be saved to Drive. " + ("; ".join(_errors))[:400]}
            _out = {
                "status": "success" if not _errors else "partial",
                "files": _saved + _kept_links,
                "_MANDATORY_ACTION": "Present each file to the user as a markdown link (name -> webViewLink), stating its "
                                     "type (Google Slides / Google Docs / Google Sheets / PDF / web page) in the user's "
                                     "language. Converted files are native Google files in the user's My Drive.",
            }
            if _errors:
                _out["problems"] = _errors
            return _out

