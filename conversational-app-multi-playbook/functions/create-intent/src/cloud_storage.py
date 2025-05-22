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

BASE_BUCKET="quick-bot"
EMBEDDINGS_FILE="embeddings.json"
EMBEDDINGS_FOLDER="embeddings"

CONTENT_TYPE="text/plain"

class CloudStorageRepository:

    def __init__(self, project_id: str):
        self.client = Client()
        self.bucket_name = f"{BASE_BUCKET}-{project_id}"
        self.bucket = self.client.bucket(self.bucket_name)
    
    def create(self, resource_name: str, content: str):
        new_blob = self.bucket.blob(resource_name)
        new_blob.content_type = CONTENT_TYPE
        new_blob.upload_from_string(content)