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


from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from .artifact.router import router as artifact_router

from .lifespan_resources import lifespan
from .websocket.router import websocket_router

# Load environment variables from a .env file if present.  When running in
# production, environment variables should be supplied by the deployment
# environment (e.g. Cloud Run, Cloud Functions) and the .env file will be
# ignored.
load_dotenv()


app = FastAPI(lifespan=lifespan, title="Financial Advisor")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(websocket_router, prefix="/api", tags=websocket_router.tags)
app.include_router(artifact_router, prefix="/api/artifact", tags=["artifact"])


@app.get("/")
async def health_check() -> str:
    return "OK"


FastAPIInstrumentor.instrument_app(app)
