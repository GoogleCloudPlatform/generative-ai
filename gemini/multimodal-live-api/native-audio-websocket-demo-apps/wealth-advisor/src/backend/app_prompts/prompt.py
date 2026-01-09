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


import re
import typing

from pathlib import Path

import yaml

from google.genai.types import (
    DynamicRetrievalConfig,
    FunctionDeclaration,
    GenerationConfig,
    GoogleSearchRetrieval,
    SafetySetting,
    Tool,
    ToolConfig,
)

from ..app_logging import get_logger


PartsType = typing.Union[str, dict, list]
logger = get_logger(__name__)  # type: ignore


class Prompt:
    def __init__(self, prompt_name: str, prompt_dir: typing.Optional[Path] = None):
        self.prompt_name = prompt_name
        if prompt_dir is not None:
            self.prompt_dir = prompt_dir
        else:
            self.prompt_dir = Path(__file__).parent / "prompts"
        self._load_from_yaml()

    def _load_from_yaml(self):
        yaml_filepath = None
        for ext in [".yaml", ".yml"]:
            potential_path = self.prompt_dir / f"{self.prompt_name}{ext}"
            if potential_path.exists():
                yaml_filepath = potential_path
                break

        if yaml_filepath is None:
            raise FileNotFoundError(
                f"YAML file not found: {self.prompt_name}.yaml or {self.prompt_name}.yml in {self.prompt_dir}"
            )

        try:
            with open(yaml_filepath, "r") as f:
                prompt_data = yaml.safe_load(f)

            self.prompt = prompt_data.get("prompt")
            self.prompt_rag_agent_v1_2 = prompt_data.get("prompt_rag_agent_v1_2")
            self.prompt_financial_planning_v2_0 = prompt_data.get("prompt_financial_planning_v2_0")
            self.variables = prompt_data.get("variables")
            self.generation_config = self._create_object(GenerationConfig, prompt_data.get("generation_config"))
            self.model = prompt_data.get("model_name")
            self.safety_settings = self._safety_setting_kv_translate(SafetySetting, prompt_data.get("safety_settings"))
            self.system_instruction = prompt_data.get("system_instruction")
            self.tools = self._create_list_of_objects(Tool, prompt_data.get("tools"))
            self.tool_config = self._create_object(ToolConfig, prompt_data.get("tool_config"))

            if self.variables:  # Process variables if they exist
                self.prompt = self._replace_variables(self.prompt, self.variables)

        except FileNotFoundError:
            raise
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML file: {e}")
        except Exception as e:  # Catch other potential errors during attribute setting
            raise ValueError(f"Error loading prompt data: {e}")

    def _replace_variables(self, text, variables):
        """Recursively replaces variables in a string, list, or dictionary."""

        if isinstance(text, str):
            for key, value in variables.items():
                if isinstance(value, (int, float, bool)):  # convert numbers to string to avoid errors
                    value = str(value)
                if isinstance(value, str):  # only do replacement if it's a string. otherwise skip
                    text = re.sub(
                        r"{" + re.escape(key) + r"}", value, text
                    )  # escape the key to handle special characters
            return text
        else:
            return text  # Return the text unchanged if it's not a string, list, or dict

    def _create_object(self, cls, data):
        """Helper to create objects from dictionaries, handling None and lists."""
        if data is None:
            return None
        if isinstance(data, list):  # Handle cases where it's a list of objects.
            return [self._create_object(cls, item) for item in data]
        if isinstance(data, dict) and cls is not None:  # Only create if data is a dict and cls is provided
            try:
                return cls(**data)  # Use keyword unpacking to create the object
            except TypeError as e:  # Handle potential mismatch between dict keys and object parameters
                raise TypeError(f"Error: Could not create object of type {cls.__name__} due to a type error: {e}")

        return data  # If not a dict, return the data as is (for simple types)

    def _safety_setting_kv_translate(self, cls, data):
        if data is None:
            return None
        try:
            return self._create_object(cls, [{"category": k, "threshold": v} for k, v in data.items()])
        except TypeError as e:  # Handle potential mismatch between dict keys and object parameters
            raise TypeError(f"Error: Could not create object of type {cls.__name__} due to a type error: {e}")

    def _create_list_of_objects(self, cls, data):
        if data is None:
            return None
        if isinstance(data, list):
            tools = []
            for item in data:
                tool_type = item.get("type")
                if tool_type == "function_declaration":
                    function_data = item.get("declaration_params")
                    tool = Tool(function_declarations=[FunctionDeclaration(**function_data)])
                elif tool_type == "google_search_retrieval":
                    dynamic_retrieval = item.get("dynamic_retrieval_tool_config")
                    if isinstance(dynamic_retrieval, dict) and dynamic_retrieval.get("dynamic_threshold"):
                        tool = Tool(
                            google_search_retrieval=GoogleSearchRetrieval(
                                dynamic_retrieval_config=DynamicRetrievalConfig(
                                    dynamic_threshold=dynamic_retrieval.get("dynamic_threshold"),
                                )
                            )
                        )
                    else:
                        tool = Tool(google_search_retrieval=GoogleSearchRetrieval())
                else:
                    print(f"Warning: Unknown tool type: {tool_type}")
                    continue  # Skip unknown tool types
                tools.append(tool)
            return tools
        return None  # Handle cases where data is not a list

    def __repr__(self):
        return f"Prompt({self.prompt_name})"
