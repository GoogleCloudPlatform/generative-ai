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

from google.cloud.aiplatform import Model

GOOGLE_AI_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
    "gemini-1.0-pro",

]

class ModelService:

    def get_all(self):
        custom_models = Model.list()
        return [
            {
                "name": "Gemini",
                "models": GOOGLE_AI_MODELS,
            },
            {
                "name": "Custom",
                "models": [cm.display_name for cm in custom_models],
            }
        ]