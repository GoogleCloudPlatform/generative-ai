import logging

from backend.app.routers import evaluation, indexes, prompts, rag
from fastapi import FastAPI
import uvicorn

# Configure logging
logging.basicConfig(filename="eval.log", encoding="utf-8", level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Include routers
app.include_router(prompts.router, tags=["prompts"])
app.include_router(indexes.router, tags=["indexes"])
app.include_router(rag.router, tags=["rag"])
app.include_router(evaluation.router, tags=["evaluation"])

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8033)
