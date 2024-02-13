# Copyright 2024 Google LLC
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

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.logger import logger
from google.cloud import storage
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

app = FastAPI()

gunicorn_logger = logging.getLogger("gunicorn.error")
logger.handlers = gunicorn_logger.handlers

if __name__ != "main":
    logger.setLevel(gunicorn_logger.level)
else:
    logger.setLevel(logging.INFO)

logger.info(f"Is CUDA available: {torch.cuda.is_available()}")
logger.info(f"CUDA device: {torch.cuda.get_device_name(torch.cuda.current_device())}")

storage_client = storage.Client()
bucket_parts = os.environ["AIP_STORAGE_URI"].removeprefix("gs://").split("/")
bucket_name = bucket_parts[0]
prefix = "/".join(bucket_parts[1:])
bucket = storage_client.bucket(bucket_name)
blobs = bucket.list_blobs(prefix=prefix)
model_dir = Path("distilled-t5")
model_dir.mkdir(exist_ok=True)

for blob in blobs:
    filename = blob.name.split("/")[-1]
    blob.download_to_filename(model_dir / filename)

model = AutoModelForSeq2SeqLM.from_pretrained(model_dir, device_map="auto")
tokenizer = AutoTokenizer.from_pretrained(model_dir)


@app.get(os.environ["AIP_HEALTH_ROUTE"], status_code=200)
def health():
    return {"status": "healthy"}


@app.post(os.environ["AIP_PREDICT_ROUTE"])
async def predict(request: Request):
    body = await request.json()

    instances = body["instances"]

    outputs = []
    for instance in instances:
        input_ids = tokenizer(instance, return_tensors="pt").input_ids
        output = model.generate(input_ids)
        prediction = tokenizer.decode(output[0], skip_special_tokens=True)
        outputs.append(prediction)

    return {"predictions": [outputs]}
