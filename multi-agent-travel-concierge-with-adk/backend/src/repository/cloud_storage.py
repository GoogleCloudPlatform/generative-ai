# Copyright 2025 Google LLC
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

from typing import List
from google.cloud.storage import Client, Blob

BUCKET="quick-bot"

INTENT_FOLDER="intents"
EMBEDDINGS_FILE="embeddings.json"
EMBEDDINGS_FOLDER="embeddings"

CONTENT_TYPE="text/plain"

class CloudStorageRepository:

    def __init__(self):
        self.client = Client()
    
    def list(self, full_path: str) -> List[Blob]:
        bucket = full_path.split("/")[2]
        prefix = full_path.replace(f"gs://{bucket}/", "")
        return list(self.client.list_blobs(bucket, prefix=prefix))