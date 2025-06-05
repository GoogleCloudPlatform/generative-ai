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

from google.cloud.storage import Client
from google.cloud.storage.bucket import Bucket

def create_bucket(bucket_name: str, location: str, storage_client: Client) -> Bucket:
    storage_bucket = storage_client.bucket(bucket_name)
    if not storage_bucket.exists():
        print(f"{bucket_name} Bucket does not exist, creating it...")
        storage_bucket = storage_client.create_bucket(
            bucket_name,
            location=location,
        )
        print(f"Successfully created bucket {storage_bucket.name}")

    return storage_bucket
