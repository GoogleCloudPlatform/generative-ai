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

from hashlib import sha256
from json import dumps
from src.model.intent import Intent
from typing import List


def intents_to_json(intents: List[Intent]):
  """Converts BigQuery results to a JSON string."""
  dictionaries = [intent.to_dict() for intent in intents]
  return dumps(dictionaries, sort_keys=True)

def generate_hash(data):
  """Generates a SHA-256 hash of the input data."""
  hash_object = sha256(data.encode())
  return hash_object.hexdigest()