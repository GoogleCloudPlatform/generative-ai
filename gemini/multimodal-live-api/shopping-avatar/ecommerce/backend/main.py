# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
# Spanner metrics and telemetry disable configurations must be set before Spanner/gRPC imports
os.environ["SPANNER_ENABLE_BUILTIN_METRICS"] = "False"
os.environ["GOOGLE_CLOUD_DISABLE_GRPC"] = "True"
os.environ["OTEL_SDK_DISABLED"] = "true"

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import config, products, mcp, websocket, admin

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ecommerce-backend")

app = FastAPI(title="Multimodal E-Commerce Assistant Backend")

# Enable CORS for React Frontend Local Dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exception_handlers import http_exception_handler

# Include Route Routers
app.include_router(config.router)
app.include_router(products.router)
app.include_router(mcp.router)
app.include_router(websocket.router)
app.include_router(admin.router)

# Resolve and mount frontend static assets
backend_dir = os.path.dirname(os.path.abspath(__file__))
possible_paths = [
    os.path.join(backend_dir, "frontend", "dist"),      # Container path
    os.path.join(backend_dir, "..", "frontend", "dist") # Dev path
]

frontend_dist_path = None
for p in possible_paths:
    if os.path.exists(p):
        frontend_dist_path = p
        break

if frontend_dist_path:
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")
    logger.info(f"Successfully mounted frontend static files from: {frontend_dist_path}")

    # Catch 404 errors for non-API client routes and serve index.html
    @app.exception_handler(StarletteHTTPException)
    async def spa_fallback_exception_handler(request, exc):
        if exc.status_code == 404 and not request.url.path.startswith("/api/"):
            index_path = os.path.join(frontend_dist_path, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
        return await http_exception_handler(request, exc)
else:
    logger.warning("Frontend dist folder not found. React UI won't be served by FastAPI.")

@app.on_event("startup")
def cleanup_stale_files():
    try:
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        scratch_dir = os.path.join(backend_dir, "scratch")
        status_path = os.path.join(scratch_dir, "seeding_status.json")
        if os.path.exists(status_path):
            os.remove(status_path)
            logger.info("Cleared stale seeding status file on backend startup.")
        log_path = os.path.join(scratch_dir, "seeding_run.log")
        if os.path.exists(log_path):
            os.remove(log_path)
            logger.info("Cleared stale seeding logs on backend startup.")
    except Exception as e:
        logger.error(f"Failed to clear stale seeding status files: {e}")

