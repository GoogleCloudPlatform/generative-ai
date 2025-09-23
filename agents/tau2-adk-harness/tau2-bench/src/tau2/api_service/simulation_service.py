# Copyright Sierra

import uvicorn
from fastapi import FastAPI, HTTPException

from tau2.config import API_PORT
from tau2.data_model.simulation import Results, RunConfig
from tau2.registry import RegistryInfo
from tau2.run import get_options, load_tasks, run_domain

from .data_model import GetTasksRequest, GetTasksResponse

app = FastAPI()


@app.get("/health")
def get_health() -> dict[str, str]:
    return {"app_health": "OK"}


@app.post("/api/v1/get_options")
async def get_options_api() -> RegistryInfo:
    """ """
    try:
        return get_options()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/get_tasks")
async def get_tasks_api(
    request: GetTasksRequest,
) -> GetTasksResponse:
    """ """
    try:
        tasks = load_tasks(request.domain)
        return GetTasksResponse(tasks=tasks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/run_domain")
async def run_domain_api(
    request: RunConfig,
) -> Results:
    """ """

    try:
        results = run_domain(request)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=API_PORT)
